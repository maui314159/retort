#!/usr/bin/env bash
set -uo pipefail
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
export PYTHONPATH=/Users/maui/dve/experiments/retort-integ/src   # BOTH fixes: OPENCODE_DB + inferred-deps
echo "easy re-run swarm $(date +%H:%M:%S), 4 shards, opencode glm-5.2 (both fixes)"
RUN="python -m retort.cli run --phase screening \
     --config experiment-opencode-rerun/workspace.yaml \
     --design experiment-opencode-rerun/design-opencode.csv --replicates 3 --resume"
T=4
$RUN --shard "0/$T" > "/tmp/rerun_shard0.log" 2>&1 &
pids=($!)
while [ ! -f experiment-opencode-rerun/retort.db ]; do sleep 1; done; sleep 4
for ((i=1;i<T;i++)); do $RUN --shard "$i/$T" > "/tmp/rerun_shard${i}.log" 2>&1 & pids+=($!); done
echo "waiting on ${#pids[@]} shards..."
fail=0; for p in "${pids[@]}"; do wait "$p" || fail=$((fail+1)); done
echo "=== easy re-run done $(date +%H:%M:%S), ${fail} non-zero shard procs ==="
grep -hE 'Done:' /tmp/rerun_shard*.log 2>/dev/null
