#!/bin/bash
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
export OPENROUTER_API_KEY="$(op read 'op://Private/OpenRouter - Initial Retort Key/credential')"
echo "key len=${#OPENROUTER_API_KEY}; re-running 30 original open-weight cells (rows 0-9)"
for i in 0 1 2 3; do
  retort run --phase screening --config experiment-15/workspace-grid.yaml \
    --design experiment-15/design-openweight.csv --replicates 3 --shard $i/4 --resume \
    > experiment-15/recover-originals-shard$i.log 2>&1 &
done
wait
echo "=== RECOVER DONE ==="
grep -hE "Done:" experiment-15/recover-originals-shard*.log
sqlite3 experiment-15/retort.db "SELECT status, COUNT(*) FROM experiment_runs GROUP BY status;"
