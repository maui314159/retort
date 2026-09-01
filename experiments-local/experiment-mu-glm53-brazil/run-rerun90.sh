#!/usr/bin/env bash
# exp-mu-glm53-brazil rerun pass — crashed cells only, at the RAISED 90-min wall
# (see workspace.yaml comment). --resume skips the 5 completed cells and retries
# the 4 wall-crashed ones. 2 shards, both under the opencode <=3-4 ceiling.
set -uo pipefail
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
echo "glm53-brazil rerun90 launch $(date '+%F %H:%M:%S'), opencode $(opencode --version)"
EXP=experiments-local/experiment-mu-glm53-brazil
RUN="retort run --phase screening --config $EXP/workspace.yaml \
     --design $EXP/design-brazil.csv --replicates 3 --resume"
pids=()
$RUN --shard 0/2 > $EXP/rerun90-shard0.log 2>&1 &
pids+=($!); echo "  shard 0/2 -> pid ${pids[-1]}"
sleep 20
$RUN --shard 1/2 > $EXP/rerun90-shard1.log 2>&1 &
pids+=($!); echo "  shard 1/2 -> pid ${pids[-1]}"
rc=0
for pid in "${pids[@]}"; do wait "$pid" || rc=$?; done
echo "glm53-brazil rerun90 COMPLETE rc=$rc $(date '+%F %H:%M:%S')"
