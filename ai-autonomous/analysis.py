#!/usr/bin/env python3
"""Convert preserved QE SCF attempts into typed JSON/CSV evidence.

Usage: python analysis.py jobs/ analysis/ code/primary_R01.json
Requires Python 3.11+. Pending or failed runs have null accepted energies.
The QE output is the authority for convergence and final site magnetizations.
"""

import argparse
import csv
from collections import defaultdict
import json
import math
from pathlib import Path
import re

from fese import A_REF, C_REF, FE_COUNT, PATTERNS, PSEUDOS, RY_TO_MEV, Z_REF, write_json

NUMERIC = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?"
SCIENCE_STATUS = {"RUN_COMPLETED", "NUMERICALLY_CHECKED", "COMPARED"}


def last_number(text, pattern):
    """Return the last numeric regex group, or None for no or nonfinite match."""
    values = re.findall(pattern, text, re.MULTILINE)
    if not values:
        return None
    value = float(values[-1].replace("D", "E").replace("d", "e"))
    return value if math.isfinite(value) else None


def classify(moments, absolute, n_fe):
    """Match Fe signs up to global spin reversal and evidence of global collapse.

    moments uses QE's site order, with Fe first, in Bohr magnetons. absolute is
    the integral of |rho_up-rho_down| per cell. Small site moments combined
    with significant absolute polarization leave the classification ambiguous.
    """
    if len(moments) != n_fe or absolute is None:
        return "missing_final_magnetic_evidence"
    signs = tuple(0 if abs(m) <= 0.05 else (1 if m > 0 else -1) for m in moments)
    if signs == PATTERNS["nm"] and absolute / n_fe <= 0.10:
        return "collapsed_nm"
    for name, expect in PATTERNS.items():
        if name != "nm" and signs in (expect, tuple(-s for s in expect)):
            return name
    return "other_or_weak"


