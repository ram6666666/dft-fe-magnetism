#!/usr/bin/env python3
"""Make and execute fixed-geometry FeSe Quantum ESPRESSO SCF experiments.

Python 3.11+ standard library, QE pw.x and optionally Open MPI are required.
Pass a verified directory with Fe_std.upf and Se_std.upf and a JSON case list.
Example: python fese.py matrix.json jobs/ --pseudo-dir common/ --pw pw.x
One fresh subdirectory per attempted case holds the immutable inputs and raw logs.
"""

import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import time
from datetime import datetime, timezone

PSEUDOS = {
    "Fe_std.upf": "79848bdb660ac0fe3f93ac0967cba01fe200f5cc2cf37e7f01e6ac051f107105",
    "Se_std.upf": "1f5d0f8b99028dee90766aab811ce5d8bb2c2b2ad38ec60436d1c2888ef5109c",
}
A_REF, C_REF, Z_REF = 3.765, 5.518, 0.2343  # Å, Å, fractional, Subedi Table I
FE_COUNT = 4
PATTERNS = {"fm": (1, 1, 1, 1), "checker": (1, -1, 1, -1),
            "stripe": (1, 1, -1, -1), "nm": (0, 0, 0, 0)}
RY_TO_MEV = 13605.693122994


def sha256(path):
    """Hash exact file bytes, including final line terminators."""
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, payload):
    """Replace JSON atomically so an interruption leaves the preceding record."""
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def atoms(z, pattern):
    """Return atoms as (type, f1, f2, f3) in the doubled tetragonal cell.

    Primitive Cartesian-oriented fractions are transformed by A'=A+B, B'=-A+B.
    (0,0) and (1,0) are the two cosets of its in-plane translation subgroup.
    The Fe nearest-neighbor translations are (A+B)/2 and (-A+B)/2.
    For the Fe origin (3/4, 1/4), their integer coordinates are u=x+y-1,
    v=y-x+1/2. Stripe alternates in u. Checker alternates in u+v.
    """
    primitive = (("Fe", .75, .25, 0.), ("Fe", .25, .75, 0.),
                 ("Se", .25, .25, z), ("Se", .75, .75, -z))
    result = []
    for element in ("Fe", "Se"):
        for translation in (0., 1.):
            for name, x, y, height in primitive:
                if name != element:
                    continue
                x += translation
                label = element
                if element == "Fe" and pattern != "nm":
                    label = "FeP" if PATTERNS[pattern][len(result)] > 0 else "FeM"
                result.append((label, ((x + y) / 2.) % 1.,
                               ((y - x) / 2.) % 1., height % 1.))
    return result


