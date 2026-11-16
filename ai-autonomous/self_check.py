#!/usr/bin/env python3
"""Check physical invariants and failure semantics, without calculating mock results.

Usage: python self_check.py. Dependencies: standard Python and adjacent fese.py.
Writes SELF_CHECK.json. Synthetic parser fixtures are only tests, never results rows.
Existing real failed outputs are rechecked when present. This is producer validation.
"""
import math
from pathlib import Path
import fese

def main():
    """Validate volume, composition, NN topology, parser failure handling and labels."""
    c=fese.normalize({'run_id':'invariant_check','initial_state':'CB'})
    cell,sites=fese.geometry(c)
    a,cc,z=c['a_ang'],c['c_ang'],c['z_se']
    assert len(sites)==8 and sum(s[0].startswith('Fe') for s in sites)==4
    determinant=(cell[0][0]*cell[1][1]-cell[0][1]*cell[1][0])*cell[2][2]
    assert abs(determinant-2*a*a*cc)<1e-10
    checks=[]
    for label in ('FM','CB','STRIPE'):
        signs=fese.PATTERNS[label]
        nn_corr=[];nnn_corr=[]
        for i,(x,y) in enumerate(fese.FE_XY):
            nn=[];nnn=[]
            for j,(xx,yy) in enumerate(fese.FE_XY):
                for tx in (-1,0,1):
                    for ty in (-1,0,1):
                        dx,dy=xx+tx-x,yy+ty-y
                        r2=2*a*a*(dx*dx+dy*dy)
                        if abs(r2-a*a/2)<1e-9:nn.append(signs[i]*signs[j])
                        if abs(r2-a*a)<1e-9:nnn.append(signs[i]*signs[j])
            assert len(nn)==4 and len(nnn)==4
            nn_corr.append(sum(nn)/4);nnn_corr.append(sum(nnn)/4)
        assert nn_corr=={'FM':[1]*4,'CB':[-1]*4,'STRIPE':[0]*4}[label]
        assert nnn_corr=={'FM':[1]*4,'CB':[1]*4,'STRIPE':[-1]*4}[label]
        checks.append({'initial_state':label,'nn_sign_correlation':nn_corr,'nnn_sign_correlation':nnn_corr})
    # Generated fixtures check acceptance logic only; no fictitious row is persisted.
    bad='Program PWSCF v.6.7MaX\nSelf-consistent Calculation\n! total energy = -1.0 Ry\nconvergence NOT achieved after 1 iterations\nJOB DONE.'
    good=bad.replace('convergence NOT achieved after 1 iterations','convergence has been achieved in 10 iterations')
    assert fese.parse_pw(bad,0)['status']=='UNCONVERGED'
    assert fese.parse_pw(good,0)['status']=='RUN_COMPLETED'
    assert fese.parse_pw(good+bad,0)['status']=='UNCONVERGED'
    assert fese.parse_pw(good,1)['status']=='RUN_FAILED'
    assert fese.parse_pw('JOB DONE.\n! total energy = -1.0 Ry',0)['status']=='UNCONVERGED'
    assert fese.parse_pw(good+'\nError in routine bad_input',0)['status']=='RUN_FAILED'
    ok={'status':'RUN_COMPLETED','absolute_magnetization_muB_cell':0}
    assert fese.final_state(c,ok,[0]*8)=='NM_COLLAPSED'
    assert fese.final_state(c,ok,[1,-1,-1,1]+[0]*4)=='CB'
    assert fese.final_state(c,ok,[1,-1,1,-1]+[0]*4)=='STRIPE'
    assert fese.final_state(c,ok,[None]*8)=='UNVERIFIED_FINAL_STATE'
    assert fese.final_state({'initial_state':'NM'},{'status':'RUN_FAILED'},[0]*8)=='UNVERIFIED_FINAL_STATE'
    actual=[]
    for name in ('P001_stripe_60_k443','P002_stripe_openblas_serial'):
        path=fese.ROOT/'runs'/name/'pw.out'
        if path.exists():
            p=fese.parse_pw(path.read_text(),2)
            assert p['status']=='RUN_FAILED' and not p['scf_converged']
            actual.append(name)
    fese.dump(fese.ROOT/'SELF_CHECK.json',{'status':'SELF_CHECK_PASS','checked_at':fese.utc(),
      'source_sha256':fese.sha(fese.__file__),'geometry':checks,
      'volume_ang3':determinant,'nn_distance_ang':a/math.sqrt(2),'se_height_ang':z*cc,
      'synthetic_parser_cases':6,'magnetic_classifier_cases':5,
      'actual_failed_runs_rechecked':actual,'independent_audit':False})
    print('Physical invariants and failure handling: PASS (producer checks)')

if __name__=='__main__':main()