def analyze_run(root, case):
    """Return exact-attempt metadata and eligible observables or explicit nulls."""
    folder = root / case["id"]
    meta_path = folder / "attempt.json"
    record = json.loads(meta_path.read_text()) if meta_path.is_file() else {}
    settings = record.get("case", case)
    structure = record.get("structure", {
        "a": settings.get("a", A_REF), "c": settings.get("c", C_REF),
        "z": settings.get("z", Z_REF), "n_fe": FE_COUNT,
        "path": "fixed-c-fixed-fractional-z-tetragonal-a",
    })
    row = {
        "run_id": case["id"], "initial_state": settings.get("pattern"),
        "final_state": None, "path": structure["path"], "a_angstrom": structure["a"],
        "c_angstrom": structure["c"], "z_se_fraction": structure["z"],
        "height_angstrom": structure["c"] * structure["z"], "n_fe": structure["n_fe"],
        "functional": "PBE", "pseudo_sha256": PSEUDOS,
        "pw_sha256": record.get("pw_sha256"), "pw_version": None,
        "ecutwfc_ry": settings.get("ecut"),
        "ecutrho_ry": settings.get("rho", 4 * settings["ecut"]) if "ecut" in settings else None,
        "k_mesh": settings.get("k"), "k_shift": [0, 0, 0], "n_k_output": None,
        "smearing": settings.get("smearing", "mv"), "degauss_ry": settings.get("sigma"),
        "mixing_beta": settings.get("mixing", 0.32), "mixing_mode": "local-TF",
        "conv_thr_ry_cell": settings.get("tol", 1e-8), "scf_accuracy_bound_ry_cell": None,
        "iteration_count": None, "state": "NOT_RUN", "exit_code": record.get("returncode"),
        "started_utc": record.get("started_utc"), "ended_utc": record.get("ended_utc"),
        "wall_seconds": record.get("wall_seconds"), "mpi_ranks": record.get("mpi_ranks"),
        "process_wall_seconds": record.get("process_wall_seconds", record.get("wall_seconds")),
        "starting_checkpoint": record.get("starting_checkpoint"),
        "input_sha256": record.get("input_sha256"), "total_energy_ry_cell": None,
        "smearing_term_ry_cell": None, "total_moment_muB_cell": None,
        "absolute_spin_muB_cell": None, "fe_weighted_moments_muB": None,
        "weighted_radii_bohr_by_species": None, "magnetic_diagnostic": None,
        "reference_run_id": None, "relative_energy_mev_fe": None,
        "ref_definition": None, "input": f"{case['id']}/pw.in" if (folder / "pw.in").exists() else None,
        "raw_stdout": f"{case['id']}/pw.stdout" if (folder / "pw.stdout").exists() else None,
        "raw_stderr": f"{case['id']}/pw.stderr" if (folder / "pw.stderr").exists() else None,
        "settings": settings,
    }
    if not record:
        return row
    text = (folder / "pw.stdout").read_text(errors="replace") if row["raw_stdout"] else ""
    version = re.findall(r"Program PWSCF v\.(\S+)", text)
    row["pw_version"] = version[-1] if version else None
    point_count = last_number(text, r"number of k points\s*=\s*(\d+)")
    row["n_k_output"] = int(point_count) if point_count is not None else None
    if record.get("state") in {"STARTING", "RUNNING"}:
        row["state"] = "IN_PROGRESS_OR_INTERRUPTED"
        return row
    if re.search(r"Calculation stopped in scf loop", text, re.IGNORECASE):
        row["state"] = "INTERRUPTED"
        return row
    if re.search(r"convergence (?:NOT achieved|has not been achieved)", text, re.IGNORECASE):
        row["state"] = "UNCONVERGED"
        return row
    if record.get("returncode") != 0 or "JOB DONE" not in text or "Error in routine" in text:
        row["state"] = "RUN_FAILED"
        return row
    markers = list(re.finditer(r"convergence has been achieved in\s+(\d+)\s+iterations", text))
    if len(markers) != 1:
        row["state"] = "UNCONVERGED_OR_AMBIGUOUS"
        return row
    energy = last_number(text, rf"^\s*!\s+total energy\s*=\s*({NUMERIC})\s+Ry")
    residual_match = re.findall(rf"estimated scf accuracy\s*<\s*({NUMERIC})\s+Ry", text)
    if not residual_match and re.search(r"estimated scf accuracy\s*<\s*\*+", text):
        # No inferred numerical bound is accepted when QE has overflowed its format.
        row["state"] = "UNCONVERGED_OR_AMBIGUOUS"
        return row
    residual = float(residual_match[-1].replace("D", "E")) if residual_match else None
    row["scf_accuracy_bound_ry_cell"] = residual
    row["iteration_count"] = int(markers[0][1])
    if energy is None or residual is None or residual > row["conv_thr_ry_cell"]:
        row["state"] = "UNCONVERGED_OR_AMBIGUOUS"
        return row
    row["total_energy_ry_cell"] = energy
    row["smearing_term_ry_cell"] = last_number(text, rf"smearing contrib\. \(-TS\)\s*=\s*({NUMERIC})")
    row["state"] = "RUN_COMPLETED"
    if row["initial_state"] == "nm":
        row.update(final_state="nm", total_moment_muB_cell=0.,
                   absolute_spin_muB_cell=0., fe_weighted_moments_muB=[0.] * row["n_fe"],
                   magnetic_diagnostic="Explicit nspin=1 models equal up/down density.")
        return row

    prior = text[:markers[0].start()]
    segments = re.split(r"\biteration #\s*\d+", prior)
    last_step = segments[-1]
    table = re.findall(rf"atom:\s+(\d+)\s+charge:\s+{NUMERIC}\s+magn:\s+({NUMERIC})", last_step)
    moments = {int(i): float(value) for i, value in table}
    fe = [moments[i] for i in range(1, row["n_fe"] + 1) if i in moments]
    absolute = last_number(text, rf"absolute magnetization\s*=\s*({NUMERIC})\s+Bohr")
    total = last_number(text, rf"total magnetization\s*=\s*({NUMERIC})\s+Bohr")
    radii = re.findall(rf"new r_m\s*:\s*{NUMERIC}\s*\(alat units\)\s*({NUMERIC})\s*\(a\.u\.\) for type\s+(\d+)", text)
    row.update(final_state=classify(fe, absolute, row["n_fe"]), total_moment_muB_cell=total,
               absolute_spin_muB_cell=absolute, fe_weighted_moments_muB=fe or None,
               weighted_radii_bohr_by_species={int(i): float(value) for value, i in radii} or None,
               magnetic_diagnostic="QE 6.7 report_mag weighted real-space site integration at last SCF iterate.")
    return row


