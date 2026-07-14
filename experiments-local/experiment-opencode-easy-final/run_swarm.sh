#!/usr/bin/env bash
set -uo pipefail
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
export PYTHONPATH=/Users/maui/dve/experiments/retort-integ/src   # ALL fixes: OPENCODE_DB + permissions + --print-logs + inferred/transitive deps + log capture
echo "easy-final swarm $(date +%H:%M:%S), 4 shards, opencode glm-5.2 (all fixes)"
RUN="python -m retort.cli run --phase screening \
     --config experiment-opencode-easy-final/workspace.yaml \
     --design experiment-opencode-easy-final/design-opencode.csv --replicates 3 --resume"
T=4
$RUN --shard "0/$T" > "/tmp/final_shard0.log" 2>&1 &
pids=($!)
while [ ! -f experiment-opencode-easy-final/retort.db ]; do sleep 1; done; sleep 4
for ((i=1;i<T;i++)); do $RUN --shard "$i/$T" > "/tmp/final_shard${i}.log" 2>&1 & pids+=($!); done
echo "waiting on ${#pids[@]} shards..."
fail=0; for p in "${pids[@]}"; do wait "$p" || fail=$((fail+1)); done
echo "=== easy-final done $(date +%H:%M:%S), ${fail} non-zero ==="
grep -hE 'Done:' /tmp/final_shard*.log 2>/dev/null
