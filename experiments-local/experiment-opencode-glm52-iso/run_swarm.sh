#!/usr/bin/env bash
set -uo pipefail
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
export PYTHONPATH=/Users/maui/dve/experiments/retort-opencode/src   # worktree code WITH the isolation fix
echo "opencode glm-5.2 ISOLATED-db swarm launch $(date +%H:%M:%S), 8 shards"
RUN="python -m retort.cli run --phase screening \
     --config experiment-opencode-glm52-iso/workspace.yaml \
     --design experiment-opencode-glm52-iso/design-opencode.csv --replicates 3 --resume"
T=8
$RUN --shard "0/$T" > "/tmp/oc_iso_shard0.log" 2>&1 &
pids=($!)
while [ ! -f experiment-opencode-glm52-iso/retort.db ]; do sleep 1; done; sleep 4
for ((i=1;i<T;i++)); do $RUN --shard "$i/$T" > "/tmp/oc_iso_shard${i}.log" 2>&1 & pids+=($!); done
echo "waiting on ${#pids[@]} shards..."
fail=0; for p in "${pids[@]}"; do wait "$p" || fail=$((fail+1)); done
echo "=== ISOLATED swarm done $(date +%H:%M:%S), ${fail} non-zero ==="
grep -hE 'Done:' /tmp/oc_iso_shard*.log 2>/dev/null
