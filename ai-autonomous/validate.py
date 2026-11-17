#!/usr/bin/env python3
"""Validate Fe square-net conventions and parser behavior on real QE pilot evidence.

Run after restoring the pilot checkpoint:
    python validate.py jobs/
Requires Python 3.11+, the companion source modules and the pilot job records.
"""

import argparse
from itertools import product
import math
from pathlib import Path
import tempfile

from analysis import analyze_run, classify
from fese import A_REF, C_REF, PATTERNS, Z_REF, atoms


def distances(x, y):
    """Yield distance and displacement components over neighboring cells, in Å."""
    for image in product((-1, 0, 1), repeat=3):
        delta = [y[j] - x[j] + image[j] for j in range(3)]
        dx = A_REF * (delta[0] - delta[1])
        dy = A_REF * (delta[0] + delta[1])
        dz = C_REF * delta[2]
        yield math.sqrt(dx**2 + dy**2 + dz**2), delta


def geometry():
    """Verify periodic Fe nearest-neighbor sign products and tetrahedral contacts."""
    expected = {"fm": [(1, 1), (1, 1)], "stripe": [(-1, -1), (1, 1)],
                "checker": [(-1, -1), (-1, -1)]}
    for pattern, bond_signs in expected.items():
        crystal = atoms(Z_REF, pattern)
        fe = crystal[:4]
        assert len(set(tuple(atom[1:]) for atom in crystal)) == 8
        for i, (_, *source) in enumerate(fe):
            products = [[], []]
            se_shell = []
            for j, (_, *target) in enumerate(crystal):
                for dist, delta in distances(source, target):
                    if j < 4 and math.isclose(dist, A_REF / math.sqrt(2), abs_tol=1e-8):
                        axis = 0 if abs(delta[0]) > .4 else 1
                        assert abs(delta[1-axis]) < 1e-8
                        products[axis].append(PATTERNS[pattern][i] * PATTERNS[pattern][j])
                    if j >= 4 and math.isclose(dist, math.hypot(.5*A_REF, C_REF*Z_REF), abs_tol=1e-8):
                        se_shell.append(delta[2])
            assert [tuple(x) for x in products] == bond_signs
            assert len(se_shell) == 4 and sum(z > 0 for z in se_shell) == 2


def parser_checks(jobs):
    """Prove that real interrupted output and pending/missing cases are excluded."""
    pattern = {"id":"pilot-stripe","pattern":"stripe","ecut":45}
    stopped = analyze_run(jobs, pattern)
    assert stopped["state"] == "INTERRUPTED", stopped["state"]
    assert stopped["total_energy_ry_cell"] is None
    clean = analyze_run(jobs, dict(pattern, id="pilot-stripe-openblas"))
    assert clean["state"] == "RUN_COMPLETED", clean["state"]
    assert clean["final_state"] == "stripe", clean["final_state"]
    assert clean["total_energy_ry_cell"] is not None
    with tempfile.TemporaryDirectory() as fake:
        missing = analyze_run(Path(fake), pattern)
        assert missing["state"] == "NOT_RUN" and missing["total_energy_ry_cell"] is None
    assert classify([-1, -1, 1, 1], 5, 4) == "stripe"
    assert classify([0.01, 0, 0, -0.01], 5, 4) == "other_or_weak"
    assert classify([0.01, 0, 0, -0.01], 0.1, 4) == "collapsed_nm"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jobs", type=Path)
    args = parser.parse_args()
    geometry()
    parser_checks(args.jobs)
    print("Verified 3 periodic Fe patterns and tetrahedral coordination; actual stopped and converged QE records parsed correctly.")


if __name__ == "__main__":
    main()
