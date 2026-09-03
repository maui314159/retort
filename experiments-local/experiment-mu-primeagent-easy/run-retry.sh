#!/usr/bin/env bash
set -uo pipefail
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
E=experiments-local/experiment-mu-primeagent-easy
retort run --phase screening --config $E/workspace.yaml --design $E/design.csv \
  --replicates 3 --resume --shard 0/1 > $E/breadth-retry.log 2>&1
echo "retry rc=$?"
