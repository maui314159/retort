#!/bin/bash
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
echo "failed before: $(sqlite3 experiment-17/retort.db "SELECT COUNT(*) FROM experiment_runs WHERE status='failed'")"
PYTHONPATH=../retort-firmrun/src retort rescore --only-failed --workers 1 \
  --experiment-dir experiment-17 --config experiment-17/workspace.yaml \
  > experiment-17/depfair-rescore.log 2>&1
echo "=== DEP-FAIR RESCORE DONE ==="
grep -c "RECOVERED" experiment-17/depfair-rescore.log | xargs echo "recovered:"
sqlite3 experiment-17/retort.db "SELECT status, COUNT(*) FROM experiment_runs GROUP BY status;"
