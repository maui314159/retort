#!/bin/bash
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
export OPENROUTER_API_KEY="$(op read 'op://Private/OpenRouter - Initial Retort Key/credential')"
retort run --phase screening --config experiment-15/workspace-grid.yaml \
  --design experiment-15/design-openweight.csv --replicates 3 --resume \
  > experiment-15/retry-empties2.log 2>&1
echo "DONE: $(grep -E 'Done:' experiment-15/retry-empties2.log | tail -1)"
sqlite3 experiment-15/retort.db "SELECT status, COUNT(*) FROM experiment_runs GROUP BY status;"
