#!/bin/bash
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
export OPENROUTER_API_KEY="$(op read 'op://Private/OpenRouter - Initial Retort Key/credential')"
export PYTHONPATH=../retort-firmrun/src
echo "key len=${#OPENROUTER_API_KEY}; Sonnet level-set: 9 brazil-bench cells, 3 shards"
RUN="retort run --phase screening --config experiment-18/workspace.yaml --design experiment-18/design.csv --replicates 3 --resume"
$RUN --shard 0/3 > experiment-18/sonnet-shard0.log 2>&1 &
while [ ! -f experiment-18/retort.db ]; do sleep 1; done; sleep 6
for i in 1 2; do $RUN --shard $i/3 > experiment-18/sonnet-shard$i.log 2>&1 & done
wait
echo "=== SONNET DONE ==="
grep -hE "Done:" experiment-18/sonnet-shard*.log
sqlite3 experiment-18/retort.db "SELECT status, COUNT(*) FROM experiment_runs GROUP BY status;"
