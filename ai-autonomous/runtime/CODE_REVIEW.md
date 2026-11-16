# Producer code self-check

Scope: the GPT lane's `fese.py` and `REPRODUCTION_PLAN_DRAFT.md`, plus official
QE 6.7 source for parser and RNG behavior. This is assistance inside the producing
lane, **not an independent scientific audit**. No other lane was inspected. The
reviewer did not edit `fese.py` or any running scientific input.

The initial code inspected had SHA-256
`d5a91f1c681fe168fa10f7d80e2db484dea5d8acc34deb13b6775dd41444b175`.
After issues were sent to the executor, an updated source was inspected and the
checks were repeated at SHA-256
`b55c18dbebc649310ac5da4ce7e0733ad8157987d654b6ad682b3dd1f1386abe`.
`CODE_REVIEW_CHECKS.json` binds the latter snapshot and observed checks. Any later
revision needs its own acceptance decision; this note does not certify it.

## Geometry, normalization and parsing checks

- The row-vector supercell has determinant `2*a*a*c` and contains four Fe and four
  Se. Transforming the documented two-Fe tetragonal positions yields the listed
  fractional positions, modulo lattice translations. All four nearest Fe-Se
  distances at the inspected geometry agree.
- Periodic nearest-neighbor enumeration gives each Fe four parallel neighbors in
  FM, four antiparallel neighbors in CB, and two parallel plus two antiparallel
  neighbors in stripe. The second stripe orientation and global spin inversion
  are correctly accepted by the classifier.
- The conversion `(E_cell - E_ref_cell)*RY_EV*1000/4` gives meV/Fe for the invariant
  four-Fe cell. The report correctly distinguishes a per-structure minimum from
  a common reference for an energy-versus-lattice curve.
- Synthetic negative tests exclude an appended incomplete invocation, explicit
  unconvergence, nonzero process exit, a trailing QE error and a second failed
  SCF stage. A total-energy line or `JOB DONE` alone does not qualify.
- The projection parser matches the actual collinear output format in the
  version-pinned `PP/src/projwfc.f90`, subroutine `print_lowdin`, including the
  per-atom `polarization = up-down` field. A formatted eight-atom fixture parsed
  correctly. This is a parser check, not a substitute for checking actual outputs.

## Actionable issues

| Priority | Issue and consequence | Required action/status at the inspected revision |
| --- | --- | --- |
| Before accepting interrupted-run tables | `analyze()` uses `NOT_RUN` whenever `parsed.json` is absent, even if the receipt or new execution record says `RUNNING`. An interrupted or currently executing attempt can be mislabeled as never launched. | Read the receipt/execution status in this branch. Preserve a distinct running/interrupted/unknown completion state and null observables; do not guess whether an old process is still alive. |
| Before accepting final-state labels | `final_state()` returns `NM_ENFORCED_NSPIN1` for any NM input, including a failed or unconverged job. | First gate a **final** magnetic label on successful SCF completion. Keep `nspin=1` as an imposed input condition even when no final state was established. |
| Before interpreting magnetic ordering | `RUN_COMPLETED` describes SCF completion; magnetic projection can be absent or failed. Such rows currently participate in numerical group minima. | Retain their energy evidence but carry an explicit final-state verification/interpretation eligibility flag. A lowest-energy row with unknown topology must not be presented as a verified named magnetic state. |
| Before a source revision is discarded | `source_sha256` records the mutable script's bytes, but `prepare()` does not itself archive that source. | Bind every recorded source hash to an immutable Git revision or a per-run source snapshot. Preserve the old implementation of already executed attempts before later edits. Exact QE input remains independently sufficient for a direct solver replay, but it does not replace generator/parser lineage. |
| Reproducible launch | A relative `--pw` or `--proj` path can resolve relative to the caller for hashing but relative to the run directory for execution. Bare `projwfc.x` can also lack a hash despite being found on PATH. | Resolve both executables once through `shutil.which`/absolute paths and use those same resolved paths for hashing and launching. The current absolute paths supplied by the executor avoid this issue for those invocations. |
| Low priority resource semantics | `RUSAGE_CHILDREN.ru_maxrss` is the process's cumulative child high-water mark. It is not a fresh per-case RAM measurement. | Keep the existing qualification and label this value as a cumulative/high-water observation, not each case's isolated peak RAM. |

The executor already addressed the following issues in the second inspected
revision: launch-time `RUNNING`/command/timestamp/PID records; numerical shared
library profile and `projwfc.x` identity; grouping by `nbnd` and `conv_thr_ry` as
well as the runtime profile. These changes are observed source changes, not
claims that the entire later campaign has been validated.

Additional choices needing explicit interpretation, rather than code repair:
symmetry can retain the initialized collinear subspace; Lowdin moments are
partition-dependent and are not the paper's LAPW-sphere observable; a completed
SCF is not a convergence study; changing the BLAS implementation must be recorded
and must not retroactively change the first pilot's provenance. The plan already
acknowledges these scientific limitations.

## Version-specific evidence

`PP_Doc_INPUT_PROJWFC.def` is the official QE 6.7.0 input definition at commit
`a34dabb0f802ee27085d6f5cc0127e2c94cd2a93`, SHA-256
`e37d4f259f51ec7585f3c3c65e4c4a3af37f7b3ecb9c30e78873342e71b25cd6`.
The upstream source files, their hashes/URLs, and failed speculative-path fetches
are preserved in `qe_source_probe.json` and `qe_source_probe_extra.json`.

Random initialization details and the exact distinction between a source-derived
default seed and runtime-observed state are recorded separately in
`RNG_PROVENANCE.md`.
