#!/usr/bin/env bash
# GLM-5.2 on brazil-bench (the hard task) — 3 langs x 3 reps = 9 cells, 6-shard
# swarm into experiment-17/retort.db via --resume. Staggered start (shard 0 first,
# then the rest after a beat) to avoid the SQLite cold-start race (#23). Lands
# against the exp-17 dep-fair table (opus 8/9, glm-5.1 6/9, qwen 5/9).
set -uo pipefail
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
export OPENROUTER_API_KEY="$(op read 'op://Private/OpenRouter - Initial Retort Key/credential' 2>/tmp/op_err)"
if [ "${#OPENROUTER_API_KEY}" -lt 20 ]; then echo "KEY READ FAILED (len ${#OPENROUTER_API_KEY}):"; cat /tmp/op_err; exit 7; fi
echo "brazil swarm launch $(date +%H:%M:%S), key len ${#OPENROUTER_API_KEY}, 6 shards"

RUN="retort run --phase screening --config experiment-17/workspace.yaml \
     --design experiment-17/design-glm52.csv --replicates 3 --resume"
T=6
pids=()
# shard 0 first; db already exists from the firm run, but stagger anyway as insurance
$RUN --shard "0/$T" > "/tmp/glm52_brazil_shard0.log" 2>&1 &
pids+=($!); echo "  shard 0/$T -> pid ${pids[-1]}"
sleep 6
for ((i=1;i<T;i++)); do
  $RUN --shard "$i/$T" > "/tmp/glm52_brazil_shard${i}.log" 2>&1 &
  pids+=($!); echo "  shard $i/$T -> pid ${pids[-1]}"
done

echo "waiting on ${#pids[@]} shards..."
fail=0
for p in "${pids[@]}"; do wait "$p" || fail=$((fail+1)); done
echo "=== brazil swarm done $(date +%H:%M:%S), ${fail} shard process(es) exited non-zero ==="
grep -hE 'Done:' /tmp/glm52_brazil_shard*.log 2>/dev/null || echo "(no Done lines)"
