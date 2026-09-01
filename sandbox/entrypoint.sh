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
T0=$(python3 -c 'import time; print(time.monotonic())')
set +e
python3 - <<'EOF' > "$WS/_agent_stdout.log" 2> "$WS/_agent_stderr.log"
import json, os, subprocess, sys
cmd = json.loads(os.environ["RETORT_AGENT_CMD"])
proc = subprocess.run(cmd, cwd="/workspace")
sys.exit(proc.returncode)
EOF
AGENT_EXIT=$?
set -e
T1=$(python3 -c 'import time; print(time.monotonic())')
AGENT_SECONDS=$(python3 -c "print(f'{$T1 - $T0:.1f}')")

# ---- scoring ---------------------------------------------------------------
# v1 mechanical gate: pytest under coverage, python only. Deliberately NOT
# full scorer parity (code_quality / maintainability / idiomatic still run on
# the host) — this proves the tests run in the environment the build ran in,
# which is what cross-lane build_time comparability requires. Timed
# separately; never added to agent_seconds.
if [ "${RETORT_SCORE_IN_CONTAINER:-0}" = "1" ] \
   && [ "${RETORT_LANGUAGE:-}" = "python" ]; then
  python3 /score_gate.py > "$WS/_score_stdout.log" 2>&1 || true
fi

# finish() uploads via the EXIT trap.
