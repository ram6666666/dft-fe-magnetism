# Batch supervisor producer self-check

`ai-autonomous/batch.py` is continuation tooling within the GPT lane, not an independent audit or a daemon. This subtask did not edit `fese.py`, campaigns or run records, and did not launch any calculation. `BATCH_SELF_CHECK.json` binds the tested source hash, exact check-only command and assertions.

## Interface

From `ai-autonomous/`, with the intended runtime library environment already set:

```bash
python batch.py campaigns/baseline.json --only EXACT_ID_1 EXACT_ID_2 \
  --pw /absolute/path/pw.x --proj /absolute/path/projwfc.x \
  --ranks 2 --max-concurrent 3
```

Add `--check-only` to print commands without creating or launching runs. `--only` is required and accepts exact IDs, not patterns. Each child receives exactly one ID and `--no-analyze`. The batch uses one executor/PID namespace; the worker retains responsibility for its separate MPI process group and per-stage shared-memory/session isolation. Existing run directories or prior atomic batch claims are skipped with explicit reasons. Nothing resumes or overwrites an old attempt.

The supervisor prints its batch ID and cancellation-file path immediately and writes `batches/<batch-id>/supervisor.json`, plus separate worker stdout/stderr. Its receipt records exact commands, source/campaign hashes, namespace identifier, PIDs, lifecycle timings, worker exit codes, run statuses, process exit codes and terminal record/log hashes. A zero worker exit cannot override a failed or incomplete run receipt. Required projection failure is also reported. These lifecycle checks do not replace raw-output validation or numerical interpretation by the analysis script.

## Graceful stopping and continuation

Create the exact printed `batches/<batch-id>/CANCEL_REQUEST` file from a separate tool call. The supervisor stops launching queued cases, marks them `NOT_STARTED_CANCELLED`, and creates `runs/<active-id>/CANCEL_REQUEST` only for its own active workers. It waits for workers to clean up their MPI groups and preserve terminal records. Caught SIGINT/SIGTERM and an optional `--max-seconds` declared batch budget use the same cooperative path. The workers must support marker polling and signal forwarding, which the parent's current `fese.py` does. A change to the runner or campaign during the batch also triggers cancellation, preserving a single source/configuration identity.

An executor-level Ctrl-C can tear down the process namespace before these cooperative handlers run; use the filesystem request when possible. An externally interrupted supervisor can leave a stale `RUNNING` receipt. A saved PID does not identify an accessible process in a fresh executor namespace. Do not infer that such a job is still running or reuse its directory. Preserve the incomplete attempt and select a new retry ID for continuation. Atomic batch claims remain as ownership evidence; they are not proof of live work.

## Verification boundary

Actual command construction was checked for the existing central baseline triplet: each command had one exact `--only` selection and `--no-analyze`, and all existing directories were recognized. Read-only classification of an actual failed pilot receipt with a hypothetical CLI exit of zero remained `RUN_FAILED`; an actual completed pipeline receipt classified as completed. No receipt or scientific datum was fabricated or changed.

No positive worker launch, concurrency or cancellation run was started by this subtask. Those behaviors remain to be observed in the parent's next authorized batch. The installed-MPI investigation and bounded cancellation dummy probes are separately documented in `MPI_NAMESPACE_ISOLATION.md`; they do not constitute a scientific production test.
