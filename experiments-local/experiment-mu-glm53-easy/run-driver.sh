#!/usr/bin/env bash
# exp-mu-glm53 driver — SERIAL: easy grid (rest-api-crud) then brazil grid.
# Pre-registered docs/future-experiments.md §0a. One experiment at a time on
# this machine (CLAUDE.md); this script IS the queue for the two grids.
#
# opencode auth: ~/.local/share/opencode/auth.json (the dedicated OpenRouter
# opencode key) — no env var needed. Provider pin + OPENCODE_CONFIG come from
# the workspace profile + runner (see workspace.yaml header).
set -uo pipefail
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate

OCV=$(opencode --version)
if [ "$OCV" = "1.18.15" ]; then
  echo "FATAL: opencode 1.18.15 hangs on model options; need >= 1.18.20" >&2
  exit 1
fi
echo "exp-mu-glm53 launch $(date '+%F %H:%M:%S'), opencode $OCV, retort $(git rev-parse --short HEAD)"

run_grid() {
  local exp=$1 design=$2 shards=$3
  local RUN="retort run --phase screening --config $exp/workspace.yaml \
       --design $exp/$design --replicates 3 --resume"
  local pids=()
  # Shard 0 creates the db; the rest must not race it.
  $RUN --shard "0/$shards" > "$exp/shard0.log" 2>&1 &
  pids+=($!); echo "  $exp shard 0/$shards -> pid ${pids[-1]}"
  sleep 20
  for ((i=1; i<shards; i++)); do
    $RUN --shard "$i/$shards" > "$exp/shard$i.log" 2>&1 &
    pids+=($!); echo "  $exp shard $i/$shards -> pid ${pids[-1]}"
  done
  local rc=0
  for pid in "${pids[@]}"; do wait "$pid" || rc=$?; done
  echo "  $exp done rc=$rc $(date '+%H:%M:%S')"
  return $rc
}

run_grid experiments-local/experiment-mu-glm53-easy design-easy.csv 3
run_grid experiments-local/experiment-mu-glm53-brazil design-brazil.csv 3
echo "exp-mu-glm53 driver COMPLETE $(date '+%F %H:%M:%S')"
