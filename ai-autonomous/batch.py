#!/usr/bin/env python3
"""Supervise exact FeSe run selections in one executor/PID namespace.

Every worker is a separate foreground ``python fese.py run CAMPAIGN --only ID
... --no-analyze`` process. Existing run directories are skipped, never resumed
or overwritten. A worker exit of zero is not scientific success: terminal run
receipts, parsed status and process exit codes are recorded separately.

Example, from ai-autonomous/ with the required numerical-library environment:
  python batch.py campaigns/baseline.json --only B_a100_FM B_a100_CB \
      --pw /absolute/pw.x --proj /absolute/projwfc.x --ranks 2 --max-concurrent 3

Use --check-only to inspect commands without creating or starting runs. During a
real batch, create batches/<batch-id>/CANCEL_REQUEST from another tool call for
graceful cancellation. This supervisor then creates runs/<ID>/CANCEL_REQUEST for
its active workers; fese.py must poll that marker and clean up its MPI children.
SIGINT/SIGTERM and optional --max-seconds use the same cooperative mechanism.
The supervisor remains attached until its children finish; it is not a daemon.
An executor-level forced interruption can prevent terminal receipts, so prefer
the filesystem cancellation request when possible. No scientific analysis runs
concurrently; collect results once after the batch exits.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parent
RUNNER = ROOT / "fese.py"
ID_PATTERN = r"[A-Za-z0-9][A-Za-z0-9_.-]*"


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, obj):
    """Atomically replace only supervisor-owned JSON, never run receipts."""
    path = Path(path)
    temp = path.with_name(path.name + f".{os.getpid()}.tmp")
    temp.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")
    temp.replace(path)


def read_record(path):
    try:
        value = json.loads(path.read_text())
        return (value, None) if isinstance(value, dict) else ({}, "JSON is not an object")
    except (OSError, ValueError) as exc:
        return {}, f"{type(exc).__name__}: {exc}"


def observed_outcome(run_dir, worker_code):
    """Preserve reported failures even if the fese CLI itself exits zero.

    This is a terminal lifecycle check, not an independent numerical audit. It
    does not substitute for raw-output/hash validation by analysis_plot.py.
    """
    receipt, receipt_error = read_record(run_dir / "receipt.json")
    parsed, parsed_error = read_record(run_dir / "parsed.json")
    config, config_error = read_record(run_dir / "config.json")
    pw = receipt.get("pw") if isinstance(receipt.get("pw"), dict) else {}
    projection = receipt.get("projection") if isinstance(receipt.get("projection"), dict) else {}
    diagnostic_required = config.get("project") is True and config.get("initial_state") != "NM"
    details = {"receipt_status": receipt.get("status"), "parsed_status": parsed.get("status"),
               "pw_exit_code": pw.get("exit_code"), "projection_exit_code": projection.get("exit_code"),
               "projection_required": diagnostic_required,
               "record_errors": {k: v for k, v in (("receipt", receipt_error), ("parsed", parsed_error),
                                                  ("config", config_error)) if v},
               "record_sha256": {name: sha(run_dir / name) for name in
                   ("config.json", "receipt.json", "parsed.json", "pw_execution.json", "proj_execution.json")
                   if (run_dir / name).is_file()}}
    if worker_code != 0:
        status = "WORKER_FAILED"
    elif receipt.get("status") == "RUN_FAILED" or parsed.get("status") == "RUN_FAILED":
        status = "RUN_FAILED"
    elif receipt_error or parsed_error or config_error:
        status = "INCOMPLETE_OR_INVALID_RECORDS"
    elif receipt.get("status") != "RUN_COMPLETED" or parsed.get("status") != "RUN_COMPLETED":
        status = "RUN_NOT_COMPLETED"
    elif pw.get("exit_code") != 0:
        status = "PW_PROCESS_NOT_SUCCESSFUL"
    elif diagnostic_required and projection.get("exit_code") != 0:
        status = "PROJECTION_NOT_SUCCESSFUL"
    else:
        status = "COMPLETED_RUN_RECORD"
    return {"status": status, **details}


def exact_cases(campaign, selected):
    """Resolve exact IDs only and reject missing/duplicate campaign identities."""
    rows = json.loads(campaign.read_text())
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("campaign must contain a JSON list of case objects")
    ids = [row.get("run_id") for row in rows]
    if not all(isinstance(run_id, str) and re.fullmatch(ID_PATTERN, run_id) for run_id in ids):
        raise ValueError("campaign contains an invalid run_id")
    if len(ids) != len(set(ids)):
        raise ValueError("campaign contains duplicate run_id values")
    if len(selected) != len(set(selected)):
        raise ValueError("--only contains duplicate IDs")
    if any(not re.fullmatch(ID_PATTERN, run_id) for run_id in selected):
        raise ValueError("--only accepts exact safe run IDs, not glob patterns")
    missing = [run_id for run_id in selected if run_id not in ids]
    if missing:
        raise ValueError("IDs absent from campaign: " + ", ".join(missing))
    return selected


def worker_command(args, campaign, run_id):
    return [sys.executable, str(RUNNER), "run", str(campaign), "--only", run_id,
            "--pw", args.pw, "--proj", args.proj, "--ranks", str(args.ranks), "--no-analyze"]


def supervise(args):
    campaign = args.campaign.resolve()
    if not campaign.is_relative_to(ROOT / "campaigns"):
        raise ValueError("campaign must be inside this lane's ai-autonomous/campaigns directory")
    selected = exact_cases(campaign, args.only)
    commands = [{"run_id": run_id, "command": worker_command(args, campaign, run_id),
                 "run_directory_exists": (ROOT / "runs" / run_id).exists()} for run_id in selected]
    if args.check_only:
        print(json.dumps({"mode": "CHECK_ONLY_NO_JOBS_STARTED", "campaign_sha256": sha(campaign),
                          "max_concurrent": args.max_concurrent, "workers": commands}, indent=2))
        return 0
    batch_id = args.batch_id or (dt.datetime.now(dt.timezone.utc).strftime("batch_%Y%m%dT%H%M%SZ_") + uuid.uuid4().hex[:8])
    if not re.fullmatch(ID_PATTERN, batch_id):
        raise ValueError("invalid --batch-id")
    directory = ROOT / "batches" / batch_id
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "workers").mkdir()
    claims = ROOT / "batches" / "claims"
    claims.mkdir(exist_ok=True)
    t0 = time.monotonic()
    state = {"batch_id": batch_id, "status": "RUNNING", "started_at": utc(), "supervisor_pid": os.getpid(),
             "pid_namespace": os.readlink("/proc/self/ns/pid") if Path("/proc/self/ns/pid").exists() else None,
             "supervisor_command": [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
             "supervisor_sha256": sha(__file__), "runner_sha256": sha(RUNNER),
             "campaign": str(campaign), "campaign_sha256": sha(campaign),
             "max_concurrent": args.max_concurrent, "max_seconds": args.max_seconds,
             "cancel_request_file": str(directory / "CANCEL_REQUEST"), "cancellation": None,
             "selected_ids": selected, "workers": []}
    pending = list(commands)
    active = {}
    received_signals = []
    old_handlers = {}
    for number in (signal.SIGINT, signal.SIGTERM):
        old_handlers[number] = signal.signal(number, lambda signum, _frame: received_signals.append(signum))

    def checkpoint():
        state["updated_at"] = utc()
        state["elapsed_seconds"] = time.monotonic() - t0
        state["active_ids"] = list(active)
        state["pending_ids"] = [item["run_id"] for item in pending]
        dump(directory / "supervisor.json", state)

    def cancel(reason):
        if state["cancellation"] is None:
            state["cancellation"] = {"requested_at": utc(), "reason": reason}

    def request_worker_cancel(run_id, job):
        marker = ROOT / "runs" / run_id / "CANCEL_REQUEST"
        # prepare() must create this directory; creating it here would violate
        # the worker's fresh-directory ownership contract.
        if marker.parent.is_dir() and not marker.exists():
            try:
                with marker.open("x") as stream:
                    stream.write(json.dumps({"batch_id": batch_id, **state["cancellation"]}) + "\n")
                job["record"]["cancel_marker_created_at"] = utc()
            except FileExistsError:
                pass

    def finish_worker(run_id, job, code):
        for stream in job["streams"]:
            stream.close()
        job["record"].update(worker_exit_code=code, ended_at=utc(),
            elapsed_seconds=time.monotonic() - job["start"],
            log_sha256={path.name: sha(path) for path in job["paths"]},
            **observed_outcome(ROOT / "runs" / run_id, code))
        del active[run_id]
        print(json.dumps({"run_id": run_id, "worker_exit_code": code,
                          "supervisor_status": job["record"]["status"]}), flush=True)

    checkpoint()
    print(json.dumps({"batch_id": batch_id, "supervisor_pid": os.getpid(),
                      "cancel_request_file": state["cancel_request_file"]}), flush=True)
    try:
        while pending or active:
            if received_signals:
                cancel("SUPERVISOR_SIGNAL_" + str(received_signals[-1]))
            if (directory / "CANCEL_REQUEST").exists():
                cancel("SUPERVISOR_CANCEL_REQUEST_FILE")
            if args.max_seconds is not None and time.monotonic() - t0 >= args.max_seconds:
                cancel("SUPERVISOR_DECLARED_TIME_BOUND")
            # Never mix a changing runner or campaign into a single batch receipt.
            if pending and (sha(RUNNER) != state["runner_sha256"] or sha(campaign) != state["campaign_sha256"]):
                cancel("RUNNER_OR_CAMPAIGN_CHANGED")
            if state["cancellation"]:
                for item in pending:
                    state["workers"].append({**item, "status": "NOT_STARTED_CANCELLED",
                                             "reason": state["cancellation"]["reason"]})
                pending.clear()
                for run_id, job in active.items():
                    request_worker_cancel(run_id, job)
            while pending and len(active) < args.max_concurrent and state["cancellation"] is None:
                item = pending.pop(0)
                run_id = item["run_id"]
                record = {**item, "status": "PENDING"}
                state["workers"].append(record)
                if (ROOT / "runs" / run_id).exists():
                    record.update(status="SKIPPED_EXISTING_DIRECTORY", reason="Existing attempts are immutable; use a new retry ID")
                    continue
                claim = claims / f"{run_id}.json"
                try:
                    with claim.open("x") as stream:
                        stream.write(json.dumps({"batch_id": batch_id, "run_id": run_id, "claimed_at": utc()}) + "\n")
                except FileExistsError:
                    record.update(status="SKIPPED_EXISTING_CLAIM", reason="Another batch has claimed this ID; no ownership is assumed")
                    continue
                out_path, err_path = (directory / "workers" / f"{run_id}.{suffix}" for suffix in ("stdout", "stderr"))
                out, err = out_path.open("wb"), err_path.open("wb")
                started = time.monotonic()
                record.update(started_at=utc(), stdout=str(out_path.relative_to(ROOT)), stderr=str(err_path.relative_to(ROOT)))
                try:
                    process = subprocess.Popen(item["command"], cwd=ROOT, stdout=out, stderr=err,
                                               start_new_session=False)
                except OSError as exc:
                    out.close(); err.close()
                    record.update(status="LAUNCH_FAILED", error=f"{type(exc).__name__}: {exc}", ended_at=utc())
                    continue
                record.update(status="RUNNING", pid=process.pid)
                active[run_id] = {"process": process, "record": record, "start": started,
                                  "streams": (out, err), "paths": (out_path, err_path)}
            for run_id, job in list(active.items()):
                code = job["process"].poll()
                if code is None:
                    continue
                finish_worker(run_id, job, code)
            checkpoint()
            if pending or active:
                time.sleep(0.5)
    except Exception as exc:
        # A supervisor failure must not silently leave known children running.
        # Workers own their MPI groups and have a forwarded-signal cleanup path.
        state["supervisor_error"] = f"{type(exc).__name__}: {exc}"
        cancel("SUPERVISOR_EXCEPTION")
        for item in pending:
            state["workers"].append({**item, "status": "NOT_STARTED_CANCELLED",
                                     "reason": "SUPERVISOR_EXCEPTION"})
        pending.clear()
        for run_id, job in active.items():
            try:
                request_worker_cancel(run_id, job)
            except OSError as marker_error:
                job["record"]["cancel_marker_error"] = str(marker_error)
            if job["process"].poll() is None:
                job["process"].terminate()
        # Do not detach: wait for owned workers to preserve terminal receipts.
        while active:
            for run_id, job in list(active.items()):
                code = job["process"].poll()
                if code is not None:
                    finish_worker(run_id, job, code)
            if active:
                time.sleep(0.5)
    finally:
        for number, handler in old_handlers.items():
            signal.signal(number, handler)
    state["ended_at"] = utc()
    statuses = [item["status"] for item in state["workers"]]
    state["status"] = ("SUPERVISOR_FAILED" if state.get("supervisor_error") else
                       "CANCELLED" if state["cancellation"] else
                       "COMPLETED" if all(status == "COMPLETED_RUN_RECORD" for status in statuses)
                       else "FINISHED_WITH_SKIPS_OR_FAILURES")
    checkpoint()
    print(json.dumps({"batch_id": batch_id, "status": state["status"],
                      "supervisor_receipt": str(directory / "supervisor.json")}), flush=True)
    return 2 if state.get("supervisor_error") else 130 if state["cancellation"] else 0 if state["status"] == "COMPLETED" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("--only", nargs="+", required=True, help="Exact run IDs; one worker per ID")
    parser.add_argument("--pw", default="pw.x")
    parser.add_argument("--proj", default="projwfc.x")
    parser.add_argument("--ranks", type=int, default=1)
    parser.add_argument("--max-concurrent", type=int, default=3)
    parser.add_argument("--max-seconds", type=float)
    parser.add_argument("--batch-id")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    if args.ranks < 1 or args.max_concurrent < 1:
        parser.error("--ranks and --max-concurrent must be positive")
    if args.max_seconds is not None and (not math.isfinite(args.max_seconds) or args.max_seconds <= 0):
        parser.error("--max-seconds must be finite and positive")
    try:
        return supervise(args)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"batch.py: {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