def primary_matrix_outcomes(rows):
    """Resolve each planned P1 member to an eligible, compatible recovery if needed.

    Original attempts remain in the full evidence table. Recovery may change
    spin-seed amplitude or mixing while preserving the seed pattern and all
    physical and quadrature settings. A successful original remains primary.
    """
    original = {r["run_id"]:r for r in rows
                if r["run_id"].startswith("p1-") and not r["settings"].get("repairs")}
    compatible = ("initial_state", "path", "a_angstrom", "c_angstrom", "z_se_fraction",
                  "n_fe", "ecutwfc_ry", "ecutrho_ry", "k_mesh", "k_shift",
                  "smearing", "degauss_ry", "conv_thr_ry_cell", "functional", "pseudo_sha256")
    for repair in rows:
        parent=repair["settings"].get("repairs")
        if parent not in original or repair["state"] not in SCIENCE_STATUS:
            continue
        predecessor=original[parent]
        if (predecessor["state"] not in SCIENCE_STATUS and
                all(predecessor[k] == repair[k] for k in compatible)):
            original[parent]=repair
    return original


def energy_reference(rows):
    """Use a single comparable numerical setting and geometry for each reference."""
    groups = defaultdict(list)
    keys = ("a_angstrom", "c_angstrom", "z_se_fraction", "ecutwfc_ry", "ecutrho_ry",
            "k_mesh", "k_shift", "smearing", "degauss_ry")
    for row in rows:
        if row["state"] in SCIENCE_STATUS and row["final_state"] != "missing_final_magnetic_evidence":
            values = tuple(tuple(row[k]) if isinstance(row[k], list) else row[k] for k in keys)
            groups[values].append(row)
    for group in groups.values():
        ref = min(group, key=lambda r: (r["total_energy_ry_cell"], r["run_id"]))
        for row in group:
            row["reference_run_id"] = ref["run_id"]
            row["ref_definition"] = "Lowest accepted energy at identical geometry and basis/mesh/smearing."
            row["relative_energy_mev_fe"] = (row["total_energy_ry_cell"] - ref["total_energy_ry_cell"]) * RY_TO_MEV / row["n_fe"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jobs", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("matrices", type=Path, nargs="*")
    args = parser.parse_args()
    planned = {}
    for path in args.matrices:
        planned.update({x["id"]: x for x in json.loads(path.read_text())})
    for folder in sorted(args.jobs.glob("*/attempt.json")):
        case = json.loads(folder.read_text())["case"]
        planned.setdefault(case["id"], case)
    rows = [analyze_run(args.jobs, case) for case in planned.values()]
    energy_reference(rows)
    args.output.mkdir(parents=True, exist_ok=True)
    write_json(args.output / "results.json", rows)
    with (args.output / "results.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, sort_keys=True) if isinstance(v, (list, dict)) else v
                             for k, v in row.items()})
    print(json.dumps(dict(sorted((k, sum(row["state"] == k for row in rows))
                                 for k in {row["state"] for row in rows}))))


if __name__ == "__main__":
    main()
