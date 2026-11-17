# FeSe lattice scan with Quantum ESPRESSO

This directory contains the editable source of an independently executed fixed-geometry FeSe DFT study. See REPRODUCTION_PLAN_R01.md for the pre-sweep choices, comparison targets and acceptance criteria. The four-Fe periodic cell accommodates ferromagnetic, checkerboard and stripe initial states. A separate explicit non-spin-polarized calculation supplies the paper comparison reference at the anchor.

## Environment

The run used Debian trixie amd64, PWSCF 6.7MaX (Debian quantum-espresso 6.7-3+b1), Open MPI 5.0.7, ScaLAPACK 2.2.2-1, serial OpenBLAS 0.3.29+ds-3, Python 3.12.14 and Matplotlib 3.10.8 for plotting. The workflow uses standard Python 3.11+ for launch, parse, comparison and integrity checks. A compatible Linux MPI host can use its regular installation. An exact package-based reconstruction recipe and verified digests are in ENVIRONMENT.md.

Retrieve the original UPF files at the fixed [PseudoDojo commit](https://github.com/PseudoDojo/ONCVPSP-PBE-SR/tree/823b18f7701b6303e0e69114eaa645173f706600). The public endpoints served bytes matching the common packet in this runtime.

```bash
mkdir -p common
upstream=https://raw.githubusercontent.com/PseudoDojo/ONCVPSP-PBE-SR/823b18f7701b6303e0e69114eaa645173f706600
curl --fail --location "$upstream/Fe/Fe_std.upf" -o common/Fe_std.upf
curl --fail --location "$upstream/Se/Se_std.upf" -o common/Se_std.upf
sha256sum -c PSEUDOPOTENTIAL_SHA256SUMS.txt
```

The runner verifies the exact filenames and hashes before starting. Original PDFs and runtime account/control records are outside this public source tree. Bibliographic locations and source roles appear in the plan and source access receipt.

## Execute

Run from this directory, using fresh distinct output directories for any independent repeat.

```bash
python fese.py primary_R01.json jobs --pseudo-dir common --pw pw.x --ranks 2 --parallel 3
python fese.py B1_R01.json jobs --pseudo-dir common --pw pw.x --ranks 2 --parallel 1
python fese.py B2_R01.json jobs --pseudo-dir common --pw pw.x --ranks 2 --parallel 1
python fese.py K1_R01.json jobs --pseudo-dir common --pw pw.x --ranks 2 --parallel 2
python fese.py S1_R01.json jobs --pseudo-dir common --pw pw.x --ranks 2 --parallel 2
python fese.py REPLAY_R01.json jobs --pseudo-dir common --pw pw.x --ranks 1
```

The sensitivity matrix can run with spare capacity during the main scan. For multiple groups running concurrently, the sum of simultaneous MPI ranks should fit the machine. The executable path, commands, input digest, attempt timestamps, stdout/stderr and terminal status are recorded per case. Reference-BLAS pilots and the repeat under serial OpenBLAS use their separate matrices and distinct IDs. Read ENVIRONMENT.md before trying to time-match the cloud run.

Make an analysis directory from all records, including failures and missing assessments.

```bash
python analysis.py jobs derived pilots.json pilots_openblas.json primary_R01.json \
  B1_R01.json B2_R01.json K1_R01.json S1_R01.json REPLAY_R01.json
python compare.py derived/results.json derived/comparisons.json
python plot.py derived/results.json derived/figures
python validate.py jobs
```

`validate.py` expects the supplied actual stopped and converged pilot attempts. With the raw checkpoint placed under `jobs`, it exercises the same parser that produced the main tables. The analysis sorts all lattice points by increasing a. Lines connect available points with identical initialization, and a marker annotation identifies moment collapse or another final state. A blank point conveys missing usable evidence.

## Read the data

- `results.json` and `results.csv` hold one row per planned or observed attempt, including unmatched or missing results. Energy and moment fields are null when unverified. `path`, cell inputs, density cutoff and smearing fields make the comparisons inspectable.
- `total_energy_ry_cell` is the QE SCF result as printed, including the chosen smearing functional. `smearing_term_ry_cell` preserves QE's printed correction term separately. The exact division is four Fe atoms per cell. `relative_energy_mev_fe` uses the lowest eligible result in each identical geometry/numerical-setting group. `reference_run_id` identifies that result.
- `fe_weighted_moments_muB` is the last SCF report for the four Fe sites, in input order. `absolute_spin_muB_cell` is the cell integral of the magnitude of spin density. The two quantities have different integration domains. The `weighted_radii_bohr_by_species` values are associated with QE species indices in `pw.in`.
- `comparisons.json` expresses signed energy differences as first minus second. Shift estimates require that both computations retain the same two final-state classes. The additive sensitivity envelope is empirical and does not bound untested effects.
- `pw.in`, `pw.stdout`, `pw.stderr` and `attempt.json` are the principal exact attempt records. An SCF must pass explicit output acceptance even if the process returned zero. The human-readable report discusses the final-state matches and physical limits.

## Resume and storage

Restore the latest independent checkpoints and confirm digests before running anything. Inspect live Work tool sessions first, because the process IDs in `attempt.json` are specific to their execution namespace. The runner preserves every existing case directory and skips its ID. To resume a missing case, run the same matrix after restore and confirm no matching live process exists. To retry a failed or interrupted case, copy its configuration to a new matrix with a new ID and preserve the earlier directory. A file whose status says RUNNING with no verified process is an interrupted or unknown attempt until reconciled.

Primary and reference figures are regenerated from `results.json` and the plotting source. Most SCFs do not save portable wavefunctions. Temporary wavefunctions remain scratch. Any deliberate warm start records exact file digests and parent evidence. Regenerate those files with the archived parent input before recomputing a warm-start descendant when they are unavailable. This preserves reproducibility while avoiding a requirement for long-term binary restartability.
