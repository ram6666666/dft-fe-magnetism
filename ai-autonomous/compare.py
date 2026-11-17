#!/usr/bin/env python3
"""Measure signed FeSe energy gaps, sensitivity checks and replay differences.

Usage: python compare.py analysis/results.json analysis/comparisons.json
Requires only Python 3.11+. Energies in the output are meV per Fe. A missing
or incompatible pair is represented by null and carries a status message.
"""

import argparse
import json
from pathlib import Path

from analysis import SCIENCE_STATUS, primary_matrix_outcomes
from fese import RY_TO_MEV, write_json


def gap(rows, first, second):
    """Calculate E(first) - E(second) for SCFs at matching numerical settings."""
    entry = {"first": first, "second": second, "mev_fe": None,
             "initial_states": None, "final_states": None, "status": "INSUFFICIENT_EVIDENCE"}
    if first not in rows or second not in rows:
        return entry
    a, b = rows[first], rows[second]
    entry.update(first=a["run_id"], second=b["run_id"],
                 initial_states=[a["initial_state"], b["initial_state"]],
                 final_states=[a["final_state"], b["final_state"]])
    if any(r["state"] not in SCIENCE_STATUS or r["final_state"] in (
            None, "missing_final_magnetic_evidence") for r in (a, b)):
        return entry
    keys = ("path", "a_angstrom", "c_angstrom", "z_se_fraction", "n_fe",
            "pw_sha256", "functional", "pseudo_sha256", "ecutrho_ry",
            "ecutwfc_ry", "k_mesh", "k_shift", "smearing", "degauss_ry")
    if any(a[k] != b[k] for k in keys):
        entry["status"] = "INCOMPATIBLE"
        return entry
    entry["mev_fe"] = (a["total_energy_ry_cell"]-b["total_energy_ry_cell"]) * RY_TO_MEV / a["n_fe"]
    entry["status"] = "COMPARABLE_SCF_ENERGIES"
    return entry


def differences(current, variants):
    """Report the signed gap shifts for checks that retain the two final basins."""
    result = []
    for name, entry in variants.items():
        row = {"name":name, "gap":entry, "shift_mev_fe":None}
        if (current["mev_fe"] is not None and entry["mev_fe"] is not None
                and current["final_states"] == entry["final_states"]):
            row["shift_mev_fe"] = entry["mev_fe"] - current["mev_fe"]
        result.append(row)
    return result


def run(rows):
    """Create the complete pair ledger for all explicitly planned route checks."""
    primary = primary_matrix_outcomes(list(rows.values()))
    scan = {}
    for lattice_point in ("compression", "anchor", "expansion"):
        left = f"p1-{lattice_point}-"
        comparisons = ("checker", "fm", "nm") if lattice_point == "anchor" else ("checker", "fm")
        scan[lattice_point] = {p: gap(primary, left+"stripe", left+p) for p in comparisons}
    sensitivity = {}
    for competitor in ("checker", "nm"):
        cur = scan["anchor"][competitor]
        b = gap(rows, "b1-anchor-stripe", "b1-anchor-"+competitor)
        k = gap(rows, "k1-anchor-stripe", "k1-anchor-"+competitor)
        s = gap(rows, "s1-anchor-stripe", "s1-anchor-"+competitor)
        variations = {"basis_90_ry":b, "mesh_6x6x5":k}
        shifts = differences(cur, variations)
        sigma = differences(k, {"smearing_reduction_at_dense_mesh":s})[0]
        shifts.append(sigma)
        available = [abs(i["shift_mev_fe"]) for i in shifts if i["shift_mev_fe"] is not None]
        envelope = sum(available) if len(available) == len(shifts) else None
        sensitivity[competitor] = {
            "baseline":cur, "checks":shifts, "complete":envelope is not None,
            "additive_observed_envelope_mev_fe":envelope,
            "within_2_mev_fe_goal":envelope <= 2. if envelope is not None else None,
            "sign_stable_beyond_envelope":abs(cur["mev_fe"]) > envelope if envelope is not None else None,
        }
    high_basis = gap(rows, "b2-anchor-stripe", "b2-anchor-nm")
    first_basis = sensitivity["nm"]["checks"][0]["gap"]
    refinement = differences(first_basis, {"basis_106_vs_90_ry":high_basis})[0]
    replay = gap(rows, "replay-anchor-stripe", "p1-anchor-stripe")
    replay["meets_tolerance"] = (abs(replay["mev_fe"]) <= 0.2
                                 and replay["final_states"] == ["stripe","stripe"]
                                 if replay["mev_fe"] is not None else None)
    return {"schema":1, "energy_unit":"meV/Fe", "sign":"first minus second",
            "primary_scan":scan, "anchor_numerical_sensitivity":sensitivity,
            "adaptive_basis_refinement":refinement, "replay":replay}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    parser.add_argument("comparisons", type=Path)
    args = parser.parse_args()
    results = {x["run_id"]:x for x in json.loads(args.results.read_text())}
    write_json(args.comparisons, run(results))


if __name__ == "__main__":
    main()
