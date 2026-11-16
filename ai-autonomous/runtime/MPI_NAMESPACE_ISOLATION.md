# MPI namespace and backing-directory investigation

This is an engineering check authored by the same-lane qe_runtime_probe helper. References to its parent below mean the independent GPT executor, not the administrative controller. No active calculation, shared library, input, or existing run record was changed. The parent reported PRTE session collisions and then shared-memory fragment crashes when independent executor sessions reused namespace PIDs. Those reports motivated this check; the stack alone does not conclusively prove filename collision.

## Installed facts and exact overrides

`ompi_info --all` reports Open MPI 5.0.7. The default BTL shared-memory backing directory is `/dev/shm`; OSC shared-memory and RDMA window components also independently default there. The following environment variables were each passed to the actual installed `ompi_info`, which reported the requested path with `data source: environment`:

```text
OMPI_MCA_btl_sm_backing_directory
OMPI_MCA_osc_sm_backing_directory
OMPI_MCA_osc_rdma_backing_directory
OMPI_MCA_shmem_mmap_backing_file_base_dir
```

Evidence: `ompi_info_all.txt` and `ompi_info_isolation_override.txt`. Earlier `prte_info_override.txt` independently confirms `PRTE_MCA_prte_tmpdir_base`. For future jobs, create a unique directory within each run and set TMPDIR, PRTE_MCA_prte_tmpdir_base and the first three OMPI variables to that directory. Keep these settings in each execution receipt.

The generic mmap relocation control is currently zero, so its separate base-directory value is inactive: mmap uses the filename supplied by the caller. Setting only `shmem_mmap_backing_file_base_dir` would not repair BTL's path at this default. The installed coll/sm component has priority zero and no independent directory parameter. Scratch runtime storage was observed as overlayfs; `/tmp` and `/dev/shm` were tmpfs.

## Official version-pinned source check

Six upstream Open MPI v5.0.7 files are saved under `mpi_isolation_sources/`; `SOURCE_MANIFEST.json` binds public URLs, Git blob identities and file SHA256. This is upstream source matching the installed version, not a claim to have audited every downstream patch.

BTL sm constructs its filename from backing directory, node name, UID, MPI job ID and node rank. The filename is not simply the Linux PID. OSC sm and OSC rdma have their own backing directories and job/communicator-derived filenames. coll/sm creates its file within `ompi_process_info.job_session_dir`; unique PRTE session placement therefore covers that path. Generic mmap relocation is conditional on its relocation parameter. CMA uses peer process identifiers learned through the job's exchange; its inspected module does not introduce another backing-directory setting.

These facts are consistent with a namespace/job-identity collision across separate executor sessions sharing storage. They support per-job directory isolation and one same-executor supervisor, without proving that every observed crash had that cause. The official 5.0.7 shared-memory web documentation itself marks its old session-path/ORTE discussion as TODO and wrong, so the installed parameters and pinned source are the relevant evidence for exact path controls.

Sources:
- https://docs.open-mpi.org/en/v5.0.7/tuning-apps/networking/shared-memory.html
- https://github.com/open-mpi/ompi/tree/v5.0.7

## Non-TTY cancellation probe

The enabled executor tools expose exec_command and write_stdin, without a separate cancel-session argument. A harmless, bounded non-TTY Python probe was started and its own tool session received Ctrl-C through write_stdin. The tool returned exit130 immediately. A second dummy probe spawned a child in a new process session; both wrote startup markers, then Ctrl-C again returned immediate exit130. Seven seconds later, the child's scheduled six-second completion marker and both processes' signal-handler markers were absent. The probe source, marker log and exact tool-return receipt are preserved as `non_tty_cancellation_probe.py`, `non_tty_cancellation_probe.jsonl`, and `NON_TTY_CANCELLATION_RECEIPT.json`.

The observed backend handles this Ctrl-C request beyond a normal input byte. Descendant termination is consistent with the marker result, but it is not a portable guarantee of graceful MPI cleanup. No production session was targeted. The parent may interrupt the original owning tool session after preserving evidence and must distinguish a tool/supervisor interruption from an observed pw.x exit. A future supervisor should respond to a filesystem stop request and create per-run CANCEL_REQUEST markers so its workers can clean up and write terminal receipts before the executor session ends.

## Public checkpoint retention

The original official C source copies used for inspection are regenerable upstream material. This checkpoint retains MPI_UPSTREAM_SOURCE_MANIFEST.json with exact public URLs, Git blob identities and SHA256 values; the full source copies remain in the local engineering runtime cache, rather than being treated as irreplaceable result data. The installed-variable excerpts and the observed crash logs are retained in this project.
