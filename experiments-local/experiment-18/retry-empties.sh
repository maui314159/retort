#!/bin/bash
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
export OPENROUTER_API_KEY="$(op read 'op://Private/OpenRouter - Initial Retort Key/credential')"
export PYTHONPATH=../retort-firmrun/src
echo "retrying empty Sonnet cells (3 shards)"
RUN="retort run --phase screening --config experiment-18/workspace.yaml --design experiment-18/design.csv --replicates 3 --resume"
for i in 0 1 2; do $RUN --shard $i/3 > experiment-18/retry-shard$i.log 2>&1 & done
wait
echo "=== SONNET RETRY DONE ==="
grep -hE "Done:" experiment-18/retry-shard*.log
sqlite3 experiment-18/retort.db "SELECT status, COUNT(*) FROM experiment_runs GROUP BY status;"
