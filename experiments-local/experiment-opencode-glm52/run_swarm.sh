#!/usr/bin/env bash
# opencode glm-5.2 easy-grid swarm (5 langs x 3 reps = 15 cells), 8 shards into
# experiment-opencode-glm52/retort.db. Runs the feat/opencode-harness WORKTREE code
# via PYTHONPATH (the harness isn't in the main checkout). opencode authenticates
# from ~/.local/share/opencode/auth.json (the dedicated OpenCode key) — no env key,
# so omp's OPENROUTER_API_KEY is deliberately NOT exported here. Staggered start to
# dodge the SQLite cold-start race (#23).
set -uo pipefail
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
export PYTHONPATH=/Users/maui/dve/experiments/retort-opencode/src
echo "opencode glm-5.2 swarm launch $(date +%H:%M:%S), 8 shards (worktree code, auth.json)"

RUN="python -m retort.cli run --phase screening \
     --config experiment-opencode-glm52/workspace.yaml \
     --design experiment-opencode-glm52/design-opencode.csv --replicates 3 --resume"
T=8
$RUN --shard "0/$T" > "/tmp/oc_glm52_shard0.log" 2>&1 &
pids=($!); echo "  shard 0/$T -> pid ${pids[-1]}"
while [ ! -f experiment-opencode-glm52/retort.db ]; do sleep 1; done; sleep 4
for ((i=1;i<T;i++)); do
  $RUN --shard "$i/$T" > "/tmp/oc_glm52_shard${i}.log" 2>&1 &
  pids+=($!); echo "  shard $i/$T -> pid ${pids[-1]}"
done

echo "waiting on ${#pids[@]} shards..."
fail=0
for p in "${pids[@]}"; do wait "$p" || fail=$((fail+1)); done
echo "=== swarm done $(date +%H:%M:%S), ${fail} shard process(es) exited non-zero ==="
grep -hE 'Done:' /tmp/oc_glm52_shard*.log 2>/dev/null || echo "(no Done lines)"
