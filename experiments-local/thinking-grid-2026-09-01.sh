#!/usr/bin/env bash
# 0e thinking grid — manual follow-up: the day chain's budget guard read an
# empty spend value (transient locked-db) and mis-skipped this despite the
# smoke PASSING on parasail and real new spend (~$13.6) being under the $40
# line. Runs the grid + one retry pass, judges it, re-aggregates.
set -uo pipefail
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
EL=experiments-local
T=$EL/experiment-mu-glm53-thinking
log() { echo "STAGE $(date '+%H:%M:%S') $*"; }

log "W waiting for day chain"
until ! pgrep -f "retort run|retort reevaluate|day-2026-09-01.sh" >/dev/null; do sleep 60; done
log "W day chain finished"

log "G thinking grid"
RUN="retort run --phase screening --config $T/workspace.yaml --design $T/design.csv --replicates 3 --resume"
$RUN --shard 0/2 > $T/shard0.log 2>&1 & p0=$!
sleep 20
$RUN --shard 1/2 > $T/shard1.log 2>&1 & p1=$!
rc=0; wait $p0 || rc=$?; wait $p1 || rc=$?
log "G grid done rc=$rc"
$RUN --shard 0/1 > $T/retry.log 2>&1 || true
log "G retry pass done"

log "J reevaluate thinking"
retort reevaluate --experiment-dir $T --eval-model claude-opus-4-8 --workers 2 \
  && log "J OK" || log "J FAILED"

log "AGG aggregate"
retort aggregate --experiments-dir $EL --out master-local.db --csv master-local.csv \
  && log "AGG OK" || log "AGG FAILED"
SPENT=$(sqlite3 $T/retort.db "select round(coalesce(sum(value),0),2) from run_results where metric_name='_cost_usd'")
log "THINKING CHAIN COMPLETE thinking_spend=\$$SPENT"
