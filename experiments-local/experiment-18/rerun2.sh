#!/bin/bash
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
export OPENROUTER_API_KEY="$(op read 'op://Private/OpenRouter - Initial Retort Key/credential')"
echo "key len=${#OPENROUTER_API_KEY} (must be 73)"
export PYTHONPATH=../retort-firmrun/src
RUN="retort run --phase screening --config experiment-18/workspace.yaml --design experiment-18/design.csv --replicates 3 --resume"
for i in 0 1 2; do $RUN --shard $i/3 > experiment-18/rerun2-shard$i.log 2>&1 & done
wait
echo "=== SONNET RE-RUN DONE ==="
grep -hE "Done:" experiment-18/rerun2-shard*.log
sqlite3 experiment-18/retort.db "SELECT status, COUNT(*) FROM experiment_runs GROUP BY status;"
