#!/usr/bin/env python3
"""Produce Markdown numerical tables and a resource receipt from assessed QE rows.

Example: python tables.py derived/results.json derived/comparisons.json derived/
Python 3.11+ standard library. Missing cases and numerical sensitivity are shown
without inventing energy values. Durations are observed wall and rank-slot time.
"""

import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path

from analysis import SCIENCE_STATUS
from fese import RY_TO_MEV, write_json


def fmt(value, decimals=3):
    if value is None:
        return "—"
    return f"{value:.{decimals}f}"


def join_table(headers, rows):
    """Return a GFM table using headings and already formatted scalar values."""
    return "\n".join(["| " + " | ".join(headers) + " |",
                      "| " + " | ".join("---" for _ in headers) + " |"] +
                     ["| " + " | ".join(str(value) for value in row) + " |" for row in rows])


def result_tables(rows, comparisons):
    valid = [x for x in rows if x["state"] in SCIENCE_STATUS]
    main = sorted([x for x in rows if x["run_id"].startswith("p1-")],
                  key=lambda x:(x["a_angstrom"],x["initial_state"]))
    candidates = [r for r in main if r in valid and r["final_state"] != "missing_final_magnetic_evidence"]
    anchor = min((r for r in candidates if r["run_id"].startswith("p1-anchor-")),
                 key=lambda x:x["total_energy_ry_cell"], default=None)
    def energy_anchor(r):
        if anchor and r in candidates:
            return fmt((r["total_energy_ry_cell"]-anchor["total_energy_ry_cell"])*RY_TO_MEV/r["n_fe"])
        return "—"

    scan = join_table(
        ("Run ID", "a (Å)", "Initial", "Final", "Energy vs same a (meV/Fe)",
         "Energy vs anchor (meV/Fe)", "Mean |Fe moment| (μB)", "Status"),
        [[r["run_id"], fmt(r["a_angstrom"]), r["initial_state"], r["final_state"] or "—",
          fmt(r["relative_energy_mev_fe"]), energy_anchor(r),
          fmt(sum(abs(m) for m in r["fe_weighted_moments_muB"]) / r["n_fe"])
          if r["fe_weighted_moments_muB"] is not None else "—",
          r["state"]] for r in main])
    numerical = []
    for opponent, group in comparisons["anchor_numerical_sensitivity"].items():
        numerical.append([opponent, "primary", fmt(group["baseline"]["mev_fe"]), "—",
                          group["baseline"]["status"]])
        for check in group["checks"]:
            numerical.append([opponent, check["name"], fmt(check["gap"]["mev_fe"]),
                              fmt(check["shift_mev_fe"]), check["gap"]["status"]])
    refinement = comparisons["adaptive_basis_refinement"]
    numerical.append(["nm", refinement["name"], fmt(refinement["gap"]["mev_fe"]),
                      fmt(refinement["shift_mev_fe"]), refinement["gap"]["status"]])
    checks = join_table(("Competitor", "Treatment", "E(stripe) − E(competitor) (meV/Fe)",
                         "Change from matched reference (meV/Fe)", "Evidence"), numerical)
    return "\n\n".join(("# Actual case tables", "## Main fixed-height scan", scan,
                        "## Anchor numerical sensitivity", checks)) + "\n"


def resources(rows):
    """Count terminal observations and sum recorded rank times, excluding pending work."""
    terminal = [r for r in rows if r["wall_seconds"] is not None]
    starts = [datetime.fromisoformat(r["started_utc"]) for r in terminal if r["started_utc"]]
    ends = [datetime.fromisoformat(r["ended_utc"]) for r in terminal if r["ended_utc"]]
    return {"rows":len(rows), "status_counts":dict(Counter(r["state"] for r in rows)),
            "first_attempt_utc":min(starts).isoformat() if starts else None,
            "last_terminal_utc":max(ends).isoformat() if ends else None,
            "elapsed_between_first_start_and_last_end_s":
                (max(ends)-min(starts)).total_seconds() if starts and ends else None,
            "sum_terminal_wall_s":sum(r["wall_seconds"] for r in terminal),
            "sum_terminal_wall_times_times_mpi_ranks_s":
                sum(r["process_wall_seconds"] * r["mpi_ranks"] for r in terminal
                    if r["mpi_ranks"] and r["process_wall_seconds"] is not None),
            "scope":"Terminal attempt records, including stopped and failed calculations.",
            "monetary_cost":None, "provider_cpu_billing_time":None}


def main():
    arg = argparse.ArgumentParser(description=__doc__)
    arg.add_argument("results", type=Path)
    arg.add_argument("comparisons", type=Path)
    arg.add_argument("folder", type=Path)
    a = arg.parse_args()
    rows = json.loads(a.results.read_text())
    data = json.loads(a.comparisons.read_text())
    a.folder.mkdir(parents=True, exist_ok=True)
    (a.folder/"CASE_TABLES.md").write_text(result_tables(rows, data))
    write_json(a.folder/"RESOURCE_RECEIPT.json", resources(rows))


if __name__ == "__main__":
    main()
