#!/usr/bin/env python3
"""Generate, run and parse a transparent four-Fe Quantum ESPRESSO experiment.

Inputs: JSON campaign (list of case dictionaries) and exact common UPFs in pseudos/.
Outputs: immutable runs/<run_id>/input.in, config.json, stdout/stderr, receipt.json,
and parsed.json; analyze writes independently readable results.json/results.csv.
Dependencies: Python >=3.10; pw.x and optional projwfc.x; MPI only if ranks >1.
Example: python fese.py run campaigns/pilot.json --pw /path/pw.x --ranks 4

No restart is implicit: each attempt starts from atomic density in a new directory.
Use a new run_id for repairs/replays. Geometry is fixed, collinear PBE, no SOC/U.
Scientific rationale, source distinctions and accuracy gates are in the plan.
"""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parent
# CODATA value is adequate far beyond the eight-decimal Ry print precision here.
RY_EV = 13.605693122994
PSEUDOS = {
    'Fe_std.upf': '79848bdb660ac0fe3f93ac0967cba01fe200f5cc2cf37e7f01e6ac051f107105',
    'Se_std.upf': '1f5d0f8b99028dee90766aab811ce5d8bb2c2b2ad38ec60436d1c2888ef5109c',
}
PATTERNS = {'FM': [1, 1, 1, 1], 'CB': [1, -1, -1, 1],
            'STRIPE': [1, -1, 1, -1], 'NM': [0, 0, 0, 0]}
FE_XY = [(0., 0.), (.5, 0.), (0., .5), (.5, .5)]
DEFAULTS = dict(a_ang=3.765, c_ang=5.518, z_se=.2343, ecutwfc_ry=60.,
                kgrid=[4, 4, 3], kshift=[0, 0, 0], degauss_ry=.02,
                conv_thr_ry=1e-7, mixing_beta=.3, electron_maxstep=120,
                starting_polarization=.15, nbnd=84, max_seconds=600,
                project=True, stage='PILOT', path_id='FIXED_C_Z_TETRAGONAL_R01')

def utc():
    """Return an unambiguous UTC timestamp for observable runtime evidence."""
    return dt.datetime.now(dt.timezone.utc).isoformat()

def sha(path):
    """SHA256 exact on-disk bytes, streamed to avoid copying large scratch files."""
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

def dump(path, obj):
    """Write readable strict JSON; missing observables stay null, never NaN/zero."""
    path=Path(path)
    temp=path.with_name(path.name+f'.{os.getpid()}.tmp')
    temp.write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')
    temp.replace(path)

def normalize(case):
    """Validate physical/settings input; a,c are Angstrom and z is fractional.

    nFe=4 and nSe=4 are invariant. Empty bands, smearing and cutoffs are explicit.
    Starting spin polarization is per valence electron (QE <=7.2 convention).
    """
    c = {**DEFAULTS, **case}
    assert re.fullmatch(r'[A-Za-z0-9_.-]+', c['run_id']), 'Unsafe run ID'
    assert c['initial_state'] in PATTERNS
    assert min(c['a_ang'], c['c_ang'], c['ecutwfc_ry'], c['conv_thr_ry']) > 0
    assert 0 < c['z_se'] < .5
    assert len(c['kgrid']) == 3 and all(isinstance(n, int) and n > 0 for n in c['kgrid'])
    assert len(c['kshift']) == 3 and all(n in (0, 1) for n in c['kshift'])
    if c.get('gamma_only',False):
        assert c['kgrid']==[1,1,1] and c['kshift']==[0,0,0]
    assert 0 <= c['starting_polarization'] < 1
    c['ecutrho_ry'] = c.get('ecutrho_ry', 4 * c['ecutwfc_ry'])
    c['n_fe'] = 4
    c['functional'] = 'PBE'
    c['smearing'] = 'mv'
    c['relativistic'] = 'scalar; collinear; no SOC'
    c['startingwfc']='atomic+random'
    c['startingpot']='atomic'
    c['rng_algorithm']='QE6.7 randy shuffled LCG; m=714025, ia=1366, ic=150889, ntab=97'
    c['rng_default_initial_seed']=0
    c['rng_seed_evidence']='SOURCE_DERIVED_DEFAULT_FOR_CONFIGURED_STATIC_SCF_PATH'
    c['rng_state_runtime_captured']=False
    return c

