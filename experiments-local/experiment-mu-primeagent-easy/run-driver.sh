#!/usr/bin/env bash
# exp-mu-primeagent driver (§0b) — first production family on the sandbox lane.
# Serial grids (easy -> brazil), 3 shards each (3 concurrent Fargate cells;
# host footprint is polling only). Budget guard between stages: skip brazil if
# easy already spent > $15; hard stop line $40 total.
set -uo pipefail
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
EL=experiments-local
log() { echo "STAGE $(date '+%F %H:%M:%S') $*"; }
spend() {
  .venv/bin/python - <<'EOF'
import sqlite3, os
t=0.0
for d in ("experiments-local/experiment-mu-primeagent-easy","experiments-local/experiment-mu-primeagent-brazil"):
    p=d+"/retort.db"
    if os.path.exists(p):
        t+=sqlite3.connect(p).execute("select coalesce(sum(value),0) from run_results where metric_name='_cost_usd'").fetchone()[0] or 0.0
print(f"{t:.2f}")
EOF
}

run_grid() {
  local exp=$1
  local RUN="retort run --phase screening --config $exp/workspace.yaml --design $exp/design.csv --replicates 3 --resume"
  local pids=()
  $RUN --shard 0/3 > $exp/shard0.log 2>&1 & pids+=($!)
  sleep 20
  $RUN --shard 1/3 > $exp/shard1.log 2>&1 & pids+=($!)
  $RUN --shard 2/3 > $exp/shard2.log 2>&1 & pids+=($!)
  local rc=0
  for p in "${pids[@]}"; do wait "$p" || rc=$?; done
  # one retry pass for crashed cells (unpinned routing hangs are expected;
  # the in-container stall watchdog converts them to fast fails)
  $RUN --shard 0/1 > $exp/retry.log 2>&1 || true
  return $rc
}

log "easy grid"
run_grid $EL/experiment-mu-primeagent-easy || true
S=$(spend); log "easy done spend=\$${S:-unknown}"
if [ -n "$S" ] && .venv/bin/python -c "exit(0 if $S <= 15 else 1)" 2>/dev/null; then
  log "brazil grid"
  run_grid $EL/experiment-mu-primeagent-brazil || true
  log "brazil done spend=\$$(spend)"
else
  log "BUDGET GUARD: easy spend \$${S:-unreadable} > \$15 (or unreadable) — brazil SKIPPED"
fi

log "judge easy"
retort reevaluate --experiment-dir $EL/experiment-mu-primeagent-easy \
  --eval-model claude-opus-4-8 --workers 2 && log "judge easy OK" || log "judge easy FAILED"
if [ -f $EL/experiment-mu-primeagent-brazil/retort.db ]; then
  log "judge brazil"
  retort reevaluate --experiment-dir $EL/experiment-mu-primeagent-brazil \
    --eval-model claude-opus-4-8 --workers 2 && log "judge brazil OK" || log "judge brazil FAILED"
fi

log "aggregate"
retort aggregate --experiments-dir $EL --out master-local.db --csv master-local.csv \
  && log "aggregate OK" || log "aggregate FAILED"
log "PRIMEAGENT CHAIN COMPLETE spend=\$$(spend)"
