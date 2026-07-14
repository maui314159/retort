#!/bin/bash
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
export OPENROUTER_API_KEY="$(op read 'op://Private/OpenRouter - Initial Retort Key/credential')"
export PYTHONPATH=../retort-csharp/src
echo "key len=${#OPENROUTER_API_KEY}; brazil-bench screening, 21 cells, 4 shards (staggered)"
RUN="retort run --phase screening --config experiment-16/workspace.yaml --design experiment-16/design.csv --replicates 1 --resume"
# shard 0 first to create the DB (avoids cold-start race on this checkout)
$RUN --shard 0/4 > experiment-16/brazil-shard0.log 2>&1 &
while [ ! -f experiment-16/retort.db ]; do sleep 1; done; sleep 6
for i in 1 2 3; do $RUN --shard $i/4 > experiment-16/brazil-shard$i.log 2>&1 & done
wait
echo "=== BRAZIL SCREENING DONE ==="
grep -hE "Done:" experiment-16/brazil-shard*.log
sqlite3 experiment-16/retort.db "SELECT status, COUNT(*) FROM experiment_runs GROUP BY status;"