def make_input(case):
    """Generate a single SCF input in Å, fractional positions and QE Rydberg units."""
    a = case.get("a", A_REF)
    c = case.get("c", C_REF)
    z = case.get("z", Z_REF)
    pattern = case["pattern"]
    magnetic = pattern != "nm"
    species = ["FeP", "FeM", "Se"] if pattern in ("checker", "stripe") else [
        "FeP" if magnetic else "Fe", "Se"]
    chemical_data = {"FeP": "55.845 Fe_std.upf", "FeM": "55.845 Fe_std.upf",
                     "Fe": "55.845 Fe_std.upf", "Se": "78.971 Se_std.upf"}
    seed = case.get("seed", 0.22)  # QE 6.7 valence-electron spin fraction
    starting_spin = ""
    if magnetic:
        starting_spin = f" starting_magnetization(1)={seed},\n"
        if "FeM" in species:
            starting_spin += f" starting_magnetization(2)={-seed},\n"
    positions = "\n".join(f"{label:3} {x:.10f} {y:.10f} {height:.10f}"
                          for label, x, y, height in atoms(z, pattern))
    kmesh = " ".join(str(k) for k in case["k"])
    cutoff = case["ecut"]
    rho_cutoff = case.get("rho", 4 * cutoff)
    electronic_tol = case.get("tol", 1.e-8)
    force_flag = ".true." if case.get("forces", False) else ".false."
    start_files = (" startingpot='file', startingwfc='file',\n"
                   if case.get("start_from") else "")
    disk_io = case.get("disk_io", "nowf")
    species_card = "\n".join(f"{name} {chemical_data[name]}" for name in species)
    return f"""! {case['id']} | periodic c-repeat of a single FeSe slab.
! Common 4-Fe supercell, a is the crystallographic 2-Fe cell parameter in Å.
! Species split initializes spin, without imposing local or total moments.
&CONTROL
 calculation='scf', prefix='fese', pseudo_dir='./pseudo',
 outdir='./scratch', disk_io='{disk_io}', tprnfor={force_flag},
/
&SYSTEM
 ibrav=0, nat=8, ntyp={len(species)}, input_dft='PBE',
 ecutwfc={cutoff}, ecutrho={rho_cutoff}, nspin={2 if magnetic else 1},
 occupations='smearing', smearing='{case.get('smearing', 'mv')}', degauss={case['sigma']},
{starting_spin}/
&ELECTRONS
 conv_thr={electronic_tol}, electron_maxstep={case.get('maxiter', 110)},
 mixing_beta={case.get('mixing', 0.32)}, mixing_mode='local-TF',
{start_files}/
ATOMIC_SPECIES
{species_card}
CELL_PARAMETERS angstrom
 {a:.10f}  {a:.10f}  0.0000000000
 {-a:.10f} {a:.10f}  0.0000000000
 0.0000000000 0.0000000000 {c:.10f}
ATOMIC_POSITIONS crystal
{positions}
K_POINTS automatic
{kmesh} 0 0 0
"""


def seed_from_saved_state(case, base, target):
    """Copy a converged compatible same-cell parent scratch checkpoint.

    This supports smearing-only sensitivity. Geometry, basis, mesh, species,
    seed label and spin formalism are held fixed. A warm restart may track an
    existing basin, so a cold replay is recorded as an independent check.
    """
    parent_id = case.get("start_from")
    if not parent_id:
        return None
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", parent_id):
        raise ValueError("Invalid parent attempt ID")
    parent = base / parent_id
    parent_record = parent / "attempt.json"
    meta = json.loads(parent_record.read_text())
    while meta["state"] in {"STARTING", "RUNNING"}:
        # Only a known explicitly named parent can hold a queued child.
        # The Work supervisor must reconcile interrupted sessions on recovery.
        time.sleep(10)
        meta = json.loads(parent_record.read_text())
    stdout = (parent / "pw.stdout").read_text()
    parent_case = meta["case"]
    comparables = ("a", "c", "z", "pattern", "k", "ecut", "rho", "seed")
    if any(parent_case.get(key) != case.get(key) for key in comparables):
        raise ValueError("Parent starting checkpoint has incompatible physical/numerical settings")
    if meta.get("returncode") != 0 or "convergence has been achieved" not in stdout or "JOB DONE" not in stdout:
        raise ValueError("Parent starting checkpoint lacks terminal SCF evidence")
    source = parent / "scratch" / "fese.save"
    if not (source / "charge-density.dat").is_file():
        raise FileNotFoundError("Parent starting checkpoint has no charge density")
    if not any(source.glob("wfc*")):
        raise FileNotFoundError("Parent starting checkpoint has no portable wavefunctions")
    shutil.copytree(source, target)
    return {"parent_id": parent_id, "parent_input_sha256": meta["input_sha256"],
            "parent_stdout_sha256": sha256(parent / "pw.stdout"),
            "copied_files_sha256": {filename.name: sha256(filename)
                                      for filename in sorted(target.iterdir()) if filename.is_file()}}


