# Independent GPT FeSe Quantum ESPRESSO experiment

Task `FESE-GPT-WORK-20261116-R01`, owned branch `ai/gpt-fese-20261116-r01`.
This directory is the active independently authored calculation. The repository's
older root material is historical context and was not consumed as a solution.

The project evaluates three FeSe magnetic starts along an explicitly declared
fixed-geometry lattice path. Its source comparison distinguishes the LDA LAPW
magnetism in Subedi et al. from the required PBE pseudopotential QE baseline.
Read `SOURCE_READING.md`, the latest frozen `REPRODUCTION_PLAN` and the final
`SCIENTIFIC_REPORT.md` when present. Plans, successful SCFs and numerically
established conclusions are separate objects.

## Files and evidence

- `fese.py`: geometry/input generator, bounded runner, fail-closed parser, collection.
- `campaigns/`: explicit planned case dictionaries, including pilots and repairs.
- `runs/<id>/`: exact actual input/config, raw outputs, receipts and parsed values.
- `results.json` and `results.csv`: actual evidence rows; null/empty means missing.
- `runtime/`: package/version/probe records and deterministic package recovery.
- `fetch_pseudos.py`: fixed-commit, SHA256-checked common UPF recovery.
- `SOURCE_READING.md`: live original reading receipt and source-to-calculation map.
- `SELF_CHECK.json`: geometry/parser producer checks, not an independent audit.
- `FIRST_OUTCOME.json` and `RESUME.md`, when present: immutable outcome and continuation.

Original copyrighted source PDFs and private project controls are not published
here. Public DOI citations, independently authored source interpretation and
exact input hashes retain the provenance needed to assess this implementation.
Required text evidence is mirrored at natural boundaries to independent storage.
Large QE scratch is retained during execution but is regenerable by a fresh SCF.

## Recover and run

Use a Linux x86-64 cloud machine with compatible MPI, FFTW, BLAS/LAPACK, libc and
Fortran runtime dependencies, or install the QE version recorded in the manifest.
The tested repair uses official Debian 6.7-3+b1 packages without root changes.
The build prints `6.7MaX`; later QE versions require separate validation.

```bash
cd ai-autonomous
python fetch_pseudos.py
python runtime/restore_runtime.py
export QE_RUNTIME_ROOT="$PWD/runtime"
export LD_LIBRARY_PATH="$QE_RUNTIME_ROOT/qe/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
python fese.py run campaigns/pilot.json \
  --pw "$QE_RUNTIME_ROOT/qe/usr/bin/pw.x" \
  --proj "$QE_RUNTIME_ROOT/qe/usr/bin/projwfc.x" --ranks 4
python fese.py analyze
```

Saved attempts are immutable: the runner refuses a reused run ID. For a fresh
replay, copy the selected case to a new campaign JSON and assign a new `run_id`.
Inputs do not depend on previous charge/wavefunction files. Subsequent optimized
runtime settings, if actually tested, are recorded in that attempt's receipt
and runtime addendum; do not silently substitute libraries into an existing run.

## Interpretation rules

Only records with explicit SCF convergence, successful exit and completed output
are `RUN_COMPLETED`. Projection failure leaves the final magnetic pattern
unverified. Energy convergence, full numerical adequacy and source comparison
have their own gates. `relative_to_group_min_mev_fe` compares states only at the
same structure/numerical settings; it is not the reference for an E(a) curve.
Use absolute energy per Fe with a single declared constant for such a curve.

The final-state Fe moment is a Lowdin atomic spin population, distinct from an
LAPW-sphere moment. No effective exchange constants, phonons, superconducting
transition temperatures or experimental ground-state claims are inferred here.

## Software and source attribution

Quantum ESPRESSO: https://www.quantum-espresso.org/ ; version-matched source
QEF/q-e tag `qe-6.7.0`, commit `a34dabb0f802ee27085d6f5cc0127e2c94cd2a93`.
PseudoDojo ONCVPSP PBE scalar-relativistic v0.4.1 exact Fe/Se files, upstream
`PseudoDojo/ONCVPSP-PBE-SR` commit `823b18f7701b6303e0e69114eaa645173f706600`.
See the retained upstream metadata and D. R. Hamann, PRB 88, 085117 (2013).
Scientific originals: DOI `10.1103/PhysRevB.78.134514`,
`10.1103/PhysRevLett.101.057010`, and `10.1103/Physics.1.28`.

The GPT executor was a fresh-context child of the current cloud task. It was
not a separately provisioned persistent native Work page. Exact provider build
identity and monetary cost were not exposed; no paid resources were purchased.
