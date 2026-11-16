# Runtime addendum R02 — preserved scientific plan R01

The unknown execution-context interruption observed at 20:45 UTC on 2026-11-16
left the three retry03 attempts without terminal SCF evidence. They are retained
with unknown QE exit codes and separate interruption records. Their incomplete
energies are not accepted. This is not evidence of a hard platform wall limit.

The same-lane engineering helper then ran harmless installed-runtime affinity
probes. Two concurrent default two-rank MPI launchers, with distinct process
identities and isolated temporary directories, each bound their rank zero to
CPU 0 and rank one to CPU 1. Explicit `--bind-to none` succeeded, and each rank
reported the exposed allowed CPU set 0 through 8. Exact commands, stdout/stderr
and terminal receipts are under `runtime/binding_probe/`.

This directly establishes overlapping default affinity in the tested runtime.
It supports explicit no-binding for concurrent jobs; it does not establish the
cause of the interruption or a precise speedup for QE. New attempts use
`mpirun --bind-to none -np 2`, two k pools, and one BLAS/OpenMP thread per rank.
The rank count, k-pool count, executable, libraries, physical input, basis,
k sampling, occupations and electronic tolerance are unchanged. This runtime
choice is recorded in every new command/configuration and in analysis grouping.

New central attempts are `B_a100_FM_r04`, `B_a100_CB_r04` and
`B_a100_STRIPE_r04`. They start from scratch and do not depend on unbacked
interrupted wavefunctions. `batch.py` supervises these workers in one owning
executor session with a maximum of three concurrent jobs. The per-run 1800 s
chosen QE bound remains; it is not described as a platform limit. The original
7200 s initial production budget is still an executor planning decision; any
extension requires an explicit decision at a completed checkpoint.

All original attempts, the frozen plan R01 and earlier source versions remain.
This addendum changes execution placement and interruption handling, not the
source targets, physical model, numerical accuracy goal or assessment rules.
