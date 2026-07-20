#!/usr/bin/env bash
# GLM-5.2 x claude-code brazil-bench arm. 3 shards, staggered (SQLite race #23).
# claude-code reaches GLM through OpenRouter's Anthropic-compatible endpoint.
set -uo pipefail
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
export ANTHROPIC_API_KEY="$(op read 'op://Private/OpenRouter - Initial Retort Key/credential' 2>/tmp/op_err)"
if [ "${#ANTHROPIC_API_KEY}" -lt 20 ]; then echo "KEY READ FAILED:"; cat /tmp/op_err; exit 7; fi
export ANTHROPIC_BASE_URL="https://openrouter.ai/api"
export ANTHROPIC_SMALL_FAST_MODEL="z-ai/glm-5.2"
echo "glm52-claudecode swarm launch $(date +%H:%M:%S), claude $(claude --version), 3 shards"

EXP=experiments-local/experiment-mu-glm52-claudecode
RUN="retort run --phase screening --config $EXP/workspace.yaml \
     --design $EXP/design.csv --replicates 3 --resume"
T=3
pids=()
$RUN --shard "0/$T" > /tmp/ccglm_shard0.log 2>&1 &
pids+=($!); echo "  shard 0/$T -> pid ${pids[-1]}"
while [ ! -f $EXP/retort.db ]; do sleep 1; done; sleep 4
for ((i=1;i<T;i++)); do
  $RUN --shard "$i/$T" > "/tmp/ccglm_shard${i}.log" 2>&1 &
  pids+=($!); echo "  shard $i/$T -> pid ${pids[-1]}"
done

echo "waiting on ${#pids[@]} shards..."
fail=0
for p in "${pids[@]}"; do wait "$p" || fail=$((fail+1)); done
echo "=== glm52-claudecode swarm done $(date +%H:%M:%S), ${fail} shard(s) non-zero ==="
grep -hE 'Done:' /tmp/ccglm_shard*.log 2>/dev/null || echo "(no Done lines)"
