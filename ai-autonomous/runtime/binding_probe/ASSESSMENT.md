# CPU binding investigation: installed Open MPI 5.0.7

## Observed result

Two concurrent harmless launchers using the default binding policy both selected the same CPU masks. Their launcher PIDs were 5 and 6 within one probe supervisor, and their four child PIDs were distinct. Each launcher had its own session/shared-memory backing directory. This directly demonstrates that moving separate mpirun invocations into one executor namespace does not itself allocate disjoint CPUs to those jobs.

| Probe | Rank 0 Linux affinity | Rank 1 Linux affinity | Exit |
|---|---|---|---|
| Default A | {0} | {1} | 0 |
| Default B, concurrent with A | {0} | {1} | 0 |
| Explicit `--bind-to none` | {0,1,2,3,4,5,6,7,8} | {0,1,2,3,4,5,6,7,8} | 0 |

The supervisor itself had the full listed nine-CPU affinity mask. `--report-bindings` reported the corresponding core bindings for default launches and reported the explicitly unbound ranks as unbound or bound to all available processors. The application independently read its actual Linux mask with `os.sched_getaffinity(0)`.

The installed `prte_info --all` output was preserved. Its default mapping parameter is blank, so that listing alone does not identify the launch-time binding decision. Open MPI's version-specific documentation describes core binding for jobs of at most two processes, package binding for larger jobs, and no binding when oversubscribed. It explicitly supports `--bind-to none`. The installed launch probes above establish the relevant behavior here.

## Exact commands and evidence

The Python probe program prints rank, local rank, PID and CPU affinity, then sleeps for one second to establish overlap. It does not import an MPI library, run QE or perform a numerical benchmark. The complete program and command arrays are saved in `probe_binding.py` and the observation receipt.

```text
mpirun --report-bindings -np 2 <python> -c <affinity probe>
mpirun --report-bindings --bind-to none -np 2 <python> -c <affinity probe>
```

The observation directory is `observation_20261116T205155Z_930fb0e2`. It contains the exact receipt and separate stdout/stderr for default_A, default_B and explicit_none. All recorded raw-output SHA256 hashes were independently rechecked. `ASSESSMENT.json` binds the receipt hash and machine-readable conclusions.

For each launch, TMPDIR, PRTE_MCA_prte_tmpdir_base, OMPI_MCA_btl_sm_backing_directory, OMPI_MCA_osc_sm_backing_directory and OMPI_MCA_osc_rdma_backing_directory pointed to that probe's own unique directory. No running job or scientific configuration was modified.

## Assessment and limits

Explicit `--bind-to none` is supported and worked in the actual installed runtime. For concurrent independent two-rank jobs, it removes the demonstrated restriction of every job to the same two CPU IDs and lets the OS schedule each rank across the allowed mask. Keep the established one-thread-per-rank settings and record the exact launcher command. A deliberately partitioned binding policy could also avoid overlap, but that would require an additional tested CPU-allocation design; it was not evaluated here.

The probes establish overlapping default affinity and the effect of disabling binding. They do not measure a QE speedup, prove that binding explains the entire previously observed slowdown, or explain the unknown context interruption. Their elapsed times include the intentional sleep and must not be used as throughput measurements. Linux affinity IDs identify allowed logical CPUs, not guaranteed dedicated physical cores or a measured resource quota.

All launches emitted `hwloc/linux: failed to find sysfs cpu topology directory, aborting linux discovery.` This is preserved in stderr. Although detailed hardware discovery was unavailable, the independent sched_getaffinity readings establish the actual masks. No additional hardware topology or platform time limit is inferred.

Official reference: https://docs.open-mpi.org/en/v5.0.7/man-openmpi/man1/mpirun.1.html (Quick Summary and mapping/ranking/binding options).
