#!/usr/bin/env python3
"""Build the editable scientific result report from immutable analysis files.

Usage: python report.py derived/results.json derived/comparisons.json report.md
Requires Python 3.11+, companion analysis utilities and a completed or partial
analysis dataset. The report uses only accepted final SCF evidence.
"""

import argparse
import json
from pathlib import Path

from analysis import SCIENCE_STATUS, primary_matrix_outcomes
from fese import RY_TO_MEV
from tables import fmt, join_table


def accepted(row):
    return row["state"] in SCIENCE_STATUS and row["final_state"] not in (
        None, "missing_final_magnetic_evidence")


def scanned(rows):
    primary = list(primary_matrix_outcomes(rows).values())
    usable = [r for r in primary if accepted(r)]
    xgrid = sorted({r["a_angstrom"] for r in primary})
    winners = []
    for x in xgrid:
        picked = sorted((r for r in usable if r["a_angstrom"] == x),
                        key=lambda r:r["total_energy_ry_cell"])
        winners.append((x,picked[0] if picked else None,len(picked),
                        sum(r["a_angstrom"] == x for r in primary)))
    minimum = min(usable,key=lambda r:r["total_energy_ry_cell"],default=None)
    return primary,winners,minimum


def report(rows, comparisons, data_url):
    primary,winners,minimum = scanned(rows)
    indexed = {r["run_id"]:r for r in rows}
    anchor_gap = comparisons["primary_scan"]["anchor"]["nm"]
    fm = indexed.get("p1-anchor-fm")
    stripe = indexed.get("p1-anchor-stripe")
    replay = comparisons["replay"]
    refinement = comparisons["adaptive_basis_refinement"]
    refinement_text = (
        f"The adaptive tighter-basis stripe–NM pair shifts the 90 Ry gap by "
        f"{refinement['shift_mev_fe']:.3f} meV/Fe."
        if refinement["shift_mev_fe"] is not None else
        "The adaptive tighter-basis stripe–NM pair has no matched comparison.")
    width = comparisons["adaptive_smearing_refinement"]
    width_text = (
        f"The second width reduction on the same dense mesh shifts the previous stripe–NM "
        f"gap by {width['shift_mev_fe']:.3f} meV/Fe."
        if width["shift_mev_fe"] is not None else
        "The second width reduction has no matched stripe–NM comparison.")
    dense = comparisons["adaptive_mesh_refinement"]
    dense_text = (
        f"The further in-plane mesh refinement shifts its previous stripe–checkerboard gap by "
        f"{dense['shift_mev_fe']:.3f} meV/Fe."
        if dense["shift_mev_fe"] is not None else
        "The further mesh refinement has no matched stripe–checkerboard comparison.")
    checked = [key for key,value in comparisons["anchor_numerical_sensitivity"].items()
               if value["complete"]]
    statuses = [
        (fmt(a),n, count, result["run_id"] if result else "—", result["final_state"] if result else "—")
        for a,result,n,count in winners]
    scan_text = join_table(("a (Å)", "Accepted observations", "Scheduled observations",
                            "Minimum sampled run", "Verified final class"), statuses)
    if minimum is None:
        minimum_text = "No accepted primary calculation supports a lattice-path minimum."
    else:
        minimum_text = (
            f"The lowest computed primary energy is from {minimum['run_id']} at "
            f"a = {minimum['a_angstrom']:.3f} Å, with final class {minimum['final_state']}. "
            "This is a sampled fixed-path minimum. It does not locate a relaxed structure "
            "or establish the location of a continuous minimum.")
    if anchor_gap["mev_fe"] is not None and anchor_gap["final_states"] == ["stripe","nm"]:
        val=anchor_gap["mev_fe"]
        agree="The sign agrees with the reported stabilization." if val < 0 else "The sign differs."
        comparison_text=(f"{anchor_gap['first']} versus {anchor_gap['second']}: "
                         f"ΔE = {val:.3f} meV/Fe. {agree} "
                         f"The signed difference from the LDA reference (−5 meV/Fe) is "
                         f"{val + 5:.3f} meV/Fe under our P1 settings.")
    else:
        comparison_text="An eligible matched stripe and explicit NM pair is unavailable."
    moments = stripe.get("fe_weighted_moments_muB") if stripe else None
    if moments:
        avg = sum(abs(m) for m in moments)/len(moments)
        moment_text = f"{stripe['run_id']} has mean |weighted Fe moment| = {avg:.4f} μB."
    else:
        moment_text = "No usable primary anchor stripe site-moment table."
    fm_text = (f"{fm['run_id']} ended as {fm['final_state']}." if fm and accepted(fm)
               else "No eligible primary FM-seeded endpoint at the anchor.")
    paper_table=join_table(
        ("Source and target", "Calculated observable and evidence", "Comparability"),
        [
            ("Subedi et al., Table I and §IV, FeSe SDW stabilization 5 meV/Fe",
             comparison_text,
             "Fixed cells share a, c and z at the anchor. QE NC-PBE and LAPW-LDA differ. Reference vertical stacking is not specified here."),
            ("Subedi et al., Table I, Fe sphere moment 0.65 μB at radius 2.1 Bohr",
             moment_text,
             "Our tapered, weighted real-space Fe moment has a different definition and method. No numerical reproduction tolerance is applied."),
            ("Subedi et al., §IV, no FM instability for FeSe",
             fm_text,
             "Qualitative comparison for the sampled initial condition. Seed collapse does not exhaust all possible polarized basins."),
            ("Yildirim, Figs. 2–4, LaFeAsO AFM patterns, moment and angle scans",
             "The planar checker and stripe definitions structure the seed comparison.",
             "Different compound, constraints, cell path and methods. No quantitative comparison."),
            ("Johannes, pp. 1–2 and Fig. 1",
             "Context for comparing magnetism in Fe tetrahedral sheets.",
             "Interpretive context only. Static spin DFT gives no pairing or transition-temperature result."),
        ])
    shifts=[]
    for opponent,g in comparisons["anchor_numerical_sensitivity"].items():
        envelope=g["additive_observed_envelope_mev_fe"]
        status=(f"Absolute-shift sum {envelope:.3f} meV/Fe. "
                f"Passes the 2 meV/Fe goal: {g['within_2_mev_fe_goal']}. "
                f"Gap exceeds the summed sensitivity: {g['sign_stable_beyond_envelope']}."
                if envelope is not None else
                "A complete cutoff, mesh and width sensitivity envelope is unavailable.")
        shifts.append(f"- Stripe versus {opponent}. {status}")
    replay_text=(f"The clean representative replay differs by {replay['mev_fe']:.6f} meV/Fe. "
                 f"The final-state and ≤0.2 meV/Fe check passes: {replay['meets_tolerance']}."
                 if replay["mev_fe"] is not None else "The clean replay has no eligible paired result.")
    summary = "、".join(f"{a:.3f} Å（{result['final_state']}）"
                      for a,result,n,count in winners if result)
    sn = "、".join(checked) if checked else "尚无完整配对"
    return f"""# FeSe fixed-geometry magnetic lattice scan

Independent GPT Work result R01. This report uses first-run evidence under the scope defined in REPRODUCTION_PLAN_R01.md. Refer to COMPLETION_ASSESSMENT.md for the producer's judgement and remaining gaps.

## Scientific question and method

A stoichiometric PbO-type FeSe cell was strained in-plane while c and the Se height remained fixed. A common periodic four-Fe cell allowed the same broad-zone quadrature and volume at each value of a for all three collinear starts. The primary series used identical scalar-relativistic PBE norm-conserving pseudopotentials, basis, mesh, occupation scheme and structural coordinates at each a. A separate NM calculation at the paper geometry provides a comparison zero.

The FM spin seed was common to all Fe sites. The checkerboard seed alternated along both nearest-neighbor directions, while stripe alternated along one direction and aligned along the other. No moment constraint was applied. The finite cell and type-label-compatible symmetries restrict the space of accessible states. A run supplies an accepted energy only on explicit QE SCF convergence with a finite final energy and supported residual. Site signs come from the last QE weighted spin-density integration, up to global spin reversal. The cell absolute moment separates an apparently zero-net AFM solution from a collapse. The taper starts at the reported radius and ends at 1.2 times that radius.

## Lattice path results

{scan_text}

{minimum_text}

The values are relative to the sampled anchor for the total-energy curve, or to the minimum among the accepted runs at the same a for within-point comparisons. The precision displayed in the tables identifies differences in the stored values. Scientific precision follows from the sensitivity checks below. The QE energy is reported in the chosen cold-smearing convention without a separately extrapolated zero-smearing value. The detailed tables, data and figure sources travel with the report.

## Numerical and replay checks

{chr(10).join(shifts)}

{replay_text}

{refinement_text} {width_text} {dense_text}

The empirical sum of observed shifts accounts for the checked changes in basis, mesh and smearing. It has no formal coverage of higher-order coupled changes or arbitrary k-mesh sequences. Endpoint rankings have their own finite-mesh and finite-basis limitations. Full relaxation, c-axis antiferromagnetic stacking, additional in-plane ordering vectors, SOC and exchange-coupling extraction are outside the present scope.

## Correspondence with the cited papers

{paper_table}

The in-plane lattice scan extends the assigned reading. Subedi et al. used QE for a PBE linear-response calculation, whereas their magnetic reference uses the separate LAPW-LDA calculation. Both the exchange-correlation and basis/core treatments differ here. Sensitivity tests probe numerical alternatives within the common PBE model and leave the cause of any difference from the paper unproved. Se-height sensitivity and magnetic preparation affect what a fixed-geometry calculation can establish.

Data and method provenance are indexed in {data_url}.

## 中文结论摘要

已通过 SCF 和最终磁态核查的采样点可比较其最低能量解。按已接受记录，各点最低态为 {summary or '暂无可用结果'}。这描述了给定结构路径与所测试起始磁态下的结果。中心点与原文的比较采用同一几何下条纹态与显式非自旋极化态的能差。完整的配对数值敏感性结果涉及 {sn}。原文磁性计算与本版本采用不同泛函和电子结构实现，差异的来源尚未逐项分离。验收状态与剩余限制见同包的执行评估。
"""


def main():
    arg = argparse.ArgumentParser(description=__doc__)
    arg.add_argument("results", type=Path)
    arg.add_argument("comparisons", type=Path)
    arg.add_argument("output", type=Path)
    arg.add_argument("--index-label", default="the delivery manifest")
    a = arg.parse_args()
    rows=json.loads(a.results.read_text())
    cmp=json.loads(a.comparisons.read_text())
    a.output.write_text(report(rows,cmp,a.index_label))


if __name__ == "__main__":
    main()