def geometry(c):
    """Return (3,3) row cell vectors in Angstrom and eight fractional sites.

    Starting tetragonal cell: Fe (0,0,0),(.5,.5,0); Se (.5,0,z),(0,.5,-z).
    A=a(1,1,0), B=a(-1,1,0) doubles its volume and puts Fe NN along A/2,B/2.
    Reciprocal/real transformation is derived exactly; all states share this cell.
    """
    a, caxis, z = c['a_ang'], c['c_ang'], c['z_se']
    cell = [[a, a, 0], [-a, a, 0], [0, 0, caxis]]
    signs = PATTERNS[c['initial_state']]
    sites = [('Feu' if s >= 0 else 'Fed', x, y, 0.)
             for (x, y), s in zip(FE_XY, signs)]
    sites += [('Se', .25, .75, z), ('Se', .75, .25, z),
              ('Se', .25, .25, 1-z), ('Se', .75, .75, 1-z)]
    return cell, sites

def input_text(c):
    """Build documented QE 6.7 syntax with no fixed-moment constraint.

    Species Feu/Fed use identical UPF bytes, distinguished only to initialize AFM.
    A common cell/grid avoids intercell k-density and normalization ambiguities.
    """
    cell, sites = geometry(c)
    nm = c['initial_state'] == 'NM'
    afm = c['initial_state'] in ('CB', 'STRIPE')
    species = ['Feu 55.845 Fe_std.upf']
    if afm:
        species.append('Fed 55.845 Fe_std.upf')
    species.append('Se 78.971 Se_std.upf')
    mag = '' if nm else f" starting_magnetization(1)={c['starting_polarization']},\n"
    if afm:
        mag += f" starting_magnetization(2)={-c['starting_polarization']},\n"
    return f"""! Independent fixed-geometry FeSe calculation; run {c['run_id']}
! a,c in Angstrom; fractional sites; four Fe per cell.
! Feu/Fed share one exact UPF; starting polarization is NOT constrained moment.
&CONTROL
 calculation='scf', restart_mode='from_scratch', prefix='fese',
 pseudo_dir='../../pseudos', outdir='./scratch', verbosity='high',
 tprnfor=.true., tstress=.true., disk_io='low', max_seconds={c['max_seconds']},
/
&SYSTEM
 ibrav=0, nat=8, ntyp={len(species)}, nspin={1 if nm else 2},
 ecutwfc={c['ecutwfc_ry']}, ecutrho={c['ecutrho_ry']}, nbnd={c['nbnd']},
 occupations='smearing', smearing='mv', degauss={c['degauss_ry']},
{mag}/
&ELECTRONS
 conv_thr={c['conv_thr_ry']:.10g}, electron_maxstep={c['electron_maxstep']},
 mixing_beta={c['mixing_beta']}, mixing_mode='plain', diagonalization='david',
 startingpot='atomic', startingwfc='atomic+random',
/
ATOMIC_SPECIES
""" + '\n'.join(species) + '\nCELL_PARAMETERS angstrom\n' + \
        '\n'.join(' '.join(f'{v:.12f}' for v in row) for row in cell) + \
        '\nATOMIC_POSITIONS crystal\n' + \
        '\n'.join(f'{s} {x:.12f} {y:.12f} {z:.12f}' for s, x, y, z in sites) + \
        ('\nK_POINTS gamma\n' if c.get('gamma_only',False) else
         '\nK_POINTS automatic\n' + ' '.join(str(x) for x in c['kgrid']+c['kshift']) + '\n')

def prepare(case):
    """Create a new immutable attempt; raises if run_id already exists."""
    c = normalize(case)
    for n, expected in PSEUDOS.items():
        assert sha(ROOT/'pseudos'/n) == expected, f'Wrong pseudopotential {n}'
    source_hash=sha(__file__)
    versions=ROOT/'source_versions'
    versions.mkdir(exist_ok=True)
    saved_source=versions/f'{source_hash}.py'
    if not saved_source.exists():
        shutil.copyfile(__file__,saved_source)
    d = ROOT/'runs'/c['run_id']
    d.mkdir(parents=True, exist_ok=False)
    (d/'scratch').mkdir()
    (d/'input.in').write_text(input_text(c))
    dump(d/'config.json', c)
    dump(d/'receipt.json', dict(run_id=c['run_id'], status='NOT_RUN', prepared_at=utc(),
         input_sha256=sha(d/'input.in'), pseudo_sha256=PSEUDOS, source_sha256=source_hash,
         source_path=str(saved_source.relative_to(ROOT))))
    return d, c

