#!/usr/bin/env bash
set -uo pipefail
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
E=experiments-local/experiment-mu-primeagent-easy
RUN="retort run --phase screening --config $E/workspace.yaml --design $E/design.csv --replicates 3 --resume"
pids=()
$RUN --shard 0/6 > $E/breadth-shard0.log 2>&1 & pids+=($!)
sleep 20
for i in 1 2 3 4 5; do $RUN --shard $i/6 > $E/breadth-shard$i.log 2>&1 & pids+=($!); done
rc=0; for p in "${pids[@]}"; do wait "$p" || rc=$?; done
echo "all shards done rc=$rc"
