# Independent decisions and changes

## Before the first pilot

Derived one common four-Fe cell and fixed-c/fixed-z in-plane scan from the original sources. PBE common pseudos are mandatory; no numerical target from LaFeAsO is transferred. Declared 1 meV/Fe energy-difference accuracy goal before any computed result. Pilot 60 Ry is below the subsequently read 90 Ry normal recommendation in the common pseudo metadata and is therefore explicitly a capability test, not an adequate production basis.

## Runtime pilot changes, before production freeze

- P001: reference BLAS, four MPI processes with FFT communication; QE stopped at its 360 s budget after 370.31 s wall, exit 2, no SCF convergence. JOB DONE did not qualify it as a completed result.
- P002: same physical/numerical input, user-space OpenBLAS and one MPI rank; stopped at the same budget after 369.24 s, exit 2, no SCF convergence. This does not demonstrate energy equivalence or successful convergence.
- P003: same physical/numerical pilot, OpenBLAS, two ranks and two k pools; allow 1800 s to measure whether a full self-consistent solution is attainable with less FFT communication. Started from atomic density, not the unprotected previous scratch. Production remains unfrozen.
- P004: a separately identified Gamma-only pipeline pilot, otherwise the same provisional 60 Ry settings, is admitted to test SCF-to-projection-to-parser completion economically while P003 runs. Gamma sampling is unsuitable as evidence of Brillouin-zone convergence in this metal. It cannot satisfy the declared 1 meV/Fe accuracy goal. It is not silently substituted for the proposed primary scan. A real complete pipeline test remains valuable even if the denser production campaign is too costly in this cloud allocation. Both attempts may overlap; report their real timing and do not infer isolated benchmark speed from overlapping jobs.

No scientific value was fitted or changed to approach a paper answer. All failures and original source versions are retained. Any eventual resource-limited stop must distinguish the executor's declared budget from an unobserved hard platform timeout.

## Producer implementation repairs

Same-lane code review identified and prompted persistent RUNNING/command records, exact numerical-library and projwfc identity, compatibility grouping including band count and electronic tolerance, incomplete-run status propagation, final-state gating on SCF completion, and immutable per-version source snapshots. P001's initial source was recovered by deterministically reversing the two recorded patches; its exact pre-run SHA256 matched. Later attempts snapshot source before launch.

CP01 integrity readback detected text-reader CRLF normalization in a CSV and a package checkout log. Both were repaired from the immutable exact-byte archive and all 61 required Git objects reverified. Subsequent snapshots read bytes and decode UTF-8 without newline normalization. Derived CSV output now specifies LF explicitly. Neither repair changes physical data.

## Production launch infrastructure repair (2026-11-16 20:10 UTC)

The first concurrent central launches used isolated process namespaces but shared /tmp. B_a100_FM and B_a100_STRIPE exited 213 before any QE stdout, with PMIX_ERR_EXISTS and prte_session_dir returned Exists. Their original directories and logs remain immutable. B_a100_CB launched normally. The runner now assigns TMPDIR and PRTE_MCA_prte_tmpdir_base to each run/stage directory; installed prte_info confirms the variable. Retry IDs B_a100_FM_r02 and B_a100_STRIPE_r02 preserve the same physical/numerical settings, with execution isolation only. This is a demonstrated recoverable infrastructure collision, not a scientific result or resource impossibility.

The first isolation repair was incomplete: B_a100_FM_r02 and the original B_a100_CB then received SIGSEGV inside mca_btl_sm_poll_handle_frag; B_a100_STRIPE_r02 remained stalled at input and is retained under its bounded external timeout. Installed ompi_info shows btl_sm_backing_directory defaults to shared /dev/shm. The runner now also isolates OMPI_MCA_btl_sm_backing_directory per attempt/stage. Retry03 preserves all scientific settings; no results from collision-affected attempts are accepted. This failure and repair are infrastructure provenance.

The stalled B_a100_STRIPE_r02 owning tool session was interrupted at 2026-11-16T20:16:43.665986+00:00 after a bounded dummy established the non-TTY Ctrl-C behavior. Tool exit130 was observed; QE exit status is explicitly unknown, no fabricated final SCF receipt is used, and the last live pw_execution.json plus separate SUPERVISOR_INTERRUPTION.json remain. Retry03 cases are progressing past input. Later code adds a CANCEL_REQUEST polling route with child-process-group termination; a real dummy-process cancellation completed in5.01s with declared code125, separate from scientific runs.

Source-level qualification: installed OpenMPI5.0.7 btl_sm filenames combine node, UID, jobid and node-rank, rather than PID directly. The crash locations, reused tool namespace PIDs and success after isolating backing paths support a runtime-identity/file-collision diagnosis, but no contemporaneous MPI jobid/file mapping was captured; direct causality is therefore inferred. The source evidence and uncertainty are retained in runtime/MPI_NAMESPACE_ISOLATION.md.
