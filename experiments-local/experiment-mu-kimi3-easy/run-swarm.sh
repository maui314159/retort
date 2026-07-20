#!/usr/bin/env bash
# kimi-k3 easy grid, opencode harness. 3 shards (opencode doesn't swarm well
# past 3-4). opencode auth comes from ~/.local/share/opencode/auth.json
# (1P "OpenRouter - Retort - OpenCode" key); model registered in opencode.jsonc.
set -uo pipefail
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
echo "kimi3-easy swarm launch $(date +%H:%M:%S), opencode $(opencode --version), 3 shards"

EXP=experiments-local/experiment-mu-kimi3-easy
RUN="retort run --phase screening --config $EXP/workspace.yaml \
     --design $EXP/design.csv --replicates 3 --resume"
T=3
pids=()
$RUN --shard "0/$T" > /tmp/kimi3_easy_shard0.log 2>&1 &
pids+=($!); echo "  shard 0/$T -> pid ${pids[-1]}"
while [ ! -f $EXP/retort.db ]; do sleep 1; done; sleep 4
for ((i=1;i<T;i++)); do
  $RUN --shard "$i/$T" > "/tmp/kimi3_easy_shard${i}.log" 2>&1 &
  pids+=($!); echo "  shard $i/$T -> pid ${pids[-1]}"
done

echo "waiting on ${#pids[@]} shards..."
fail=0
for p in "${pids[@]}"; do wait "$p" || fail=$((fail+1)); done
echo "=== kimi3-easy swarm done $(date +%H:%M:%S), ${fail} shard(s) non-zero ==="
grep -hE 'Done:' /tmp/kimi3_easy_shard*.log 2>/dev/null || echo "(no Done lines)"
