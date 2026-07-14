#!/bin/bash
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
export OPENROUTER_API_KEY="$(op read 'op://Private/OpenRouter - Initial Retort Key/credential')"
export PYTHONPATH=../retort-firmrun/src
echo "key len=${#OPENROUTER_API_KEY}; firm pass: 45 brazil-bench cells, 4 shards (staggered)"
RUN="retort run --phase screening --config experiment-17/workspace.yaml --design experiment-17/design.csv --replicates 3 --resume"
$RUN --shard 0/4 > experiment-17/firm-shard0.log 2>&1 &
while [ ! -f experiment-17/retort.db ]; do sleep 1; done; sleep 6
for i in 1 2 3; do $RUN --shard $i/4 > experiment-17/firm-shard$i.log 2>&1 & done
wait
echo "=== FIRM PASS DONE ==="
grep -hE "Done:" experiment-17/firm-shard*.log
sqlite3 experiment-17/retort.db "SELECT status, COUNT(*) FROM experiment_runs GROUP BY status;"
