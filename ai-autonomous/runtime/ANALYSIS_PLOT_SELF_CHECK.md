# Analysis/plot producer self-check

This is assistance within the GPT production lane, not an independent audit. Only `ai-autonomous/analysis_plot.py` was implemented; no scientific input, run record, or `fese.py` was edited by this subtask. The parent owns the persistence checkpoint.

## Exact interface

Run from the `ai-autonomous` directory:

```bash
python analysis_plot.py --production-ids 'B_*' --comparison-ids 'B_*' 'C_*' --target-mev-fe 1 --outdir analysis/r01
```

`--production-ids` and `--comparison-ids` accept one or more exact IDs or quoted glob patterns. Actual configuration values determine compatibility; names do not set cutoffs or meshes. `--energy-reference-run ID` selects a completed, eligible point within the production selection. Without it, the minimum observed energy per Fe in that exact selection is the one common zero; its ID and energy are explicitly recorded. If the suggested central baseline reference is absent, the default remains a disclosed alternative and is not a per-a minimum. `--root` overrides the run-data directory. Use a fresh output directory to preserve an earlier analysis.

Outputs comprise verified records, JSON/CSV production points, JSON/CSV single-setting convergence pairs, JSON/CSV changes in magnetic energy differences, four PNG/SVG figures (with table pagination as needed), and `analysis_manifest.json`. Inputs are read-only. Protected run/input directories cannot be selected as outputs. Existing unrelated output files are not deleted or claimed as regenerated artifacts.

## Implemented integrity and interpretation gates

Raw SCF logs are reparsed with the adjacent, hash-recorded `fese.py`. Actual per-run configurations and receipts take precedence over a stale `results.json` index. A successful process, explicit SCF convergence, a final energy and completed output are all required. Config, input and raw SCF hashes must match the run receipt. Missing metadata, damaged records and unfinished runs are visible with exclusion reasons. Magnetic diagnostics additionally require successful projection, completed output and matching raw projection hash. The known QE build's seed default is explicitly labeled source-derived, with unobserved per-rank evolving streams disclosed.

Each accepted convergence pair holds a/c/z, initial state, starting polarization, model/pseudopotential/runtime identity, starting potential/wavefunctions and other settings fixed, while changing exactly one setting axis. Coupled wavefunction/density cutoffs require a fixed ratio. Changed or unverified final states cannot produce a same-state `convergence_delta_mev_fe`; their qualified observed solution shift is retained. Changes in magnetic energy differences require matched refinements and verified unchanged final states, separate from the total-energy drift. A threshold pass is one observed refinement step, not a numerical error bound.

Production E(a) uses one common constant in meV/Fe and measured scatter points only. There is no interpolation, EOS fit or inferred optimum. All signed projected Fe moments are retained in the data table; the figure shows their mean absolute value with its projection caveat. Missing diagnostics are not plotted as zero. Pilot IDs/stages, including an exact selection of P004, remain excluded.

## Actual self-check evidence

Command executed from the lane root:

```bash
python ai-autonomous/analysis_plot.py --outdir runtime/analysis_plot_selfcheck --target-mev-fe 1
```

Analysis timestamp: `2026-11-16T20:09:50.158012+00:00`.
Analysis source SHA256: `33efffb1547a3e07a5b71ee90e3eb744b1869aa8711b732c0b4b5bdbb74694af`.
Parser source SHA256: `89f54f8ba18cc425aee3b0ddaeeae9453f8209e4ddde11479f2dad967110ce66`.

The actual snapshot contained 7 records, 2 of which passed raw-record energy gates. The default B/C selection yielded no eligible production points and no convergence pairs. Completed pilots did not enter production.

| Run | Observed status | Raw-record energy eligible |
|---|---|---|
| B_a100_CB | RUNNING | False |
| B_a100_FM | RUN_FAILED | False |
| B_a100_STRIPE | RUN_FAILED | False |
| P001_stripe_60_k443 | RUN_FAILED | False |
| P002_stripe_openblas_serial | RUN_FAILED | False |
| P003_stripe_openblas_pool2 | RUN_COMPLETED | True |
| P004_stripe_gamma_pipeline | RUN_COMPLETED | True |

Checks passed: every one of 15 artifact hashes and byte counts matched the manifest; all three empty JSON tables were empty lists and CSVs retained their headers; the common zero and fitted minimum were null; missing-values-as-zero was false; exact P004 selection was rejected. The empty E(a) and convergence PNGs were visually inspected for legibility and unclipped labels.

## Remaining validation boundary

No invented energies or relabeled pilot data were introduced. There were no eligible B/C production/refinement observations in this self-check, so populated production figures, positive matched-pair detection, and final-state-change display are implemented but have not yet been exercised on actual B/C results. Re-run the above command after real records become available and inspect the populated figures and pair tables before interpreting them. The full changing run tree was not atomically snapshotted by this script; terminal per-run hashes are the integrity gate, and the parent should archive a completed analysis at a natural checkpoint.
