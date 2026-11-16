#!/usr/bin/env python3
"""Inspect completed QE logs for independent units, occupations and residual checks.

Inputs: actual runs/*/{config,receipt,parsed}.json and pw.out, never invented data.
Output: numerical_diagnostics.json, including explicit unavailable/failed cases.
Dependencies: Python >=3.10 and adjacent fese.py; no QE execution occurs here.
Example: python numerical_diagnostics.py

These diagnostics supplement, rather than replace, magnetic energy-difference
convergence tests. Printed zero occupations mean below print resolution; cold
smearing occupations may slightly exceed one and are not clipped or rejected.
"""
from pathlib import Path
import json
import math
import re

import fese

ROOT=Path(__file__).resolve().parent
BOHR_ANG=0.529177210903  # CODATA 2018; printed-volume check, not a fitted constant.
NUMBER=r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eEdD][-+]?\d+)?'


def numbers_after(lines, start):
    """Read a consecutive printed numeric block, skipping only initial blanks."""
    values=[]
    for line in lines[start:]:
        if not line.strip():
            if values:break
            continue
        if not re.fullmatch(r'\s*(?:'+NUMBER+r'\s*)+',line):break
        values.extend(float(x.replace('D','E').replace('d','e')) for x in re.findall(NUMBER,line))
    return values


def inspect_run(directory):
    """Return observed log diagnostics in eV, Ry, Angstrom and meV/Fe.

    A failed or incomplete process has no accepted numerical diagnostic values.
    Occupation checks require every final printed band block to contain nbnd
    values. Missing blocks never become zero occupancy or an adequacy claim.
    """
    c=json.loads((directory/'config.json').read_text())
    receipt=json.loads((directory/'receipt.json').read_text())
    logpath=directory/'pw.out'
    text=logpath.read_text() if logpath.exists() else ''
    raw=fese.parse_pw(text,receipt.get('pw',{}).get('exit_code'))
    row={'run_id':directory.name,'run_status':receipt.get('status'),'input_sha256':receipt.get('input_sha256'),
         'log_sha256':fese.sha(logpath) if logpath.exists() else None,'diagnostic_status':'NOT_COMPLETED',
         'occupation_check':None,'volume_check':None,'energy_residual_check':None}
    if receipt.get('status')!='RUN_COMPLETED' or raw['status']!='RUN_COMPLETED':return row
    if receipt.get('file_hashes',{}).get('config.json')!=fese.sha(directory/'config.json') or receipt.get('input_sha256')!=fese.sha(directory/'input.in'):
        row['diagnostic_status']='INPUT_OR_CONFIG_HASH_MISMATCH';return row
    if receipt.get('file_hashes',{}).get('pw.out')!=row['log_sha256']:
        row['diagnostic_status']='RAW_LOG_HASH_MISMATCH';return row
    block=re.split(r'Program PWSCF',text)[-1]
    final=block.rsplit('End of self-consistent calculation',1)[-1]
    lines=final.splitlines()
    bands=[numbers_after(lines,i+1) for i,line in enumerate(lines) if 'bands (ev):' in line]
    occs=[numbers_after(lines,i+1) for i,line in enumerate(lines) if 'occupation numbers' in line]
    matches=re.findall(r'the Fermi energy is\s+('+NUMBER+r')\s+ev',final,re.I)
    fermi=float(matches[-1]) if matches else None
    complete=bool(bands) and len(bands)==len(occs) and all(len(x)==c['nbnd'] for x in bands+occs)
    highest=max(abs(x[-1]) for x in occs) if complete else None
    margin=min(x[-1]-fermi for x in bands) if complete and fermi is not None else None
    width_ev=c['degauss_ry']*fese.RY_EV
    row['occupation_check']={'status':'PRINTED_BLOCKS_COMPLETE' if complete else 'NOT_ESTABLISHED',
        'nbnd':c['nbnd'],'printed_band_blocks':len(bands),'printed_occupation_blocks':len(occs),
        'fermi_energy_ev':fermi,'maximum_abs_printed_highest_band_occupation':highest,
        'occupation_print_resolution':0.0001,'minimum_highest_band_above_fermi_ev':margin,
        'minimum_margin_in_smearing_widths':margin/width_ev if margin is not None else None,
        'highest_band_empty_at_print_precision':highest<0.00005 if highest is not None else None,
        'interpretation':'Checks truncation of occupied bands at printed precision; does not establish k-mesh or smearing convergence'}
    volumes=re.findall(r'unit-cell volume\s*=\s*('+NUMBER+r')\s*\(a.u.\)\^3',block)
    volume=float(volumes[-1]) if volumes else None
    expected=2*c['a_ang']**2*c['c_ang']/BOHR_ANG**3
    relative=abs(volume-expected)/expected if volume is not None else None
    row['volume_check']={'qe_printed_bohr3':volume,'derived_bohr3':expected,'relative_difference':relative,
        'within_print_precision':relative<1e-6 if relative is not None else None,
        'definition':'det(A,B,C)=2*a^2*c; Angstrom^3 converted using CODATA bohr'}
    energies=[float(x) for x in re.findall(r'(?:!\s*)?total energy\s*=\s*('+NUMBER+r')\s+Ry',block)]
    final_delta=abs(energies[-1]-energies[-2])*fese.RY_EV*1000/c['n_fe'] if len(energies)>1 else None
    row['energy_residual_check']={'qe_estimated_scf_accuracy_ry_cell':raw.get('scf_accuracy_ry'),
        'qe_estimated_scf_accuracy_mev_fe':raw['scf_accuracy_ry']*fese.RY_EV*1000/c['n_fe'] if raw.get('scf_accuracy_ry') is not None else None,
        'last_printed_iteration_energy_change_mev_fe':final_delta,
        'interpretation':'Electronic self-consistency diagnostics only; not a total discretization error bound'}
    row['diagnostic_status']='OBSERVED_COMPLETED_LOG_CHECKS'
    return row


def main():
    rows=[inspect_run(p.parent) for p in sorted((ROOT/'runs').glob('*/config.json'))]
    result={'source_sha256':fese.sha(__file__),'bohr_in_angstrom':BOHR_ANG,
            'scope':'Actual completed logs; no synthetic scientific values','runs':rows}
    fese.dump(ROOT/'numerical_diagnostics.json',result)
    print(json.dumps({'records':len(rows),'completed_diagnostics':sum(r['diagnostic_status']=='OBSERVED_COMPLETED_LOG_CHECKS' for r in rows)}))


if __name__=='__main__':main()
