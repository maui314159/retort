#!/usr/bin/env bash
set -uo pipefail
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
export PYTHONPATH=/Users/maui/dve/experiments/retort-integ/src   # both fixes
echo "easy re-run3 SERIAL $(date +%H:%M:%S), opencode glm-5.2 (concurrency=1)"
python -m retort.cli run --phase screening \
  --config experiment-opencode-rerun3/workspace.yaml \
  --design experiment-opencode-rerun3/design-opencode.csv --replicates 3 --resume \
  > /tmp/rerun3_serial.log 2>&1
echo "=== easy re-run3 serial done $(date +%H:%M:%S) ==="
grep -E 'Done:' /tmp/rerun3_serial.log
