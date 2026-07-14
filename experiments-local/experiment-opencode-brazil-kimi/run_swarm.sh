#!/usr/bin/env bash
set -uo pipefail
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
# ../retort-brazil = integ opencode harness + inferred deps + firmrun C#/ts-node scorers.
export PYTHONPATH=/Users/maui/dve/experiments/retort-brazil/src
echo "brazil-kimi opencode swarm $(date +%H:%M:%S), 3 shards, opencode kimi-k2.7-code (hard task)"
RUN="python -m retort.cli run --phase screening \
     --config experiment-opencode-brazil-kimi/workspace.yaml \
     --design experiment-opencode-brazil-kimi/design-opencode.csv --replicates 3 --resume"
T=3
$RUN --shard "0/$T" > "/tmp/kimi_shard0.log" 2>&1 &
pids=($!)
while [ ! -f experiment-opencode-brazil-kimi/retort.db ]; do sleep 1; done; sleep 4
for ((i=1;i<T;i++)); do $RUN --shard "$i/$T" > "/tmp/kimi_shard${i}.log" 2>&1 & pids+=($!); done
echo "waiting on ${#pids[@]} shards..."
fail=0; for p in "${pids[@]}"; do wait "$p" || fail=$((fail+1)); done
echo "=== brazil-kimi opencode done $(date +%H:%M:%S), ${fail} non-zero shard exits ==="
grep -hE 'Done:' /tmp/kimi_shard*.log 2>/dev/null
