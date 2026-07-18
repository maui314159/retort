#!/usr/bin/env bash
# GLM-5.2 brazil-bench rerun on omp 16.5.0 (post GLM tool-call fix, 0b9bdaae).
# 3 langs x 3 reps = 9 cells, 3-shard swarm into this dir's retort.db via
# --resume. Staggered start (shard 0 first) to avoid the SQLite cold-start
# race (#23) — same pattern as exp-17's run_glm52_brazil.sh.
set -uo pipefail
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
export OPENROUTER_API_KEY="$(op read 'op://Private/OpenRouter - Initial Retort Key/credential' 2>/tmp/op_err)"
if [ "${#OPENROUTER_API_KEY}" -lt 20 ]; then echo "KEY READ FAILED (len ${#OPENROUTER_API_KEY}):"; cat /tmp/op_err; exit 7; fi
echo "ompfix swarm launch $(date +%H:%M:%S), key len ${#OPENROUTER_API_KEY}, omp $(omp --version), 3 shards"

EXP=experiments-local/experiment-mu-glm52-ompfix
RUN="retort run --phase screening --config $EXP/workspace.yaml \
     --design $EXP/design.csv --replicates 3 --resume"
T=3
pids=()
$RUN --shard "0/$T" > "/tmp/ompfix_shard0.log" 2>&1 &
pids+=($!); echo "  shard 0/$T -> pid ${pids[-1]}"
sleep 8
for ((i=1;i<T;i++)); do
  $RUN --shard "$i/$T" > "/tmp/ompfix_shard${i}.log" 2>&1 &
  pids+=($!); echo "  shard $i/$T -> pid ${pids[-1]}"
done

echo "waiting on ${#pids[@]} shards..."
fail=0
for p in "${pids[@]}"; do wait "$p" || fail=$((fail+1)); done
echo "=== ompfix swarm done $(date +%H:%M:%S), ${fail} shard process(es) exited non-zero ==="
grep -hE 'Done:' /tmp/ompfix_shard*.log 2>/dev/null || echo "(no Done lines)"
