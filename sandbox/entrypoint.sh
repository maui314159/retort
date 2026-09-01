#!/usr/bin/env bash
# retort sandbox container entrypoint — one experiment cell, then exit.
#
# Contract with sandbox_runner.py (env, all required unless noted):
#   RETORT_S3_IN        s3://... input workspace tarball
#   RETORT_S3_OUT       s3://... where to upload the artifacts tarball
#   RETORT_AGENT_CMD    JSON array: the headless agent command
#   RETORT_ENV_ID       cell id (logging only)
#   RETORT_LANGUAGE     language factor (scoring stage)
#   RETORT_MODEL        served model id (logging only)
#   RETORT_IMAGE_DIGEST pinned image digest, recorded into _sandbox_meta.json
#   RETORT_SCORE_IN_CONTAINER  "1" to run scorers here (v1: stub, records
#                              scored=false; gated on the §0c scorer-parity smoke)
#   OPENROUTER_API_KEY  injected by the job definition from Secrets Manager;
#                       written to opencode's auth.json below, never logged.
#
# Invariants:
#   * agent_seconds is measured HERE, around the agent invocation only —
#     S3 transfers and setup are excluded (duration is a first-class response).
#   * The artifacts tarball is uploaded EVEN when the agent fails (trap), so a
#     failed run stays diagnosable.
set -euo pipefail

WS=/workspace
mkdir -p "$WS"
cd "$WS"

META="$WS/_sandbox_meta.json"
AGENT_EXIT=-1
AGENT_SECONDS=0

finish() {
  # Always write meta + upload artifacts, whatever happened above.
  python3 - "$META" "$AGENT_EXIT" "$AGENT_SECONDS" <<'EOF' || true
import json, os, sys
meta = {
    "agent_exit": int(sys.argv[2]),
    "agent_seconds": float(sys.argv[3]),
    "image_digest": os.environ.get("RETORT_IMAGE_DIGEST", "unpinned"),
    "env_id": os.environ.get("RETORT_ENV_ID", ""),
    "language": os.environ.get("RETORT_LANGUAGE", ""),
    "model": os.environ.get("RETORT_MODEL", ""),
    "scored": False,
}
try:
    meta.update(json.load(open("/tmp/score.json")))
except Exception:
    pass
try:
    meta["kill_reason"] = open("/tmp/kill_reason").read().strip()
except Exception:
    pass
open(sys.argv[1], "w").write(json.dumps(meta))
EOF
  tar -C "$WS" -czf /tmp/out.tar.gz . || true
  aws s3 cp /tmp/out.tar.gz "$RETORT_S3_OUT" || true
}
trap finish EXIT

# ---- pull the workspace ----------------------------------------------------
aws s3 cp "$RETORT_S3_IN" /tmp/in.tar.gz
tar -C "$WS" -xzf /tmp/in.tar.gz

# ---- opencode auth + isolation --------------------------------------------
# Key material comes from the job definition's Secrets Manager wiring; it is
# written to opencode's auth.json (its only auth path under --pure) and never
# echoed. OPENCODE_CONFIG makes the per-workspace config authoritative (no
# global config exists in this image, but be explicit anyway).
if [ -n "${OPENROUTER_API_KEY:-}" ]; then
  mkdir -p "$HOME/.local/share/opencode"
  python3 - <<'EOF'
import json, os
path = os.path.expanduser("~/.local/share/opencode/auth.json")
open(path, "w").write(json.dumps(
    {"openrouter": {"type": "api", "key": os.environ["OPENROUTER_API_KEY"]}}
))
os.chmod(path, 0o600)
EOF
fi
export OPENCODE_CONFIG="$WS/opencode.json"
export OPENCODE_DB=/tmp/opencode.db

# ---- run the agent, timed around the invocation only -----------------------
# The driver enforces the SAME two guards the local lane's progress guard
# does, so a cell dies the same way in both lanes:
#   * hard wall  = RETORT_AGENT_TIMEOUT_SECONDS  -> kill_reason=timeout
#   * stall      = RETORT_STALL_SECONDS with no new stdout bytes AND no
#                  workspace file writes           -> kill_reason=stall (0=off)
# Without the stall guard a hung agent burns the whole Batch wall silently —
# observed six times in one evening on long z-ai streams (2026-08-31). The
# kill must happen HERE (not via Batch's attempt timeout) so the artifacts
# tarball still uploads and the run stays diagnosable.
T0=$(python3 -c 'import time; print(time.monotonic())')
set +e
python3 - <<'EOF'
import json, os, signal, subprocess, sys, time

cmd = json.loads(os.environ["RETORT_AGENT_CMD"])
ws = "/workspace"
stall_secs = int(os.environ.get("RETORT_STALL_SECONDS", "0") or 0)
wall_secs = int(os.environ.get("RETORT_AGENT_TIMEOUT_SECONDS", "0") or 0)

out = open(os.path.join(ws, "_agent_stdout.log"), "wb")
err = open(os.path.join(ws, "_agent_stderr.log"), "wb")
proc = subprocess.Popen(cmd, cwd=ws, stdout=out, stderr=err,
                        start_new_session=True)

def workspace_mtime() -> float:
    latest = 0.0
    for root, _dirs, files in os.walk(ws):
        for name in files:
            if name.startswith("_agent_"):
                continue  # our own log files are not agent progress
            try:
                latest = max(latest, os.stat(os.path.join(root, name)).st_mtime)
            except OSError:
                pass
    return latest

start = time.monotonic()
last_progress = start
last_stdout = 0
kill_reason = ""
while True:
    rc = proc.poll()
    if rc is not None:
        break
    now = time.monotonic()
    size = os.path.getsize(os.path.join(ws, "_agent_stdout.log"))
    if size != last_stdout or workspace_mtime() > time.time() - 15:
        last_stdout = size
        last_progress = now
    if wall_secs and now - start > wall_secs:
        kill_reason = "timeout"
    elif stall_secs and now - last_progress > stall_secs:
        kill_reason = "stall"
    if kill_reason:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            proc.kill()
        proc.wait(timeout=30)
        break
    time.sleep(10)

if kill_reason:
    with open("/tmp/kill_reason", "w") as fh:
        fh.write(kill_reason)
    sys.exit(124)
sys.exit(proc.returncode)
EOF
AGENT_EXIT=$?
set -e
T1=$(python3 -c 'import time; print(time.monotonic())')
AGENT_SECONDS=$(python3 -c "print(f'{$T1 - $T0:.1f}')")

# ---- scoring ---------------------------------------------------------------
# Full scorer parity (v3): the image carries retort itself, and score_full.py
# runs the REAL ScoreCollector over the workspace for the metrics named in
# RETORT_RESPONSES, writing _container_scores.json. The v1 pytest gate keeps
# running too (its keys feed _sandbox_meta.json for backward compat). Timed
# separately; never added to agent_seconds.
if [ "${RETORT_SCORE_IN_CONTAINER:-0}" = "1" ]; then
  # score_gate is the python-only pytest fast path; score_full is the real
  # scorer suite and runs for EVERY language (the python-only gate here made
  # go/ts containers silently skip scoring — caught by the go/ts parity
  # checks reading all-zeros, 2026-09-01).
  if [ "${RETORT_LANGUAGE:-}" = "python" ]; then
    python3 /score_gate.py > "$WS/_score_stdout.log" 2>&1 || true
  fi
  if [ -n "${RETORT_RESPONSES:-}" ]; then
    python3 /score_full.py >> "$WS/_score_stdout.log" 2>&1 || true
  fi
fi

# finish() uploads via the EXIT trap.
