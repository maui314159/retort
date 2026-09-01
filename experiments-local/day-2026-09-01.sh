#!/usr/bin/env bash
# Day chain 2026-09-01 (user items 1-3): serial, one experiment at a time.
#   A. retry glm53-brazil's crashed 5.3 cell (--resume, 1 shard)
#   B. retry provider grid's crashed z-ai cell (--resume, 1 shard)
#   C. 0e off-switch smoke ON PARASAIL -> gate -> thinking grid + retry pass
#   D. reevaluate: brazil (new cells), provider grid, thinking grid (opus-4.8)
#   E. aggregate master-local
# Budget: new spend tracked vs the overnight baseline $72.78 (provider db) —
# guard skips the 0e grid if new spend already > $40 after the retries.
set -uo pipefail
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
EL=experiments-local
BASELINE=72.78
log() { echo "STAGE $(date '+%H:%M:%S') $*"; }
spend_new() {
  python3 - <<EOF
import sqlite3, os
total = 0.0
for d in ("$EL/experiment-mu-glm53-provider", "$EL/experiment-mu-glm53-thinking",
          "$EL/experiment-mu-glm53-brazil"):
    p = d + "/retort.db"
    if os.path.exists(p):
        total += sqlite3.connect(p).execute(
            "select coalesce(sum(value),0) from run_results where metric_name='_cost_usd'"
        ).fetchone()[0] or 0.0
# brazil pre-existing spend + provider baseline; brazil db held $23.08 before today
print(f"{total - $BASELINE - 23.08:.2f}")
EOF
}

log "A brazil retry (crashed 5.3 cell)"
B=$EL/experiment-mu-glm53-brazil
retort run --phase screening --config $B/workspace.yaml --design $B/design-brazil.csv \
  --replicates 3 --resume --shard 0/1 > $B/retry-0901.log 2>&1
log "A brazil retry done rc=$?"

log "B provider retry (crashed z-ai cell)"
P=$EL/experiment-mu-glm53-provider
retort run --phase screening --config $P/workspace.yaml --design $P/design.csv \
  --replicates 3 --resume --shard 0/1 > $P/retry-0901.log 2>&1
log "B provider retry done rc=$? new_spend=\$$(spend_new)"

log "C thinking smoke on parasail"
T=$EL/experiment-mu-glm53-thinking
if bash $T/smoke-thinking.sh > $T/smoke-parasail.log 2>&1; then
  log "C smoke PASS"
  S=$(spend_new)
  if python3 -c "exit(0 if $S <= 40 else 1)"; then
    RUN="retort run --phase screening --config $T/workspace.yaml --design $T/design.csv --replicates 3 --resume"
    $RUN --shard 0/2 > $T/shard0.log 2>&1 & p0=$!
    sleep 20
    $RUN --shard 1/2 > $T/shard1.log 2>&1 & p1=$!
    rc=0; wait $p0 || rc=$?; wait $p1 || rc=$?
    log "C thinking grid done rc=$rc new_spend=\$$(spend_new)"
    $RUN --shard 0/1 > $T/retry.log 2>&1 || true
    log "C thinking retry pass done new_spend=\$$(spend_new)"
  else
    log "C BUDGET GUARD: new spend \$$S > \$40 — thinking grid SKIPPED"
  fi
else
  log "C smoke FAIL on parasail — thinking grid SKIPPED (see $T/smoke-parasail.log)"
fi

log "D reevaluate brazil (new cells)"
retort reevaluate --experiment-dir $B --eval-model claude-opus-4-8 --workers 2 \
  && log "D brazil OK" || log "D brazil FAILED"
log "D reevaluate provider grid"
retort reevaluate --experiment-dir $P --eval-model claude-opus-4-8 --workers 2 \
  && log "D provider OK" || log "D provider FAILED"
log "D reevaluate thinking grid"
retort reevaluate --experiment-dir $T --eval-model claude-opus-4-8 --workers 2 \
  && log "D thinking OK" || log "D thinking FAILED"

log "E aggregate"
retort aggregate --experiments-dir $EL --out master-local.db --csv master-local.csv \
  && log "E aggregate OK" || log "E aggregate FAILED"
log "DAY CHAIN COMPLETE new_spend=\$$(spend_new)"