def execute(case, base, pseudo_dir, pw, ranks, launcher):
    """Start one new attempt, keeping partial logs and pre-launch provenance."""
    run_id = case["id"]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", run_id):
        raise ValueError(f"Invalid run ID {run_id!r}")
    folder = base / run_id
    if folder.exists():
        print(f"{run_id}: existing attempt preserved", flush=True)
        return
    folder.mkdir()
    (folder / "scratch").mkdir()
    (folder / "pseudo").symlink_to(pseudo_dir, target_is_directory=True)
    input_path = folder / "pw.in"
    input_path.write_text(make_input(case))
    command = [pw, "-nk", str(ranks), "-in", "pw.in"]
    if ranks > 1:
        command = [launcher, "--bind-to", "none", "-n", str(ranks), *command]
    run_env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
                   MKL_NUM_THREADS="1", LC_ALL="C")
    structural = {"a": A_REF, "c": C_REF, "z": Z_REF, "n_fe": FE_COUNT,
                  "units": {"a": "angstrom", "c": "angstrom", "z": "fractional"},
                  "path": "fixed-c-fixed-fractional-z-tetragonal-a"}
    structural.update({k: case[k] for k in ("a", "c", "z") if k in case})
    record = {"case": case, "structure": structural, "started_utc": timestamp(),
              "state": "STARTING", "command": command, "command_shell": shlex.join(command),
              "input_sha256": sha256(input_path), "pseudopotential_sha256": PSEUDOS,
              "pw_sha256": sha256(pw), "mpi_ranks": ranks,
              "thread_env": {k: run_env.get(k) for k in (
                  "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "LC_ALL",
                  "HWLOC_COMPONENTS", "LD_LIBRARY_PATH")}}
    write_json(folder / "attempt.json", record)
    started = time.monotonic()
    launched = None
    try:
        record["starting_checkpoint"] = seed_from_saved_state(case, base, folder / "scratch" / "fese.save")
        with (folder / "pw.stdout").open("wb") as stdout, (folder / "pw.stderr").open("wb") as stderr:
            launched = time.monotonic()
            record["launched_utc"] = timestamp()
            with subprocess.Popen(command, cwd=folder, env=run_env, stdin=subprocess.DEVNULL,
                                  stdout=stdout, stderr=stderr) as proc:
                record.update(state="RUNNING", process_pid=proc.pid)
                write_json(folder / "attempt.json", record)
                record["returncode"] = proc.wait()
        record["state"] = "PROCESS_EXITED"
    except (OSError, ValueError) as exc:
        record.update(state="LAUNCH_FAILED", launch_error=str(exc), returncode=None)
    finally:
        ended = time.monotonic()
        record.update(ended_utc=timestamp(), wall_seconds=round(ended - started, 3),
                      process_wall_seconds=round(ended - launched, 3) if launched is not None else None)
        write_json(folder / "attempt.json", record)
    print(f"{run_id}: {record.get('returncode')} ({record['wall_seconds']} s)", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matrix", type=Path)
    parser.add_argument("root", type=Path)
    parser.add_argument("--pseudo-dir", type=Path, required=True)
    parser.add_argument("--pw", default="pw.x")
    parser.add_argument("--launcher", default="mpirun")
    parser.add_argument("--ranks", type=int, default=1)
    parser.add_argument("--parallel", type=int, default=1)
    args = parser.parse_args()
    pseudo_dir = args.pseudo_dir.resolve(strict=True)
    for filename, digest in PSEUDOS.items():
        if sha256(pseudo_dir / filename) != digest:
            raise SystemExit(f"Unexpected bytes for {filename}")
    pw = shutil.which(args.pw)
    launcher = shutil.which(args.launcher)
    if not pw or (args.ranks > 1 and not launcher):
        raise SystemExit("Cannot locate the requested QE and MPI executables")
    base = args.root.resolve()
    base.mkdir(parents=True, exist_ok=True)
    cases = json.loads(args.matrix.read_text())
    identifiers = [case["id"] for case in cases]
    if len(set(identifiers)) != len(identifiers):
        raise SystemExit("Input matrix contains duplicate attempt IDs")
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallel) as executor:
        futures = [executor.submit(execute, case, base, pseudo_dir, str(Path(pw).resolve()),
                                   args.ranks, launcher) for case in cases]
        for future in concurrent.futures.as_completed(futures):
            future.result()


if __name__ == "__main__":
    main()
