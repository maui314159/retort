#!/usr/bin/env bash
# kimi-k3 brazil-bench, opencode harness. 3 shards staggered.
set -uo pipefail
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
echo "kimi3-brazil swarm launch $(date +%H:%M:%S), opencode $(opencode --version), 3 shards"

EXP=experiments-local/experiment-mu-kimi3-brazil
RUN="retort run --phase screening --config $EXP/workspace.yaml \
     --design $EXP/design.csv --replicates 3 --resume"
T=3
pids=()
$RUN --shard "0/$T" > /tmp/kimi3_brazil_shard0.log 2>&1 &
pids+=($!); echo "  shard 0/$T -> pid ${pids[-1]}"
while [ ! -f $EXP/retort.db ]; do sleep 1; done; sleep 4
for ((i=1;i<T;i++)); do
  $RUN --shard "$i/$T" > "/tmp/kimi3_brazil_shard${i}.log" 2>&1 &
  pids+=($!); echo "  shard $i/$T -> pid ${pids[-1]}"
done

echo "waiting on ${#pids[@]} shards..."
fail=0
for p in "${pids[@]}"; do wait "$p" || fail=$((fail+1)); done
echo "=== kimi3-brazil swarm done $(date +%H:%M:%S), ${fail} shard(s) non-zero ==="
grep -hE 'Done:' /tmp/kimi3_brazil_shard*.log 2>/dev/null || echo "(no Done lines)"
