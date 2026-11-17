#!/usr/bin/env python3
"""Pack terminated QE raw attempts as a Drive ZIP and a reversible small-text backup.

Python 3.11+ standard library. Example from work root:
    python code/checkpoint.py PILOTS_R01 jobs checkpoints --prefix pilot-
The JSON stores per-file compressed base64 bytes and a SHA-256 after decoding.
To independently verify a downloaded pair, use --verify with both output files.
"""

import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


RUN_FILES = ("attempt.json", "pw.in", "pw.stdout", "pw.stderr", "CRASH", "work-stop.json")


def pack(work, jobs, name, prefix):
    """Capture frozen exact bytes from terminal jobs and explicitly named controls."""
    paths = []
    for attempt in sorted(jobs.glob(f"{prefix}*/attempt.json")):
        record = json.loads(attempt.read_text())
        if (record["state"] not in {"PROCESS_EXITED", "LAUNCH_FAILED"} and
                not (attempt.parent/"work-stop.json").is_file()):
            continue
        paths.extend(p for filename in RUN_FILES if (p := attempt.parent / filename).is_file())
    for pattern in ("apt-update.*", "blas-install.*", "qe-install.*", "qe-openblas.ldd",
                    "qe-source-files.txt", "pilots*.*", "package-network-probe.log",
                    "SOURCE_ACCESS_R01.md", "CAPABILITY_RECEIPT_R01.json", "primary.command",
                    "primary.started"):
        paths.extend(p for p in (work / "control").glob(pattern) if p.is_file())
    return sorted(set(paths))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_pair(paths, root, archive, backup):
    """Preserve the same bytes in two independently addressable artifact formats."""
    records = {}
    with ZipFile(archive, "w", compression=ZIP_DEFLATED, compresslevel=6) as out:
        for file in paths:
            key = file.relative_to(root).as_posix()
            data = file.read_bytes()
            out.writestr(key, data)
            records[key] = {"size_bytes": len(data), "sha256": digest(data),
                            "encoding": "gzip+base64", "data": base64.b64encode(
                                gzip.compress(data, compresslevel=6, mtime=0)).decode("ascii")}
    packed = (json.dumps({"schema": 1, "files": records}, indent=2) + "\n").encode()
    if len(packed) > 1048576:
        raise ValueError("Independent backup exceeds 1 MiB. Select one narrower immutable stage.")
    backup.write_bytes(packed)


def verify_pair(archive, backup):
    """Independently decode every exact member and compare with the primary ZIP."""
    contents = json.loads(backup.read_text())["files"]
    with ZipFile(archive) as bundle:
        if set(contents) != set(bundle.namelist()) or len(contents) != len(bundle.namelist()):
            raise ValueError("Inventories differ")
        for key, item in contents.items():
            restored = gzip.decompress(base64.b64decode(item["data"], validate=True))
            if (restored != bundle.read(key) or len(restored) != item["size_bytes"]
                    or digest(restored) != item["sha256"]):
                raise ValueError(f"Exact restoration failed for {key}")
    print(f"Verified {len(contents)} exact files")
    print(f"{archive.name} {digest(archive.read_bytes())}")
    print(f"{backup.name} {digest(backup.read_bytes())}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", nargs="?")
    parser.add_argument("jobs", type=Path, nargs="?")
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("--prefix", default="")
    parser.add_argument("--verify", type=Path, nargs=2)
    args = parser.parse_args()
    if args.verify:
        verify_pair(*args.verify)
        return
    work = Path.cwd()
    archive = args.output / f"{args.name}.zip"
    backup = args.output / f"{args.name}_BACKUP.json"
    if archive.exists() or backup.exists():
        raise SystemExit("Checkpoint name already exists")
    paths = pack(work, args.jobs.resolve(), args.name, args.prefix)
    write_pair(paths, work, archive, backup)
    verify_pair(archive, backup)


if __name__ == "__main__":
    main()
