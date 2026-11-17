# Computational environment and rootless Debian recipe

Published Debian trixie snapshot dated 2026-11-03 was used for signed APT metadata, the QE executables and two auxiliary performance libraries. Download the listed package versions and extract them without modifying the host. The optional QE data package was present. Host system libraries still provide glibc, FFTW, Open MPI and related dependencies, so reproduce those via the same Debian release where possible.

```bash
mkdir -p debs
cd debs
apt-get download quantum-espresso=6.7-3+b1 libscalapack-openmpi2.2=2.2.2-1 \
  quantum-espresso-data=6.7-3 libopenblas0-serial=0.3.29+ds-3
for package in ./*.deb; do dpkg-deb -x "$package" extracted; done
lib="$PWD/extracted/usr/lib/x86_64-linux-gnu"
export LD_LIBRARY_PATH="$lib/openblas-serial:$lib"
export PATH="$PWD/extracted/usr/bin:$PATH"
export HWLOC_COMPONENTS=-linux
```

Verify the downloaded package checksums.

```text
44f9f38afc08fa53148cdddf8936464ba992b894a0843cc4aaf8749809b54bca  quantum-espresso_6.7-3+b1_amd64.deb
19edff3e0d4d27b350965246ac93de8bc0328fa3c42f1b9a93048873ec2aeb7d  libscalapack-openmpi2.2_2.2.2-1_amd64.deb
f6b6ca4c800730e10698a0234fae0cb4dee11807f173bb0f943464e9cffe77c1  quantum-espresso-data_6.7-3_all.deb
edd238e774562e37cb67e01a8698ed4d33b5ba848ca2000c4237f4df124349d1  libopenblas0-serial_0.3.29+ds-3_amd64.deb
bcd96679f8a8b77d1a26abe8cba9f34a17f8aef7ad2f6688c6d11fb8cf16ec6f  extracted/usr/bin/pw.x
```

The original pilots used the system reference BLAS. For that profile omit the OpenBLAS subdirectory from LD_LIBRARY_PATH and retain the ScaLAPACK directory. Work used one MPI process per k-point pool, with one library thread per process. The report includes actual rank-slot time and observed concurrency. Nominal allocated CPU count is distinct from charged CPU time. The Work cloud surface did not expose its monetary charge or hard task-lifetime allowance.

The executable's run banner was PWSCF v.6.7MaX. A version probe passing only -help prints the banner then attempts to parse stdin under this build, and its expected namelist failure was recorded. Converged ordinary runs independently confirm the executable and dependencies. Diagnostics came from the QE source archive corresponding to this release, Debian espresso_6.7.orig.tar.gz (SHA-256 8f06ea31ae52ad54e900a2f51afd5c70f78096d9dcf39c86c2b17dccb1ec9c87).