def run_process(cmd, d, stem, seconds):
    """Run without a shell, save both streams and terminate the process group on timeout.

    CPU seconds is child user+system delta, including MPI children where OS accounts
    them. ru_maxrss is a process high-water mark, not aggregate node RAM utilization.
    """
    start, t0 = utc(), time.monotonic()
    r0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    env = os.environ.copy()
    env.setdefault('OMP_NUM_THREADS', '1')
    env.setdefault('OPENBLAS_NUM_THREADS', '1')
    timed_out = False
    live=dict(command=cmd,cwd=str(d),start=start,status='RUNNING',timeout_seconds=seconds,
              environment={k:env.get(k) for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','LD_LIBRARY_PATH')})
    dump(d/f'{stem}_execution.json',live)
    with (d/f'{stem}.out').open('w') as out, (d/f'{stem}.err').open('w') as err:
        try:
            p = subprocess.Popen(cmd, cwd=d, env=env, stdout=out, stderr=err, start_new_session=True)
            live['pid']=p.pid
            dump(d/f'{stem}_execution.json',live)
            try:
                code = p.wait(timeout=seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(p.pid, signal.SIGTERM)
                try:
                    p.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(p.pid, signal.SIGKILL)
                    p.wait()
                code = 124
        except OSError as e:
            err.write(f'{type(e).__name__}: {e}\n')
            code = 127
    r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    result=dict(command=cmd, cwd=str(d), start=start, end=utc(), exit_code=code,
        elapsed_seconds=time.monotonic()-t0, timed_out=timed_out,
        child_cpu_seconds=r1.ru_utime+r1.ru_stime-r0.ru_utime-r0.ru_stime,
        child_maxrss_kib=r1.ru_maxrss, environment={k:env.get(k) for k in
          ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','LD_LIBRARY_PATH')})
    dump(d/f'{stem}_execution.json',{**result,'status':'PROCESS_EXITED'})
    return result

def runtime_identity(pw, proj):
    """Record selected numerical libraries, not only the unchanged executable hash.

    Library selection is resolved by the actual loader under this run environment.
    This is execution evidence, not a claim of equivalence between BLAS builds.
    """
    result={'pw_sha256':sha(pw) if Path(pw).is_file() else None,
            'projwfc_sha256':sha(proj) if Path(proj).is_file() else None}
    try:
        probe=subprocess.run(['ldd',pw],capture_output=True,text=True,timeout=20)
        result['ldd_stdout']=probe.stdout;result['ldd_stderr']=probe.stderr
        libs={}
        for line in probe.stdout.splitlines():
            if re.search(r'lib(?:blas|lapack|openblas|scalapack|mpi|fftw|gfortran)',line):
                m=re.search(r'=>\s+(/\S+)',line)
                if m and Path(m.group(1)).is_file():
                    path=Path(m.group(1)).resolve()
                    libs[path.name]={'path':str(path),'sha256':sha(path)}
        result['numerical_libraries']=libs
        result['profile_sha256']=hashlib.sha256(json.dumps({n:v['sha256'] for n,v in libs.items()},sort_keys=True).encode()).hexdigest()
    except (OSError,subprocess.TimeoutExpired) as e:
        result['identity_error']=str(e)
    return result

def parse_pw(text, exit_code):
    """Parse only the final SCF invocation. Completion requires explicit SCF evidence.

    A previous converged invocation cannot rescue an appended failed/incomplete one.
    A final energy or JOB DONE alone is insufficient. Return absent values as null.
    """
    block = re.split(r'Program PWSCF', text)[-1]
    scf = re.split(r'Self-consistent Calculation', block)[-1]
    def last(pattern, cast=float):
        vals = re.findall(pattern, scf, flags=re.I)
        return cast(vals[-1].replace('D','E').replace('d','e')) if vals else None
    number = r'([-+0-9.eEdD]+)'
    conv = bool(re.search(r'convergence has been achieved in\s+\d+ iterations', scf, re.I))
    failed = bool(re.search(r'Error in routine|MPI_ABORT|%%%%%%%%', scf, re.I))
    notconv = bool(re.search(r'convergence NOT achieved', scf, re.I))
    energy = last(r'!\s*total energy\s*=\s*'+number+r'\s+Ry')
    done = 'JOB DONE.' in block
    status = 'RUN_FAILED' if exit_code != 0 or failed else 'RUN_COMPLETED' if conv and done and not notconv and energy is not None else 'UNCONVERGED'
    return dict(status=status, scf_converged=conv and not notconv, job_done=done,
        energy_total_ry=energy, scf_accuracy_ry=last(r'estimated scf accuracy\s*[<=>]+\s*'+number),
        scf_iterations=last(r'convergence has been achieved in\s+(\d+) iterations',int),
        total_magnetization_muB_cell=last(r'total magnetization\s*=\s*'+number),
        absolute_magnetization_muB_cell=last(r'absolute magnetization\s*=\s*'+number),
        smearing_contribution_ry=last(r'smearing contrib\. \(-TS\)\s*=\s*'+number),
        qe_version=(re.findall(r'v\.([^\s]+)',block) or [None])[0])

def parse_projection(text):
    """Extract per-site Lowdin spin polarization (up-down) in electrons/muB.

    Projector populations are partition-dependent. They do not equal the 2.1-bohr
    LAPW sphere observable in Subedi Table I. Missing or ambiguous sites fail closed.
    """
    text = text.split('Lowdin Charges:')[-1]
    blocks = re.split(r'Atom\s*#\s*(\d+)\s*:', text)
    moments = {}
    for i in range(1,len(blocks),2):
        m = re.search(r'polarization\s*=\s*([-+0-9.Ee]+)',blocks[i+1],re.I)
        if m:
            moments[int(blocks[i])] = float(m.group(1))
    return [moments.get(i) for i in range(1,9)]

def final_state(c, p, moments):
    """Classify topology from all four Fe moments; zero net spin alone is insufficient.

    Below 0.05 muB/Fe is an explicitly declared numerical classification threshold.
    This is a label tolerance, not a magnetic susceptibility/stability threshold.
    Global spin inversion and both stripe orientations are equivalent for this cell.
    """
    if p.get('status')!='RUN_COMPLETED':
        return 'UNVERIFIED_FINAL_STATE'
    if c['initial_state'] == 'NM':
        return 'NM_ENFORCED_NSPIN1'
    if len(moments)<4 or any(x is None for x in moments[:4]):
        return 'UNVERIFIED_FINAL_STATE'
    m = moments[:4]
    if max(abs(x) for x in m)<.05:
        abs_cell = p.get('absolute_magnetization_muB_cell')
        return 'NM_COLLAPSED' if abs_cell is not None and abs_cell/4<.05 else 'SMALL_FE_MOMENTS'
    s = [1 if x>.05 else -1 if x<-.05 else 0 for x in m]
    for label,pattern in [('FM',PATTERNS['FM']),('CB',PATTERNS['CB']),
                          ('STRIPE',PATTERNS['STRIPE']),('STRIPE',[1,1,-1,-1])]:
        if s==pattern or s==[-x for x in pattern]:
            return label
    return 'MIXED_OR_UNCLASSIFIED'

def execute(case, pw, proj, ranks):
    """Run one fresh SCF and, only on explicit SCF success, its spin diagnostic."""
    d,c = prepare(case)
    receipt = json.loads((d/'receipt.json').read_text())
    pwpath = shutil.which(pw) or pw
    proj = shutil.which(proj) or proj
    launcher = ['mpirun','-np',str(ranks)] if ranks>1 else []
    receipt['pw_executable'] = str(Path(pwpath).resolve())
    receipt['pw_sha256'] = sha(pwpath) if Path(pwpath).is_file() else None
    identity=runtime_identity(pwpath,proj)
    dump(d/'runtime.json',identity)
    receipt['runtime_profile_sha256']=identity.get('profile_sha256')
    receipt['projwfc_sha256']=identity.get('projwfc_sha256')
    receipt['status']='RUNNING'
    dump(d/'receipt.json',receipt)
    receipt['pw'] = run_process(launcher+[pwpath,'-nk',str(c.get('kpoint_pools',1)),'-in','input.in'],d,'pw',c['max_seconds']+60)
    p = parse_pw((d/'pw.out').read_text(),receipt['pw']['exit_code'])
    moments = [None]*8
    if p['status']=='RUN_COMPLETED' and c['project'] and c['initial_state']!='NM':
        # Same saved SCF wavefunctions and k-grid; no separate NSCF approximation.
        (d/'proj.in').write_text("&PROJWFC\n prefix='fese', outdir='./scratch',\n filpdos='pdos',\n DeltaE=0.05,\n/\n")
        receipt['projection'] = run_process(launcher+[proj,'-in','proj.in'],d,'proj',300)
        if receipt['projection']['exit_code']==0:
            moments=parse_projection((d/'proj.out').read_text())
    p.update(run_id=c['run_id'], initial_state=c['initial_state'],
             fe_lowdin_moments_muB=moments[:4], all_lowdin_moments_muB=moments,
             magnetic_diagnostic='Lowdin atomic spin population plus cell spin integrals',
             final_state=final_state(c,p,moments))
    receipt['status']=p['status']
    receipt['file_hashes']={f.name:sha(f) for f in d.iterdir() if f.is_file() and f.name not in ('receipt.json','parsed.json') and f.suffix in ('.in','.out','.err','.json')}
    dump(d/'receipt.json',receipt)
    dump(d/'parsed.json',p)
    print(json.dumps({'run_id':c['run_id'],'status':p['status'],'elapsed_s':receipt['pw']['elapsed_seconds'],'final_state':p['final_state']}),flush=True)
    return p

def analyze():
    """Collect actual records and compare only identical numerical/structural groups.

    Relative-to-min values are per-a comparisons, not a common reference for fitting
    an E(a) curve. Absolute energies and the group identity remain available.
    """
    rows=[]
    for d in sorted((ROOT/'runs').glob('*')):
        if not (d/'config.json').exists():
            continue
        c=json.loads((d/'config.json').read_text())
        r=json.loads((d/'receipt.json').read_text())
        p=json.loads((d/'parsed.json').read_text()) if (d/'parsed.json').exists() else {'status':r.get('status','NOT_RUN'),'energy_total_ry':None,'final_state':'UNVERIFIED_FINAL_STATE'}
        row={**c,**p,'input_path':f'runs/{d.name}/input.in','log_path':f'runs/{d.name}/pw.out',
             'input_sha256':r['input_sha256'],'pw_sha256':r.get('pw_sha256'),
             'runtime_profile_sha256':r.get('runtime_profile_sha256'),
             'exit_code':r.get('pw',{}).get('exit_code'),'elapsed_seconds':r.get('pw',{}).get('elapsed_seconds')}
        row['energy_per_fe_ry']=row['energy_total_ry']/4 if row['energy_total_ry'] is not None else None
        rows.append(row)
    keys=['a_ang','c_ang','z_se','ecutwfc_ry','ecutrho_ry','kgrid','kshift','gamma_only','degauss_ry','smearing','functional','pw_sha256','runtime_profile_sha256','nbnd','conv_thr_ry']
    groups={}
    for r in rows:
        key=json.dumps({k:r.get(k) for k in keys},sort_keys=True)
        groups.setdefault(key,[]).append(r)
    for group in groups.values():
        good=[r for r in group if r['status']=='RUN_COMPLETED']
        emin=min((r['energy_total_ry'] for r in good),default=None)
        nms=[r for r in good if r['initial_state']=='NM']
        enm=nms[0]['energy_total_ry'] if nms else None
        for r in group:
            ok=r in good
            r['relative_to_group_min_mev_fe']=(r['energy_total_ry']-emin)*RY_EV*1000/4 if ok else None
            r['relative_to_nm_mev_fe']=(r['energy_total_ry']-enm)*RY_EV*1000/4 if ok and enm is not None else None
    dump(ROOT/'results.json',rows)
    fields=['run_id','stage','initial_state','final_state','status','path_id','a_ang','c_ang','z_se','n_fe','functional','ecutwfc_ry','ecutrho_ry','kgrid','kshift','degauss_ry','conv_thr_ry','starting_polarization','qe_version','exit_code','scf_converged','scf_iterations','energy_total_ry','relative_to_group_min_mev_fe','relative_to_nm_mev_fe','total_magnetization_muB_cell','absolute_magnetization_muB_cell','fe_lowdin_moments_muB','elapsed_seconds','input_path','log_path']
    csv_temp=ROOT/f'results.csv.{os.getpid()}.tmp'
    with csv_temp.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore',lineterminator='\n');w.writeheader()
        for r in rows:
            w.writerow({k:json.dumps(v) if isinstance(v,(list,dict)) else v for k,v in r.items()})
    csv_temp.replace(ROOT/'results.csv')
    print(f'Wrote {len(rows)} actual run records',flush=True)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest='action',required=True)
    for action in ('run','prepare'):
        p=sub.add_parser(action);p.add_argument('campaign');p.add_argument('--only');p.add_argument('--pw',default='pw.x');p.add_argument('--proj',default='projwfc.x');p.add_argument('--ranks',type=int,default=1);p.add_argument('--no-analyze',action='store_true')
    sub.add_parser('analyze')
    args=ap.parse_args()
    if args.action=='analyze':
        analyze();return
    for case in json.loads(Path(args.campaign).read_text()):
        if args.only and args.only!=case['run_id']:
            continue
        if args.action=='prepare':prepare(case)
        else:
            execute(case,args.pw,args.proj,args.ranks)
            if not args.no_analyze:analyze()

if __name__=='__main__':
    main()
