#!/usr/bin/env bash
# Overnight chain v2 (replaces v1 before any billed stage ran).
# CHANGE vs v1: budget guards. A 90-min glm-5.3 brazil cell measured $9.63 —
# 3-5x the per-cell estimate the §0d/0e budgets were written against. Caps:
#   after the 0d main pass: 0d spend > $50  -> skip 0d retry AND the 0e grid
#   before the 0e grid:     night spend > $70 -> skip the 0e grid
# The 0e SMOKE always runs (~$0.15) so the off-switch verdict lands either way.
set -uo pipefail
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
EL=experiments-local
log() { echo "STAGE $(date '+%H:%M:%S') $*"; }
spend() { # sum _cost_usd across the night's two new experiment dbs
  python3 - <<'EOF'
import sqlite3, os
total = 0.0
for d in ("experiments-local/experiment-mu-glm53-provider",
          "experiments-local/experiment-mu-glm53-thinking"):
    p = d + "/retort.db"
    if os.path.exists(p):
        row = sqlite3.connect(p).execute(
            "select coalesce(sum(value),0) from run_results where metric_name='_cost_usd'"
        ).fetchone()
        total += row[0] or 0.0
print(f"{total:.2f}")
EOF
}

log "0 waiting for glm53-brazil pass 3"
until ! pgrep -f "retort run" >/dev/null; do sleep 120; done
log "0 pass 3 finished"

log "1 reevaluate glm53-easy"
retort reevaluate --experiment-dir $EL/experiment-mu-glm53-easy \
  --eval-model claude-opus-4-8 --workers 2 \
  && log "1 easy reevaluate OK" || log "1 easy reevaluate FAILED"
log "1 reevaluate glm53-brazil"
retort reevaluate --experiment-dir $EL/experiment-mu-glm53-brazil \
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
S=$(spend); log "3 provider grid done rc=$rc spend=\$$S"
if python3 -c "exit(0 if $S <= 50 else 1)"; then
  $RUN --shard 0/1 > $P/retry.log 2>&1 || true
  log "3 provider retry pass done spend=\$$(spend)"
else
  log "3 BUDGET GUARD: \$$S > \$50 — skipping 0d retry and 0e grid"
fi

log "4 thinking smoke (0e)"
T=$EL/experiment-mu-glm53-thinking
if bash $T/smoke-thinking.sh > $T/smoke.log 2>&1; then
  log "4 thinking smoke PASS"
  S=$(spend)
  if python3 -c "exit(0 if $S <= 70 else 1)"; then
    log "4 running thinking grid (night spend \$$S)"
    RUN="retort run --phase screening --config $T/workspace.yaml --design $T/design.csv --replicates 3 --resume"
    $RUN --shard 0/2 > $T/shard0.log 2>&1 & p0=$!
    sleep 20
    $RUN --shard 1/2 > $T/shard1.log 2>&1 & p1=$!
    rc=0; wait $p0 || rc=$?; wait $p1 || rc=$?
    log "4 thinking grid done rc=$rc spend=\$$(spend)"
    $RUN --shard 0/1 > $T/retry.log 2>&1 || true
    log "4 thinking retry pass done spend=\$$(spend)"
  else
    log "4 BUDGET GUARD: night spend \$$S > \$70 — thinking grid SKIPPED"
  fi
else
  log "4 thinking smoke FAIL — grid SKIPPED (see $T/smoke.log)"
fi

log "5 final aggregate"
retort aggregate --experiments-dir $EL --out master-local.db --csv master-local.csv \
  && log "5 aggregate OK" || log "5 aggregate FAILED"
log "OVERNIGHT CHAIN COMPLETE night_spend=\$$(spend)"
