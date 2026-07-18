#!/usr/bin/env bash
# Retry the 2 cells that failed on provider infrastructure errors
# (csharp rep3: connection refused x6; typescript rep3: upstream idle
# timeout at turn ~208). --retry-failed re-runs failed DATA-POINT cells;
# completed cells are skipped via --resume.
set -uo pipefail
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
export OPENROUTER_API_KEY="$(op read 'op://Private/OpenRouter - Initial Retort Key/credential' 2>/tmp/op_err)"
if [ "${#OPENROUTER_API_KEY}" -lt 20 ]; then echo "KEY READ FAILED (len ${#OPENROUTER_API_KEY}):"; cat /tmp/op_err; exit 7; fi
echo "retry launch $(date +%H:%M:%S), omp $(omp --version)"

EXP=experiments-local/experiment-mu-glm52-ompfix
retort run --phase screening --config $EXP/workspace.yaml \
  --design $EXP/design.csv --replicates 3 --resume --retry-failed \
  > /tmp/ompfix_retry.log 2>&1
echo "=== retry done $(date +%H:%M:%S) ==="
grep -E 'Done:' /tmp/ompfix_retry.log || true
