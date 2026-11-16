#!/usr/bin/env python3
"""Compare actual clean-replay and lower-spin-seed cases with central references.

Inputs: the declared D_ campaign and actual raw-verified per-run records.
Output: replay_and_seed_checks.json; unattempted cases remain NOT_RUN.
Dependencies: Python >=3.10, adjacent analysis_plot.py/fese.py and their imports.
Example: python replay_checks.py

A lower initial polarization is a basin test, not a clean replay. Different final
states are retained explicitly. The energy threshold is the predeclared 1 meV/Fe
comparison goal; a single repeat does not establish universal reproducibility.
"""
from pathlib import Path
import json

import analysis_plot as analysis
import fese

ROOT=Path(__file__).resolve().parent
REFERENCES={'FM':'B_a100_FM_r04','CB':'B_a100_CB_r04','STRIPE':'B_a100_STRIPE_r04'}
FIXED=('a_ang','c_ang','z_se','n_fe','path_id','functional','relativistic',
       'pseudo_sha256','pw_sha256','runtime_profile_sha256','ecutwfc_ry',
       'ecutrho_ry','kgrid','kshift','gamma_only','smearing','degauss_ry',
       'nbnd','conv_thr_ry','mixing_beta','initial_state','startingpot',
       'startingwfc','restart_mode','rng','parallel_layout')


def compare(record, reference, kind):
    """Return one matched observed comparison; missing or inconsistent data fails closed."""
    row={'run_id':record['run_id'],'reference_run_id':reference['run_id'],
         'comparison_kind':kind,'status':'INELIGIBLE_RECORD',
         'energy_change_mev_fe':None,'same_final_state':None}
    if not record['eligible'] or not reference['eligible']:
        row['issues']={'run':record['issues'],'reference':reference['issues']};return row
    a,b=reference['data'],record['data']
    differences=[key for key in FIXED if not analysis._same(a.get(key),b.get(key))]
    if kind=='CLEAN_REPLAY' and not analysis._same(a.get('starting_polarization'),b.get('starting_polarization')):
        differences.append('starting_polarization')
    if differences:
        row.update(status='INCOMPARABLE_SETTINGS',mismatched_fields=differences);return row
    shift=(b['energy_total_ry']-a['energy_total_ry'])*fese.RY_EV*1000/a['n_fe']
    moments_a=a['fe_lowdin_moments_muB'];moments_b=b['fe_lowdin_moments_muB']
    finite=all(analysis._finite(x) for x in moments_a+moments_b)
    moment_delta=min(max(abs(y-s*x) for x,y in zip(moments_a,moments_b)) for s in (1,-1)) if finite else None
    row.update(status='OBSERVED_COMPARABLE_CASES',energy_change_mev_fe=shift,
        same_final_state=a['final_state']==b['final_state'],
        reference_final_state=a['final_state'],run_final_state=b['final_state'],
        final_states_verified=record['final_state_verified'] and reference['final_state_verified'],
        reference_starting_polarization=a['starting_polarization'],
        run_starting_polarization=b['starting_polarization'],
        reference_fe_lowdin_muB=moments_a,run_fe_lowdin_muB=moments_b,
        maximum_site_difference_after_global_spin_flip_muB=moment_delta,
        moment_comparison_limit='Global spin reversal allowed; no spatial permutation is optimized. Printed site moments are retained.',
        energy_goal_mev_fe=1.0,within_energy_goal=abs(shift)<=1.0,
        input_paths=[a['input_path'],b['input_path']],log_paths=[a['log_path'],b['log_path']],
        interpretation='Fresh identical-settings replay' if kind=='CLEAN_REPLAY' else 'Initialization-basin sensitivity; different final solutions are not numerical noise')
    return row


def main():
    records,diagnostics=analysis.load_records(ROOT)
    records={r['run_id']:r for r in records}
    planned=json.loads((ROOT/'campaigns/replays.json').read_text())
    rows=[]
    for case in planned:
        name=case['run_id'];ref=REFERENCES[case['initial_state']]
        kind='CLEAN_REPLAY' if name=='D_replay_STRIPE' else 'LOWER_SPIN_SEED'
        if name not in records:
            rows.append({'run_id':name,'reference_run_id':ref,'comparison_kind':kind,'status':'NOT_RUN','energy_change_mev_fe':None});continue
        if ref not in records:
            rows.append({'run_id':name,'reference_run_id':ref,'comparison_kind':kind,'status':'MISSING_REFERENCE','energy_change_mev_fe':None});continue
        rows.append(compare(records[name],records[ref],kind))
    fese.dump(ROOT/'replay_and_seed_checks.json',{'source_sha256':fese.sha(__file__),
        'analysis_source_sha256':fese.sha(Path(analysis.__file__)),
        'reference_selection':'Explicit central production r04 references, independently frozen before D cases',
        'index_diagnostics':diagnostics,'rows':rows})
    print(json.dumps({'planned_cases':len(rows),'observed_comparisons':sum(x['status']=='OBSERVED_COMPARABLE_CASES' for x in rows)}))


if __name__=='__main__':main()
