#!/usr/bin/env bash
# Sonnet 4.6 x claude-code brazil arm, on the Claude Max SUBSCRIPTION.
# 2 shards (gentler on Max usage windows than 3). Guards against accidental
# API-key billing: refuses to run if ANTHROPIC_API_KEY / ANTHROPIC_BASE_URL set.
set -uo pipefail
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
if [ -n "${ANTHROPIC_API_KEY:-}" ] || [ -n "${ANTHROPIC_BASE_URL:-}" ]; then
  echo "REFUSING: ANTHROPIC_API_KEY/ANTHROPIC_BASE_URL set — this arm must bill the Max subscription, not the API."
  exit 7
fi
echo "sonnet-claudecode swarm launch $(date +%H:%M:%S), claude $(claude --version), 2 shards, subscription auth"

EXP=experiments-local/experiment-mu-sonnet-claudecode
RUN="retort run --phase screening --config $EXP/workspace.yaml \
     --design $EXP/design.csv --replicates 3 --resume"
T=2
pids=()
$RUN --shard "0/$T" > /tmp/ccsonnet_shard0.log 2>&1 &
pids+=($!); echo "  shard 0/$T -> pid ${pids[-1]}"
while [ ! -f $EXP/retort.db ]; do sleep 1; done; sleep 4
$RUN --shard "1/$T" > /tmp/ccsonnet_shard1.log 2>&1 &
pids+=($!); echo "  shard 1/$T -> pid ${pids[-1]}"

echo "waiting on ${#pids[@]} shards..."
fail=0
for p in "${pids[@]}"; do wait "$p" || fail=$((fail+1)); done
echo "=== sonnet-claudecode swarm done $(date +%H:%M:%S), ${fail} shard(s) non-zero ==="
grep -hE 'Done:' /tmp/ccsonnet_shard*.log 2>/dev/null || echo "(no Done lines)"
