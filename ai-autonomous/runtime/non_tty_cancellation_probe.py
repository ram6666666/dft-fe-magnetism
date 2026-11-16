"""Bounded engineering probe; never targets an existing calculation/session."""
import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
LOG = HERE / "non_tty_cancellation_probe.jsonl"
ROLE = "child_new_session" if len(sys.argv) > 1 else "parent"


def event(name):
    with LOG.open("a") as stream:
        stream.write(json.dumps({"utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                 "role": ROLE, "pid": os.getpid(), "event": name}) + "\n")


def caught(number, _frame):
    event("signal_" + signal.Signals(number).name)
    raise SystemExit(128 + number)


for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
    signal.signal(number, caught)
event("started")
if ROLE == "child_new_session":
    time.sleep(6)
    event("timer_finished")
else:
    subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "child"], start_new_session=True)
    print("OWN_DUMMY_PROBE_READY", flush=True)
    time.sleep(20)
    event("timer_finished")
