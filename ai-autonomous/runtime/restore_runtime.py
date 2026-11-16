#!/usr/bin/env python3
"""Recover the verified Debian QE 6.7 user-space runtime without root privileges.

Inputs: the two fixed HTTPS package locations below; no scientific input data.
Outputs: exact .deb caches and the unpacked ``qe/`` directory next to this script.
Dependencies: Python >= 3.8, dpkg-deb, and ABI-compatible Debian runtime libraries
listed in pw_ldd_after.log. This does not install or alter system packages.

Example: python restore_runtime.py
The fixed SHA-256 values were independently checked against official Debian
package download pages during the 2026-11-16 capability probe.
"""
from pathlib import Path
import hashlib
import subprocess
import urllib.request

PACKAGES = [
    (
        "https://deb.debian.org/debian/pool/main/e/espresso/quantum-espresso_6.7-3+b1_amd64.deb",
        "44f9f38afc08fa53148cdddf8936464ba992b894a0843cc4aaf8749809b54bca",
    ),
    (
        "https://deb.debian.org/debian/pool/main/s/scalapack/libscalapack-openmpi2.2_2.2.2-1_amd64.deb",
        "19edff3e0d4d27b350965246ac93de8bc0328fa3c42f1b9a93048873ec2aeb7d",
    ),
]


def restore(destination: Path) -> None:
    """Download or verify package bytes, then extract them below destination.

    A checksum mismatch raises ValueError before extraction. Existing files are
    accepted only if their exact bytes match; partial downloads are kept under a
    .part name and never treated as a package. No package-maintainer scripts run.
    """
    destination.mkdir(parents=True, exist_ok=True)
    for url, expected in PACKAGES:
        package = destination / url.rsplit("/", 1)[1]
        if not package.exists():
            partial = package.with_suffix(package.suffix + ".part")
            with urllib.request.urlopen(url, timeout=60) as response, partial.open("wb") as stream:
                while block := response.read(1024 * 1024):
                    stream.write(block)
            if hashlib.sha256(partial.read_bytes()).hexdigest() != expected:
                raise ValueError(f"Downloaded checksum mismatch: {package.name}")
            partial.rename(package)
        if hashlib.sha256(package.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Cached checksum mismatch: {package.name}")
        subprocess.run(["dpkg-deb", "-x", str(package), str(destination / "qe")], check=True)
        print(f"Verified and extracted {package.name}")


if __name__ == "__main__":
    restore(Path(__file__).resolve().parent)
