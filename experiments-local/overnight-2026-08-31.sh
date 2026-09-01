#!/usr/bin/env bash
# Overnight chain 2026-08-31 (user asleep; ONE experiment at a time, serial):
#   0. wait for the in-flight glm53-brazil pass 3
#   1. retort reevaluate (opus-4.8 judge) on glm53-easy + glm53-brazil
#   2. aggregate to master-local.* (NEVER root master.db)
#   3. §0d provider grid   (9 brazil cells, ~$10-25)
#   4. §0e thinking smoke; grid ONLY if smoke passes (6 cells, ~$10)
# Each stage logs a STAGE line; failures stop dependent stages only.
set -uo pipefail
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
EL=experiments-local
log() { echo "STAGE $(date '+%H:%M:%S') $*"; }

log "0 waiting for glm53-brazil pass 3"
until ! pgrep -f "retort run" >/dev/null; do sleep 120; done
log "0 pass 3 finished"

log "1 reevaluate glm53-easy"
retort reevaluate --experiment-dir $EL/experiment-mu-glm53-easy \
  --eval-model claude-opus-4-8 --workers 2 \
  && log "1 easy reevaluate OK" || log "1 easy reevaluate FAILED"
log "1 reevaluate glm53-brazil"
retort reevaluate --experiment-dir $EL/experiment-mu-glm53-brazil \
  --config $EL/experiment-mu-glm53-brazil/workspace.yaml \
  --eval-model claude-opus-4-8 --workers 2 \
  && log "1 brazil reevaluate OK" || log "1 brazil reevaluate FAILED"

log "2 aggregate master-local"
retort aggregate --experiments-dir $EL --out master-local.db --csv master-local.csv \
  && log "2 aggregate OK" || log "2 aggregate FAILED"

log "3 provider grid (0d)"
P=$EL/experiment-mu-glm53-provider
RUN="retort run --phase screening --config $P/workspace.yaml --design $P/design.csv --replicates 3 --resume"
$RUN --shard 0/2 > $P/shard0.log 2>&1 & p0=$!
sleep 20
$RUN --shard 1/2 > $P/shard1.log 2>&1 & p1=$!
rc=0; wait $p0 || rc=$?; wait $p1 || rc=$?
log "3 provider grid done rc=$rc"
# one retry pass for stall-crashed cells (the known z-ai hang mode)
$RUN --shard 0/1 > $P/retry.log 2>&1 || true
log "3 provider retry pass done"

log "4 thinking smoke (0e)"
T=$EL/experiment-mu-glm53-thinking
if bash $T/smoke-thinking.sh > $T/smoke.log 2>&1; then
  log "4 thinking smoke PASS — running grid"
  RUN="retort run --phase screening --config $T/workspace.yaml --design $T/design.csv --replicates 3 --resume"
  $RUN --shard 0/2 > $T/shard0.log 2>&1 & p0=$!
  sleep 20
  $RUN --shard 1/2 > $T/shard1.log 2>&1 & p1=$!
  rc=0; wait $p0 || rc=$?; wait $p1 || rc=$?
  log "4 thinking grid done rc=$rc"
  $RUN --shard 0/1 > $T/retry.log 2>&1 || true
  log "4 thinking retry pass done"
else
  log "4 thinking smoke FAIL — grid SKIPPED (see $T/smoke.log)"
fi

log "5 final aggregate"
retort aggregate --experiments-dir $EL --out master-local.db --csv master-local.csv \
  && log "5 aggregate OK" || log "5 aggregate FAILED"
log "OVERNIGHT CHAIN COMPLETE"
