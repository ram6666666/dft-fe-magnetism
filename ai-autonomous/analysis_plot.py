#!/usr/bin/env python3
"""Analyze only observed FeSe run records and draw discrete, qualified results.

Inputs: results.json (a convenience index) and runs/<id>/{config,receipt,parsed}.json,
input.in, pw.out, and, for magnetic diagnostics, proj.out. Per-run records and raw
logs take precedence over a stale results.json. The existing fese.py parsers are
reused; this script neither runs QE nor edits any input, run record, or fese.py.

Outputs below --outdir: verified_runs.json, production_points.{json,csv},
convergence_pairs.{json,csv}, energy_difference_convergence.{json,csv}, PNG/SVG
plots, and a manifest binding source/data hashes, exclusions, and the common zero.
Dependencies: Python >=3.10, the adjacent fese.py, NumPy, Matplotlib.

Examples (quote patterns so the shell does not expand them):
  python analysis_plot.py --production-ids 'B_*' --comparison-ids 'B_*' 'C_*'
  python analysis_plot.py --production-ids B_FM_100 B_CB_100 B_STRIPE_100 \
      --target-mev-fe 1 --outdir analysis/frozen_r01

Default production selection is B_*; default convergence selection is B_* plus
C_*. Prefixes do not imply numerical settings: actual recorded settings decide
comparability. All P_* and stage=PILOT* records, including the Gamma pipeline
pilot P004, are excluded from scientific production/convergence selection. Empty
or incomplete selections produce explicit empty tables and labeled placeholder
plots, never invented energies or zeros. Plots show measured points only, with no
interpolation, equation-of-state fit, or inferred optimum from three points.

Energy is QE's reported total energy in Ry. All energy differences are converted
to meV/Fe using the recorded Fe count. The E(a) figure uses ONE energy zero for
all selected compatible points. Single-setting convergence pairs hold geometry,
initial magnetic state, spin seed, model identity and other recorded settings
fixed. A cutoff pair with fixed ecutrho/ecutwfc ratio is one controlled basis axis.
Changing final magnetic states is flagged and never called same-state convergence.
Absolute-energy shifts and changes in magnetic energy differences are separate.
One refinement step is a diagnostic, not a rigorous numerical uncertainty bound.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import fnmatch
import itertools
import json
import math
from pathlib import Path
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import fese

ROOT = Path(__file__).resolve().parent
RY_TO_MEV = fese.RY_EV * 1000.0
COMPLETE = {"RUN_COMPLETED", "NUMERICALLY_CHECKED", "COMPARED"}
NAMED_STATES = {"FM", "CB", "STRIPE", "NM_COLLAPSED", "NM_ENFORCED_NSPIN1"}
KNOWN_QE67_BINARY = "bcd96679f8a8b77d1a26abe8cba9f34a17f8aef7ad2f6688c6d11fb8cf16ec6f"
COLORS = {"FM": "#c05621", "CB": "#2563a6", "STRIPE": "#2f855a", "NM": "#6b46a3"}
SETTING_FIELDS = {
    "basis_cutoff": ("ecutwfc_ry", "ecutrho_ry"),
    "k_sampling": ("kgrid", "kshift", "gamma_only"),
    "smearing_width": ("degauss_ry",),
    "band_count": ("nbnd",),
    "electronic_tolerance": ("conv_thr_ry",),
    "parallel_layout": ("parallel_layout",),
}


def _sha(path):
    return fese.sha(path)


def _json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def _read_json(path, problems, required=True):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        if required or Path(path).exists():
            problems.append(f"{Path(path).name}: {type(exc).__name__}: {exc}")
        return {}


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _same(left, right):
    if _finite(left) and _finite(right):
        return math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-12)
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(_same(left[k], right[k]) for k in left)
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right))
    return left == right


def _canonical(value):
    # The same numeric metadata can be serialized as 90 or 90.0. Normalize only
    # for grouping; original values remain in the independently readable tables.
    if _finite(value):
        return format(value, ".12g")
    if isinstance(value, dict):
        return {k: _canonical(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_canonical(v) for v in value]
    return value


def _key(value):
    return json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"))


def _input_string(text, name):
    found = re.search(r"\b" + re.escape(name) + r"\s*=\s*['\"]([^'\"]+)['\"]", text, re.I)
    return found.group(1).strip().lower() if found else None


def _command_integer(command, flags, default):
    for flag in flags:
        if flag in command:
            try:
                return int(command[command.index(flag) + 1])
            except (ValueError, IndexError):
                return None
    return default


def _rng_descriptor(config, receipt, input_text):
    for container in (config, receipt):
        for field in ("rng", "rng_provenance", "rng_seed"):
            if field in container:
                return {"recorded_field": field, "value": container[field]}
    # This is the exact binary/source combination inspected by this lane. The
    # default is source-derived, never relabeled as a runtime-emitted seed dump.
    # QEF commit a34dabb0f802ee27085d6f5cc0127e2c94cd2a93, Modules/random_numbers.f90
    # and PW/src/wfcinit.f90; the inspected Debian patch series does not alter them.
    if (receipt.get("pw_sha256") == KNOWN_QE67_BINARY and
            _input_string(input_text, "calculation") == "scf" and
            _input_string(input_text, "restart_mode") == "from_scratch"):
        return {"algorithm": "QE6.7 randy shuffled LCG", "default_initial_seed": 0,
                "evidence": "SOURCE_DERIVED_STATIC_SCF_DEFAULT",
                "per_rank_state_captured": False}
    return {"evidence": "RNG_INITIALIZATION_NOT_ESTABLISHED"}


def load_records(root: Path):
    """Read and revalidate actual records; return records plus index diagnostics.

    Raw logs are reparsed with fese.py, and input/config/log hashes are checked
    against the run receipt. Missing, live, damaged or inconsistent records remain
    visible but are ineligible for numerical comparison. No files are modified.
    """
    root = root.resolve()
    index_problems = []
    index = _read_json(root / "results.json", index_problems, required=False)
    if not isinstance(index, list):
        if index:
            index_problems.append("results.json is not a list")
        index = []
    cached = {}
    for row in index:
        if isinstance(row, dict) and isinstance(row.get("run_id"), str):
            if row["run_id"] in cached:
                index_problems.append(f"duplicate index ID: {row['run_id']}")
            cached[row["run_id"]] = row
    ids = set(cached)
    ids.update(p.parent.name for p in (root / "runs").glob("*/config.json"))
    records = []
    for run_id in sorted(ids):
        issues, warnings = [], []
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", run_id):
            index_problems.append(f"unsafe run ID ignored: {run_id!r}")
            continue
        directory = root / "runs" / run_id
        config = _read_json(directory / "config.json", issues)
        receipt = _read_json(directory / "receipt.json", issues)
        parsed = _read_json(directory / "parsed.json", issues, required=False)
        if not all(isinstance(x, dict) for x in (config, receipt, parsed)):
            records.append({"run_id": run_id, "eligible": False,
                            "issues": ["A per-run JSON record is not an object"]})
            continue
        data = {**config, **parsed, "run_id": run_id}
        data["status"] = parsed.get("status", receipt.get("status", "NOT_RUN"))
        hashes = {}
        for name in ("config.json", "receipt.json", "parsed.json", "input.in", "pw.out", "proj.out", "runtime.json"):
            path = directory / name
            if path.is_file():
                hashes[name] = _sha(path)
        text = (directory / "input.in").read_text() if (directory / "input.in").is_file() else ""
        log = (directory / "pw.out").read_text() if (directory / "pw.out").is_file() else ""
        if data["status"] not in COMPLETE:
            issues.append(f"run status is {data['status']}")
        if not parsed:
            issues.append("completed parsed.json is absent")
        for field in ("a_ang", "c_ang", "z_se", "n_fe", "ecutwfc_ry", "ecutrho_ry",
                      "degauss_ry", "conv_thr_ry", "nbnd", "starting_polarization"):
            if not _finite(config.get(field)):
                issues.append(f"missing/nonfinite metadata: {field}")
        if not _finite(config.get("n_fe")) or config.get("n_fe", 0) <= 0:
            issues.append("n_fe must be positive")
        n_fe = config.get("n_fe")
        if not _finite(n_fe) or n_fe <= 0 or int(n_fe) != n_fe:
            issues.append("n_fe must be an integer atom count")
            n_fe = 4  # Placeholder for absent diagnostics only; this record is excluded.
        n_fe = int(n_fe)
        for field in ("kgrid", "kshift"):
            value = config.get(field)
            if (not isinstance(value, list) or len(value) != 3 or
                    not all(isinstance(x, int) and not isinstance(x, bool) for x in value)):
                issues.append(f"invalid three-integer metadata: {field}")
            elif field == "kgrid" and not all(x > 0 for x in value):
                issues.append("kgrid entries must be positive")
            elif field == "kshift" and not all(x in (0, 1) for x in value):
                issues.append("automatic-grid kshift entries must be zero or one")
        expected_hashes = receipt.get("file_hashes", {})
        if not isinstance(expected_hashes, dict):
            issues.append("receipt file_hashes is not an object")
            expected_hashes = {}
        for name in ("config.json", "input.in", "pw.out"):
            expected = receipt.get("input_sha256") if name == "input.in" else expected_hashes.get(name)
            if not expected or name not in hashes or hashes[name] != expected:
                issues.append(f"unverified or mismatched receipt hash: {name}")
        process = receipt.get("pw", {})
        if not isinstance(process, dict):
            issues.append("receipt pw execution record is not an object")
            process = {}
        raw = fese.parse_pw(log, process.get("exit_code"))
        if raw.get("status") != "RUN_COMPLETED":
            issues.append(f"raw SCF gate: {raw.get('status')}")
        if not _finite(raw.get("energy_total_ry")):
            issues.append("raw completed energy is absent/nonfinite")
        elif not _same(parsed.get("energy_total_ry"), raw["energy_total_ry"]):
            issues.append("parsed energy does not match the raw final SCF energy")
        data.update({k: raw.get(k) for k in ("energy_total_ry", "scf_converged", "job_done",
                    "qe_version", "absolute_magnetization_muB_cell", "total_magnetization_muB_cell")})
        data["pw_sha256"] = receipt.get("pw_sha256")
        data["runtime_profile_sha256"] = receipt.get("runtime_profile_sha256")
        data["pseudo_sha256"] = receipt.get("pseudo_sha256")
        data["startingwfc"] = _input_string(text, "startingwfc")
        data["startingpot"] = _input_string(text, "startingpot")
        data["restart_mode"] = _input_string(text, "restart_mode")
        data["gamma_only"] = bool(re.search(r"K_POINTS\s*[({]?\s*gamma", text, re.I))
        data["rng"] = _rng_descriptor(config, receipt, text)
        if data["rng"].get("evidence") == "RNG_INITIALIZATION_NOT_ESTABLISHED":
            issues.append("RNG initialization cannot be shown compatible")
        elif data["rng"].get("evidence") == "SOURCE_DERIVED_STATIC_SCF_DEFAULT":
            warnings.append("RNG default seed is source-derived; evolving rank states were not captured")
        command = process.get("command", [])
        env = process.get("environment", {})
        if not isinstance(command, list) or not all(isinstance(x, str) for x in command):
            issues.append("pw command is not an argument list")
            command = []
        if not isinstance(env, dict):
            issues.append("pw environment is not an object")
            env = {}
        data["parallel_layout"] = {
            "ranks": _command_integer(command, ("-np", "-n"), 1),
            "pools": _command_integer(command, ("-nk", "-npool", "-npools"), 1),
            "binding": command[command.index("--bind-to")+1] if "--bind-to" in command and command.index("--bind-to")+1<len(command) else "NOT_EXPLICIT_IN_COMMAND",
            "omp_threads": env.get("OMP_NUM_THREADS"),
            "blas_threads": env.get("OPENBLAS_NUM_THREADS"),
        }
        for field in ("pw_sha256", "runtime_profile_sha256", "pseudo_sha256", "functional",
                      "relativistic", "path_id", "initial_state", "startingwfc", "startingpot"):
            if data.get(field) is None:
                issues.append(f"missing comparability identity: {field}")
        moments = [None] * n_fe
        final_state = "UNVERIFIED_FINAL_STATE"
        if raw.get("status") == "RUN_COMPLETED" and config.get("initial_state") == "NM":
            if re.search(r"\bnspin\s*=\s*1\b", text, re.I):
                final_state = "NM_ENFORCED_NSPIN1"
            else:
                warnings.append("NM config is not supported by explicit nspin=1 input")
        elif raw.get("status") == "RUN_COMPLETED":
            projection = receipt.get("projection", {})
            if not isinstance(projection, dict):
                warnings.append("receipt projection execution record is not an object")
                projection = {}
            plog = (directory / "proj.out").read_text() if (directory / "proj.out").is_file() else ""
            phash = expected_hashes.get("proj.out")
            if (projection.get("exit_code") == 0 and "JOB DONE." in plog and phash
                    and hashes.get("proj.out") == phash):
                all_moments = fese.parse_projection(plog)
                moments = all_moments[:n_fe]
                final_state = fese.final_state(config, raw, all_moments)
            else:
                warnings.append("final magnetic projection did not pass its completion/hash gate")
        data["final_state"] = final_state
        data["fe_lowdin_moments_muB"] = moments
        data["mean_abs_fe_lowdin_muB"] = (float(np.mean(np.abs(moments)))
            if moments and all(_finite(x) for x in moments) else None)
        if parsed.get("final_state") not in (None, final_state):
            warnings.append("recorded final_state differs from fresh diagnostic classification")
        if run_id in cached:
            for field in ("status", "energy_total_ry", "final_state"):
                if not _same(cached[run_id].get(field), data.get(field)):
                    warnings.append(f"results.json is stale/different for {field}; actual records used")
        data["input_path"] = f"runs/{run_id}/input.in"
        data["log_path"] = f"runs/{run_id}/pw.out"
        records.append({"run_id": run_id, "eligible": not issues, "data": data,
                        "issues": issues, "warnings": warnings, "file_hashes": hashes,
                        "final_state_verified": final_state in NAMED_STATES})
    return records, index_problems


def _select(records, patterns):
    selected, missing = [], []
    for pattern in patterns:
        hits = [r for r in records if fnmatch.fnmatchcase(r["run_id"], pattern)]
        if not hits:
            missing.append(pattern)
        selected.extend(hits)
    unique = {r["run_id"]: r for r in selected}
    accepted, excluded = [], []
    for record in unique.values():
        stage = str(record.get("data", {}).get("stage", "")).upper()
        if record["run_id"].startswith("P") or stage.startswith("PILOT"):
            excluded.append({"run_id": record["run_id"], "reasons": ["pilot excluded from scientific selection"]})
        elif not record["eligible"]:
            excluded.append({"run_id": record["run_id"], "reasons": record["issues"]})
        else:
            accepted.append(record)
    return sorted(accepted, key=lambda r: r["run_id"]), excluded, missing


def _invariants(data, include_state=True, include_a=True):
    fields = ["c_ang", "z_se", "n_fe", "path_id", "functional", "relativistic",
              "pseudo_sha256", "pw_sha256", "runtime_profile_sha256", "smearing",
              "startingpot", "startingwfc", "restart_mode", "rng", "mixing_beta"]
    if include_a:
        fields.append("a_ang")
    if include_state:
        fields += ["initial_state", "starting_polarization"]
    return {k: data.get(k) for k in fields}


def _settings(data):
    return {axis: {key: data.get(key) for key in fields} for axis, fields in SETTING_FIELDS.items()}


def _axis_order(axis, data):
    if axis == "basis_cutoff":
        return (data["ecutwfc_ry"], data["ecutrho_ry"])
    if axis == "k_sampling":
        return (math.prod(data["kgrid"]), *data["kgrid"], *data["kshift"], data["gamma_only"])
    if axis in ("smearing_width", "electronic_tolerance"):
        return (-data[SETTING_FIELDS[axis][0]],)
    if axis == "band_count":
        return (data["nbnd"],)
    return (_key(data["parallel_layout"]),)


def convergence_pairs(records):
    """Return comparable one-setting pairs and rejected-pair reasons.

    delta E means E_to/NFe - E_from/NFe in meV/Fe. A changed final state is retained
    as an observed solution shift, but same-state convergence_delta is null. A
    changed cutoff pair counts as one axis only when its density/wavefunction
    ratio remains fixed (or only one component was varied).
    """
    pairs, rejected = [], []
    for left, right in itertools.combinations(records, 2):
        a, b = left["data"], right["data"]
        inv_a, inv_b = _invariants(a), _invariants(b)
        different = [k for k in inv_a if not _same(inv_a[k], inv_b[k])]
        if different:
            rejected.append({"run_ids": [left["run_id"], right["run_id"]],
                             "reason": "invariant mismatch", "fields": different})
            continue
        sa, sb = _settings(a), _settings(b)
        axes = [axis for axis in sa if not _same(sa[axis], sb[axis])]
        if len(axes) != 1:
            rejected.append({"run_ids": [left["run_id"], right["run_id"]],
                             "reason": "not exactly one changed setting axis", "axes": axes})
            continue
        axis = axes[0]
        changed_fields = [k for k in SETTING_FIELDS[axis] if not _same(a.get(k), b.get(k))]
        if axis == "basis_cutoff" and len(changed_fields) == 2:
            if not _same(a["ecutrho_ry"] / a["ecutwfc_ry"], b["ecutrho_ry"] / b["ecutwfc_ry"]):
                rejected.append({"run_ids": [left["run_id"], right["run_id"]],
                                 "reason": "both cutoffs changed without fixed ratio"})
                continue
        if _axis_order(axis, b) < _axis_order(axis, a):
            left, right = right, left
            a, b, sa, sb = b, a, sb, sa
        final_changed = a["final_state"] != b["final_state"]
        verified = left["final_state_verified"] and right["final_state_verified"]
        valid = verified and not final_changed
        shift = (b["energy_total_ry"] / b["n_fe"] - a["energy_total_ry"] / a["n_fe"]) * RY_TO_MEV
        pairs.append({"pair_id": f"{left['run_id']}__{right['run_id']}",
            "run_from": left["run_id"], "run_to": right["run_id"],
            "axis": axis, "changed_fields": changed_fields,
            "from_setting": sa[axis], "to_setting": sb[axis],
            "initial_state": a["initial_state"], "starting_polarization": a["starting_polarization"],
            "a_ang": a["a_ang"], "c_ang": a["c_ang"], "z_se": a["z_se"],
            "final_from": a["final_state"], "final_to": b["final_state"],
            "final_state_changed": final_changed, "final_states_verified": verified,
            "same_state_convergence_valid": valid,
            "observed_solution_energy_shift_mev_fe": shift,
            "convergence_delta_mev_fe": shift if valid else None,
            "interpretation": "single-setting same-state diagnostic" if valid else
                "solution/state change or unverified state; not a same-state numerical error estimate",
            "comparison_identity": {"fixed": _invariants(a, include_state=False),
                "spin_seed": a["starting_polarization"],
                "settings_from": sa, "settings_to": sb},
            "energy_from_ry_fe": a["energy_total_ry"] / a["n_fe"],
            "energy_to_ry_fe": b["energy_total_ry"] / b["n_fe"],
            "input_from": a["input_path"], "input_to": b["input_path"],
            "log_from": a["log_path"], "log_to": b["log_path"]})
    return pairs, rejected


def difference_convergence(pairs, tolerance):
    """Measure changes in magnetic energy differences, separately from total drift.

    For two initial-state branches A/B with matched refinements, calculate
    (E_A-E_B)_to - (E_A-E_B)_from in meV/Fe. Missing or changed final states exclude
    this derived diagnostic. Passing a requested threshold is only one observed
    refinement step, not a convergence certification or bound on all errors.
    """
    groups = {}
    for pair in pairs:
        if pair["same_state_convergence_valid"]:
            groups.setdefault(_key(pair["comparison_identity"]), []).append(pair)
    rows = []
    for group in groups.values():
        for a, b in itertools.combinations(sorted(group, key=lambda p: p["initial_state"]), 2):
            if a["initial_state"] == b["initial_state"]:
                continue
            before = (a["energy_from_ry_fe"] - b["energy_from_ry_fe"]) * RY_TO_MEV
            after = (a["energy_to_ry_fe"] - b["energy_to_ry_fe"]) * RY_TO_MEV
            delta = after - before
            rows.append({"states": [a["initial_state"], b["initial_state"]],
                "axis": a["axis"], "a_ang": a["a_ang"], "c_ang": a["c_ang"], "z_se": a["z_se"],
                "pair_a": a["pair_id"], "pair_b": b["pair_id"],
                "run_ids": [a["run_from"], b["run_from"], a["run_to"], b["run_to"]],
                "difference_definition": "E_first_state - E_second_state",
                "difference_from_mev_fe": before, "difference_to_mev_fe": after,
                "change_in_difference_mev_fe": delta,
                "requested_threshold_mev_fe": tolerance,
                "single_step_below_threshold": abs(delta) <= tolerance if tolerance is not None else None,
                "interpretation": "observed change across one matched refinement; not a global uncertainty bound"})
    return rows


def production_points(records, reference_id=None):
    """Create a compatible fixed-c,z E(a) dataset with one common meV/Fe zero.

    All selected points must share the actual model and numerical settings. Only
    a and magnetic starting configuration may vary. Incompatible selections are
    rejected as a whole, rather than silently plotting a convenient subset. The
    default zero is the minimum observed E/NFe across this exact selected set.
    """
    if not records:
        return [], {"status": "NO_ELIGIBLE_SELECTED_PRODUCTION_POINTS", "energy_zero": None}
    signatures = {}
    for record in records:
        data = record["data"]
        signature = {"fixed": _invariants(data, include_state=False, include_a=False),
                     "settings": _settings(data)}
        signatures.setdefault(_key(signature), []).append(record["run_id"])
    if len(signatures) != 1:
        return [], {"status": "INCOMPARABLE_PRODUCTION_SELECTION", "energy_zero": None,
                    "incompatible_groups": list(signatures.values()),
                    "reason": "selected points mix model, fixed c/z path or numerical settings"}
    if reference_id:
        refs = [r for r in records if r["run_id"] == reference_id]
        if not refs:
            return [], {"status": "REQUESTED_REFERENCE_NOT_ELIGIBLE_OR_NOT_SELECTED", "energy_zero": None}
        reference = refs[0]
    else:
        reference = min(records, key=lambda r: (r["data"]["energy_total_ry"] / r["data"]["n_fe"], r["run_id"]))
    zero = reference["data"]["energy_total_ry"] / reference["data"]["n_fe"]
    points = []
    for record in records:
        data = record["data"]
        points.append({"run_id": record["run_id"], "initial_state": data["initial_state"],
            "final_state": data["final_state"], "final_state_verified": record["final_state_verified"],
            "a_ang": data["a_ang"], "c_ang": data["c_ang"], "z_se": data["z_se"],
            "n_fe": data["n_fe"], "path_id": data["path_id"],
            "energy_total_ry": data["energy_total_ry"],
            "energy_per_fe_ry": data["energy_total_ry"] / data["n_fe"],
            "energy_relative_common_zero_mev_fe": (data["energy_total_ry"] / data["n_fe"] - zero) * RY_TO_MEV,
            "reference_run_id": reference["run_id"], "reference_energy_ry_fe": zero,
            "fe_lowdin_moments_muB": data["fe_lowdin_moments_muB"],
            "mean_abs_fe_lowdin_muB": data["mean_abs_fe_lowdin_muB"],
            "input_path": data["input_path"], "log_path": data["log_path"]})
    return sorted(points, key=lambda p: (p["a_ang"], p["initial_state"], p["run_id"])), {
        "status": "MEASURED_DISCRETE_POINTS_ONLY", "energy_zero": {
            "run_id": reference["run_id"], "energy_ry_fe": zero,
            "definition": "one common zero for every selected lattice value and magnetic start",
            "selection": "explicit reference" if reference_id else "minimum observed within the exact selected set"}}


def _csv(path, rows, columns):
    with Path(path).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else v for k, v in row.items() if k in columns})


def _save_figure(fig, outdir, name):
    paths = [outdir / f"{name}.png", outdir / f"{name}.svg"]
    fig.savefig(paths[0], dpi=180, bbox_inches="tight")
    fig.savefig(paths[1], bbox_inches="tight")
    plt.close(fig)
    return paths


def _empty(ax, title, explanation):
    ax.set_title(title, loc="left", weight="bold")
    ax.text(.5, .5, explanation, transform=ax.transAxes, ha="center", va="center", wrap=True, color="#4b5563")
    ax.set_xticks([])
    ax.set_yticks([])


def draw_plots(points, production, pairs, differences, outdir):
    """Draw only measured points and explicit convergence tables; never fit E(a)."""
    written = []
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                        "axes.spines.right": False, "svg.fonttype": "none"})
    fig, ax = plt.subplots(figsize=(8, 4.8), constrained_layout=True)
    if not points:
        _empty(ax, "FeSe: energy along the declared lattice path", production["status"].replace("_", " "))
    else:
        for state in sorted({p["initial_state"] for p in points}):
            group = [p for p in points if p["initial_state"] == state]
            ax.scatter([p["a_ang"] for p in group], [p["energy_relative_common_zero_mev_fe"] for p in group],
                       label=f"{state} start", s=48, color=COLORS.get(state, "#374151"))
            for p in group:
                if not p["final_state_verified"] or p["final_state"] not in (state, "NM_ENFORCED_NSPIN1"):
                    ax.annotate(p["final_state"], (p["a_ang"], p["energy_relative_common_zero_mev_fe"]),
                                xytext=(4, 6), textcoords="offset points", fontsize=7)
        ax.set_title("FeSe: measured total energies", loc="left", weight="bold")
        ax.set_xlabel("Tetragonal a (Å)")
        ax.set_ylabel("Energy relative to one common zero (meV/Fe)")
        ax.legend(frameon=False)
        ax.grid(alpha=.18)
        ax.text(0, -.22, "Zero: " + production["energy_zero"]["run_id"] + "; discrete points only; no fitted minimum.",
                transform=ax.transAxes, fontsize=8)
    written += _save_figure(fig, outdir, "energy_vs_a")
    fig, ax = plt.subplots(figsize=(8, 4.8), constrained_layout=True)
    measured = [p for p in points if _finite(p["mean_abs_fe_lowdin_muB"])]
    if not measured:
        _empty(ax, "FeSe: final projected Fe moments", "No verified selected production Lowdin moment data.\nMissing diagnostics are not plotted as zero.")
    else:
        for state in sorted({p["initial_state"] for p in measured}):
            group = [p for p in measured if p["initial_state"] == state]
            ax.scatter([p["a_ang"] for p in group], [p["mean_abs_fe_lowdin_muB"] for p in group],
                       label=f"{state} start", s=48, color=COLORS.get(state, "#374151"))
        ax.set_title("FeSe: final Lowdin spin populations", loc="left", weight="bold")
        ax.set_xlabel("Tetragonal a (Å)")
        ax.set_ylabel("Mean absolute Fe Lowdin moment (μB/Fe)")
        ax.legend(frameon=False)
        ax.grid(alpha=.18)
        ax.text(0, -.22, "Partition-dependent projection; all signed site moments are retained in production_points.json.",
                transform=ax.transAxes, fontsize=8)
    written += _save_figure(fig, outdir, "magnetic_moments")
    display = []
    for row in pairs:
        display.append([row["initial_state"], row["axis"], f"{row['a_ang']:.6g}",
            f"{row['observed_solution_energy_shift_mev_fe']:.4f}",
            "same final state" if row["same_state_convergence_valid"] else "STATE/DIAGNOSTIC CHANGE"])
    if not display:
        fig, ax = plt.subplots(figsize=(9, 3.5), constrained_layout=True)
        _empty(ax, "Single-setting convergence diagnostics", "No eligible completed single-setting pairs.\nFailed, unconverged, pilot and incomparable runs are excluded.")
        written += _save_figure(fig, outdir, "convergence_table")
    else:
        # Paginate rather than shrinking a large table until it is unreadable.
        for page, first in enumerate(range(0, len(display), 16), 1):
            subset = display[first:first + 16]
            fig, ax = plt.subplots(figsize=(11, max(3.4, .37 * len(subset) + 1.7)), constrained_layout=True)
            ax.axis("off")
            ax.set_title("Single-setting energy shifts (not global error bounds)", loc="left", weight="bold", pad=18)
            table = ax.table(cellText=subset, colLabels=["Initial state", "Changed axis", "a (Å)", "E_to − E_from\n(meV/Fe)", "Interpretation"],
                             cellLoc="left", colLoc="left", loc="center", colWidths=[.13, .2, .12, .18, .37])
            table.auto_set_font_size(False)
            table.set_fontsize(8.5)
            table.scale(1, 1.7)
            for (row, _), cell in table.get_celld().items():
                cell.set_edgecolor("#d1d5db")
                cell.set_facecolor("#e5edf5" if row == 0 else "#ffffff")
            name = "convergence_table" if len(display) <= 16 else f"convergence_table_{page:02d}"
            written += _save_figure(fig, outdir, name)
    fig, ax = plt.subplots(figsize=(9, max(3.4, .4 * len(differences) + 1.8)), constrained_layout=True)
    if not differences:
        _empty(ax, "Convergence of magnetic energy differences", "No matched two-state refinements with verified, unchanged final states.\nAbsolute-energy drift alone is not an ordering-convergence test.")
    else:
        labels = [f"{' − '.join(r['states'])}; {r['axis']}; a={r['a_ang']:.5g}" for r in differences]
        ax.scatter([r["change_in_difference_mev_fe"] for r in differences], np.arange(len(differences)), color="#2563a6", s=40)
        ax.axvline(0, color="#9ca3af", linewidth=1)
        ax.set_yticks(np.arange(len(differences)), labels)
        ax.set_xlabel("Change in magnetic energy difference after one refinement (meV/Fe)")
        ax.set_title("Observed energy-difference convergence diagnostics", loc="left", weight="bold")
        ax.grid(axis="x", alpha=.18)
    written += _save_figure(fig, outdir, "energy_difference_convergence")
    return written


def build_analysis(root: Path, outdir: Path, production_ids, comparison_ids, reference_id=None, tolerance=None):
    """Create regenerable analysis artifacts and return their provenance manifest.

    Inputs are read-only. A separate output directory is required; attempting to
    write into the run tree or overwrite project input directories is rejected.
    Tolerance, if supplied, is meV/Fe and labels a single observed refinement only.
    """
    root, outdir = root.resolve(), outdir.resolve()
    protected = [root / name for name in ("runs", "pseudos", "campaigns", "source_versions")]
    if outdir == root or any(p == outdir or p in outdir.parents for p in protected):
        raise ValueError("--outdir must be separate from project source/input/run directories")
    if tolerance is not None and (not _finite(tolerance) or tolerance <= 0):
        raise ValueError("--target-mev-fe must be a finite positive value")
    outdir.mkdir(parents=True, exist_ok=True)
    records, index_problems = load_records(root)
    production_records, production_excluded, production_missing = _select(records, production_ids)
    comparison_records, comparison_excluded, comparison_missing = _select(records, comparison_ids)
    points, production = production_points(production_records, reference_id)
    pairs, rejected_pairs = convergence_pairs(comparison_records)
    differences = difference_convergence(pairs, tolerance)
    _json(outdir / "verified_runs.json", records)
    for name, data in (("production_points", points), ("convergence_pairs", pairs),
                       ("energy_difference_convergence", differences)):
        _json(outdir / f"{name}.json", data)
    _csv(outdir / "production_points.csv", points, ["run_id", "initial_state", "final_state", "final_state_verified",
        "a_ang", "c_ang", "z_se", "n_fe", "path_id", "energy_total_ry", "energy_per_fe_ry",
        "energy_relative_common_zero_mev_fe", "reference_run_id", "reference_energy_ry_fe",
        "fe_lowdin_moments_muB", "mean_abs_fe_lowdin_muB", "input_path", "log_path"])
    _csv(outdir / "convergence_pairs.csv", pairs, ["pair_id", "run_from", "run_to", "axis", "changed_fields",
        "from_setting", "to_setting", "initial_state", "starting_polarization", "a_ang", "c_ang", "z_se",
        "final_from", "final_to", "final_state_changed", "final_states_verified", "same_state_convergence_valid",
        "observed_solution_energy_shift_mev_fe", "convergence_delta_mev_fe", "interpretation", "log_from", "log_to"])
    _csv(outdir / "energy_difference_convergence.csv", differences, ["states", "axis", "a_ang", "c_ang", "z_se",
        "pair_a", "pair_b", "run_ids", "difference_definition", "difference_from_mev_fe", "difference_to_mev_fe",
        "change_in_difference_mev_fe", "requested_threshold_mev_fe", "single_step_below_threshold", "interpretation"])
    written = draw_plots(points, production, pairs, differences, outdir)
    written += [outdir / "verified_runs.json"]
    written += [outdir / f"{name}.{ext}" for name in ("production_points", "convergence_pairs", "energy_difference_convergence") for ext in ("json", "csv")]
    manifest = {"created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "analysis_source_sha256": _sha(__file__), "parser_source_sha256": _sha(Path(fese.__file__)),
        "results_index_sha256": _sha(root / "results.json") if (root / "results.json").is_file() else None,
        "record_count": len(records), "eligible_record_count": sum(r["eligible"] for r in records),
        "index_diagnostics": index_problems, "production_selection_patterns": production_ids,
        "comparison_selection_patterns": comparison_ids,
        "production_selected_ids": [r["run_id"] for r in production_records],
        "comparison_selected_ids": [r["run_id"] for r in comparison_records],
        "production_exclusions": production_excluded, "production_unmatched_patterns": production_missing,
        "comparison_exclusions": comparison_excluded, "comparison_unmatched_patterns": comparison_missing,
        "production": production, "convergence_pair_count": len(pairs),
        "energy_difference_convergence_count": len(differences), "rejected_pairs": rejected_pairs,
        "units": {"energy_input": "Ry per cell", "differences": "meV/Fe", "a_c": "Angstrom", "z": "fractional",
                  "moments": "Lowdin spin-population difference, muB"},
        "energy_conversion_eV_per_Ry": fese.RY_EV,
        "scientific_status": "ANALYSIS_OF_OBSERVED_RECORDS_ONLY_NOT_INDEPENDENT_AUDIT",
        "fitted_minimum": None, "missing_values_are_zero": False,
        "artifacts": [{"path": p.name, "bytes": p.stat().st_size, "sha256": _sha(p)} for p in sorted(written)],
        "unreferenced_existing_files": [p.name for p in sorted(outdir.iterdir())
            if p.is_file() and p not in written and p.name != "analysis_manifest.json"]}
    _json(outdir / "analysis_manifest.json", manifest)
    return manifest


def main():
    """CLI: select exact IDs or quoted ID patterns; print operational counts only."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--outdir", type=Path, default=ROOT / "analysis")
    parser.add_argument("--production-ids", nargs="+", default=["B_*"])
    parser.add_argument("--comparison-ids", nargs="+", default=["B_*", "C_*"])
    parser.add_argument("--energy-reference-run")
    parser.add_argument("--target-mev-fe", type=float)
    args = parser.parse_args()
    manifest = build_analysis(args.root, args.outdir, args.production_ids, args.comparison_ids,
                              args.energy_reference_run, args.target_mev_fe)
    print(json.dumps({"records": manifest["record_count"], "eligible": manifest["eligible_record_count"],
        "production_status": manifest["production"]["status"], "convergence_pairs": manifest["convergence_pair_count"],
        "energy_difference_checks": manifest["energy_difference_convergence_count"], "output": str(args.outdir)}))


if __name__ == "__main__":
    main()
