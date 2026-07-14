#!/usr/bin/env bash
# GLM-5.2 easy-grid swarm: 8 sharded `retort run` processes over design-glm52.csv
# (5 langs x 3 reps = 15 cells), sharing experiment-15/retort.db via --resume.
# Hash-sharding at T=8 caps any active shard at 3 cells; empty shards exit fast.
# Serial rescore afterward (run separately) clears any concurrency false-fails.
set -uo pipefail
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
export OPENROUTER_API_KEY="$(op read 'op://Private/OpenRouter - Initial Retort Key/credential' 2>/tmp/op_err)"
if [ "${#OPENROUTER_API_KEY}" -lt 20 ]; then echo "KEY READ FAILED (len ${#OPENROUTER_API_KEY}):"; cat /tmp/op_err; exit 7; fi
echo "swarm launch $(date +%H:%M:%S), key len ${#OPENROUTER_API_KEY}, 8 shards"

T=8
pids=()
for ((i=0;i<T;i++)); do
  retort run --phase screening --config experiment-15/workspace-grid.yaml \
    --design experiment-15/design-glm52.csv --replicates 3 \
    --shard "$i/$T" --resume > "/tmp/glm52_shard_${i}.log" 2>&1 &
  pids+=($!)
  echo "  shard $i/$T -> pid ${pids[-1]}"
done

echo "waiting on ${#pids[@]} shards..."
fail=0
for p in "${pids[@]}"; do wait "$p" || fail=$((fail+1)); done
echo "=== swarm done $(date +%H:%M:%S), ${fail} shard process(es) exited non-zero ==="
echo "--- per-shard 'Done:' lines ---"
grep -H 'Done:' /tmp/glm52_shard_*.log 2>/dev/null || echo "(no Done lines)"
