#!/bin/bash
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
echo "failed before: $(sqlite3 experiment-17/retort.db "SELECT COUNT(*) FROM experiment_runs WHERE status='failed'")"
PYTHONPATH=../retort-firmrun/src retort rescore --only-failed --workers 1 \
  --experiment-dir experiment-17 --config experiment-17/workspace.yaml \
  > experiment-17/serial-rescore.log 2>&1
echo "=== SERIAL RESCORE DONE ==="
grep -cE "RECOVERED" experiment-17/serial-rescore.log | xargs echo "recovered:"
tail -1 experiment-17/serial-rescore.log
sqlite3 experiment-17/retort.db "SELECT status, COUNT(*) FROM experiment_runs GROUP BY status;"
