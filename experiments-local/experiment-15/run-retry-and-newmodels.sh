#!/bin/bash
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
export OPENROUTER_API_KEY="$(op read 'op://Private/OpenRouter - Initial Retort Key/credential')"
echo "key len=${#OPENROUTER_API_KEY}"

echo "=== RETRY rep1 empties (java/deepseek, rust/qwen) ==="
retort run --phase screening --config experiment-15/workspace-grid.yaml \
  --design experiment-15/design-grid.csv --replicates 1 --resume \
  > experiment-15/retry-grid.log 2>&1
echo "  grid retry: $(grep -E 'Done:' experiment-15/retry-grid.log | tail -1)"

echo "=== RETRY rep2/3 empties (rust/minimax r2, ts/kimi r3) ==="
retort run --phase screening --config experiment-15/workspace-grid.yaml \
  --design experiment-15/design-openweight.csv --replicates 3 --resume \
  > experiment-15/retry-openweight.log 2>&1
echo "  openweight retry: $(grep -E 'Done:' experiment-15/retry-openweight.log | tail -1)"

echo "=== NEW MODELS: glm-5.1 + tencent/hy3-preview (30 runs, 4 shards) ==="
for i in 0 1 2 3; do
  retort run --phase screening --config experiment-15/workspace-grid.yaml \
    --design experiment-15/design-newmodels.csv --replicates 3 --shard $i/4 --resume \
    > experiment-15/newmodels-shard$i.log 2>&1 &
done
wait
echo "=== ALL DONE ==="
sqlite3 experiment-15/retort.db "SELECT status, COUNT(*) FROM experiment_runs GROUP BY status;"
