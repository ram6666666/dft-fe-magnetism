#!/usr/bin/env python3
"""Make the FeSe scan curves from JSON evidence with explicit gaps for missing SCFs.

Example: python plot.py analysis/results.json analysis/figures/
Requires Matplotlib 3.10 and Python 3.11+. Each curve follows one initial
seed; the labels on points indicate the final state when it differs.
"""

import argparse
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analysis import SCIENCE_STATUS, primary_matrix_outcomes
from fese import RY_TO_MEV

STYLES = {"fm": ("#b44c30","s"), "checker": ("#28778f","^"), "stripe": ("#173854","o")}
LABELS = {"fm":"FM", "checker":"Checkerboard", "stripe":"Stripe"}


def plot(rows, output):
    output.mkdir(parents=True, exist_ok=True)
    primary = list(primary_matrix_outcomes(rows).values())
    accepted = [r for r in primary if r["state"] in SCIENCE_STATUS
                and r["final_state"] != "missing_final_magnetic_evidence"]
    anchor = [r for r in accepted if r["run_id"].startswith("p1-anchor-")]
    if not anchor:
        raise ValueError("No accepted primary anchor")
    reference = min(anchor, key=lambda r:r["total_energy_ry_cell"])
    fig, ax = plt.subplots(figsize=(7.3,4.7), layout="constrained")
    for initial, (color, marker) in STYLES.items():
        route = sorted((r for r in primary if r["initial_state"]==initial),key=lambda x:x["a_angstrom"])
        xs = [r["a_angstrom"] for r in route]
        ys = [(r["total_energy_ry_cell"]-reference["total_energy_ry_cell"])*RY_TO_MEV/r["n_fe"]
              if r in accepted else math.nan for r in route]
        ax.plot(xs, ys, color=color, marker=marker, linewidth=1.7, label=LABELS[initial]+" start")
        for row,y in zip(route,ys):
            state=row["final_state"]
            if math.isfinite(y) and state!=initial:
                label="NM-like" if state=="collapsed_nm" else state
                ax.annotate(label, (row["a_angstrom"], y),
                            xytext=(4,5), textcoords="offset points", color=color, fontsize=8)
    ax.set(xlabel="Tetragonal in-plane lattice parameter a (Å)",
           ylabel="Energy relative to anchor minimum (meV/Fe)",
           title="FeSe at fixed c and Se height")
    ax.set_xticks(sorted({r["a_angstrom"] for r in primary}))
    ax.legend(frameon=False, loc="best")
    ax.grid(axis="y", alpha=.2)
    ax.spines[["top","right"]].set_visible(False)
    for extension in ("svg","png"):
        fig.savefig(output/f"fese_lattice_scan.{extension}",dpi=220)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results",type=Path)
    parser.add_argument("output",type=Path)
    args = parser.parse_args()
    plot(json.loads(args.results.read_text()), args.output)


if __name__ == "__main__":
    main()
