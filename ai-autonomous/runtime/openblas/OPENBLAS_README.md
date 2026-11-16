# Optional LP64 OpenBLAS runtime profile

This is a separate opt-in runtime profile. The original QE, ScaLAPACK, reference
BLAS/LAPACK, running pilot and its environment were not modified.

Official Debian trixie package: `libopenblas0-pthread_0.3.29+ds-3_amd64.deb`.
The 6,740,184-byte package matches the published SHA-256
`e3541ee2c956c64383054ba116fb6ef86bbaf40035d64e1795185029fdcf0807`.
Checksum source:
https://packages.debian.org/trixie/amd64/libopenblas0-pthread/download

The package declares `INTERFACE64=0`, `USE_THREAD=1`, `USE_OPENMP=0`. Its ordinary
Fortran symbols `dgemm_`, `dsyev_` and `dsygvx_` are present. Loader inspection shows
that all QE libraries resolve with this profile. This is ABI/loader evidence;
performance and scientific output equivalence remain for the executor's new pilot.

## Explicit activation for a new run

```bash
export QE_RUNTIME_ROOT=/workspace/scratch/47b868c7a5c6/gpt_fese_r01/runtime
export LD_LIBRARY_PATH="$QE_RUNTIME_ROOT/openblas/usr/lib/x86_64-linux-gnu/openblas-pthread:$QE_RUNTIME_ROOT/qe/usr/lib/x86_64-linux-gnu"
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
"$QE_RUNTIME_ROOT/qe/usr/bin/pw.x" -in /absolute/path/to/new/input.in
```

Use a new run ID and retain the actual runtime-profile hash. The executable hash
alone is identical to the reference-BLAS run and does not identify its libraries.

## Recovery

Download the exact package from:

https://deb.debian.org/debian/pool/main/o/openblas/libopenblas0-pthread_0.3.29+ds-3_amd64.deb

Verify its SHA-256 above before extracting with `dpkg-deb -x PACKAGE.deb openblas`.
No package-maintainer script or system alternatives update is needed. Dependency
requirements are compatible with the observed Debian 13 cloud runtime; another
host must independently verify them.

`OPENBLAS_RECEIPT.json`, `pw_ldd_openblas.log`, `openblas_symbols.log` and
`openblas_package_metadata.log` preserve the package identity and actual checks.
The Python-bundled NumPy/SciPy OpenBLAS libraries were not reused because their
Fortran symbols are renamed and are not drop-in replacements for QE's LP64 ABI.
