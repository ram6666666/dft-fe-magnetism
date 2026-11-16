"""Bounded CPU-affinity launch probes; no MPI science program is executed."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE / ("observation_" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ_") + uuid.uuid4().hex[:8])
ROOT.mkdir()
CODE = ("import json,os,time; print(json.dumps({'rank':os.environ.get('OMPI_COMM_WORLD_RANK'),"
        "'local_rank':os.environ.get('OMPI_COMM_WORLD_LOCAL_RANK'),'pid':os.getpid(),"
        "'affinity':sorted(os.sched_getaffinity(0))}),flush=True); time.sleep(1)")
receipt = {"started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
           "probe_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "supervisor_pid": os.getpid(), "supervisor_affinity": sorted(os.sched_getaffinity(0)),
           "os_cpu_count": os.cpu_count(), "runs": [],
           "scope": "Python launch/affinity only, no QE or numerical benchmark"}


def start(label, extra):
    directory = ROOT / label
    directory.mkdir()
    temp = directory / "mpi_tmp"
    temp.mkdir()
    env = os.environ.copy()
    overrides = {name: str(temp) for name in ("TMPDIR", "PRTE_MCA_prte_tmpdir_base",
                 "OMPI_MCA_btl_sm_backing_directory", "OMPI_MCA_osc_sm_backing_directory",
                 "OMPI_MCA_osc_rdma_backing_directory")}
    env.update(overrides)
    command = ["mpirun", "--report-bindings", *extra, "-np", "2", sys.executable, "-c", CODE]
    record = {"label": label, "command": command, "environment_overrides": overrides,
              "started_at": dt.datetime.now(dt.timezone.utc).isoformat()}
    process = subprocess.Popen(command, cwd=directory, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, start_new_session=True)
    record["launcher_pid"] = process.pid
    return process, record, time.monotonic(), directory


def finish(job):
    process, record, t0, directory = job
    try:
        out, err = process.communicate(timeout=20)
        record["exit_code"] = process.returncode
    except subprocess.TimeoutExpired:
        # This group belongs solely to this bounded probe.
        os.killpg(process.pid, signal.SIGTERM)
        try:
            out, err = process.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            out, err = process.communicate()
        record["exit_code"] = process.returncode
        record["timeout"] = True
    record["elapsed_seconds"] = time.monotonic() - t0
    record["ended_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    (directory / "stdout.txt").write_text(out)
    (directory / "stderr.txt").write_text(err)
    record["ranks"] = []
    for line in out.splitlines():
        try:
            item = json.loads(line)
            if isinstance(item, dict) and "affinity" in item:
                record["ranks"].append(item)
        except ValueError:
            pass
    record["file_sha256"] = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
                             for name in ("stdout.txt", "stderr.txt")}
    record["report_bindings"] = err
    receipt["runs"].append(record)


# Two harmless default launchers overlap for one second, testing whether their
# independently selected CPU masks overlap despite distinct launcher PIDs.
jobs = [start("default_A", []), start("default_B", [])]
for job in jobs:
    finish(job)
finish(start("explicit_none", ["--bind-to", "none"]))
receipt["ended_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
(ROOT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"observation": str(ROOT), "receipt": receipt}, indent=2))
