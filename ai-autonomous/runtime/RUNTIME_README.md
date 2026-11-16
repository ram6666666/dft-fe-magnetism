# QE runtime capability repair

The cloud environment's system package manager could not install QE: its package
index did not contain the package, the system dpkg lock was unavailable to the
unprivileged user, and sudo was absent. Those failures are retained in the probe
logs (the original install log is in the parent executor's private directory).

The working route uses standard `dpkg-deb -x` extraction, entirely inside this
runtime directory. It downloaded the official Debian trixie `quantum-espresso`
6.7-3+b1 amd64 package and its missing ScaLAPACK runtime library. Both package
SHA-256 values match Debian's separately retrieved published checksums:

- https://packages.debian.org/trixie/amd64/quantum-espresso/download
- https://packages.debian.org/trixie/amd64/libscalapack-openmpi2.2/download

No system files, other lanes, global controls, or scientific inputs were changed.
The installer creates no paid resources. About 51.1 MB of package bytes were
downloaded. Files and actual hashes are in `RUNTIME_RECEIPT.json`.

## Use

From the directory containing this file:

```bash
export QE_RUNTIME_ROOT="$PWD"
export LD_LIBRARY_PATH="$QE_RUNTIME_ROOT/qe/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export OMP_NUM_THREADS=1
"$QE_RUNTIME_ROOT/qe/usr/bin/pw.x" -in /absolute/path/to/input.in
# MPI, when chosen by the scientific executor:
mpirun -np 2 "$QE_RUNTIME_ROOT/qe/usr/bin/pw.x" -in /absolute/path/to/input.in
```

`pw.x` reports **PWSCF v.6.7MaX**. Open MPI reports **5.0.7**. The exact version
identifier is retained rather than relabeled as a newer QE release. Use the
QE 6.7 input definitions, not later version defaults without checking.

## What has been verified

The ELF loader resolves every required shared library after setting the library
path above. The executable started through MPI at one and two ranks and reached
the QE input parser. `-h` is not treated as a help-and-exit request by this build:
the version probes received empty stdin, reported missing `&control`, and exited
with status 1. These are version/startup probes, **not completed SCF runs**.
The scientific executor must perform its own actual pilot calculation.

The startup logs include a missing sysfs topology warning from hwloc and an
unavailable UCX VFS socket warning. Neither prevented the observed parser
startup. They were preserved rather than silently removed.

## Recovery and retention

Run `python restore_runtime.py` to verify/download the two frozen package files
and extract them without root permissions. This requires compatible system
libraries; `pw_ldd_after.log` records the runtime library mapping actually used.
The package archives and extracted binaries are retained in this session. They
are reproducible software dependencies, not irreplaceable scientific outputs;
this directory by itself is not a durable cross-session backup claim.

This agent performed engineering repair only. It selected no scientific
parameters and generated no scientific result or model comparison.
