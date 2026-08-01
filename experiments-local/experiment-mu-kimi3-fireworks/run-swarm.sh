#!/usr/bin/env bash
# kimi-k3 serving-layer gate probe: brazil-bench, python, 2 Fireworks tiers, 1 rep.
# 2 shards (one per tier) — well under the <=3-4 shard ceiling opencode tolerates.
set -uo pipefail
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate

# Fireworks auth. Read from a 0600 keyfile, NOT `op read`: the 1Password CLI
# needs the desktop agent, which a detached/background launch can't reach — it
# fails silently and takes the whole swarm with it. Stage the file from an
# interactive shell first:
#   umask 077; op read 'op://Private/Fireworks Test Key/credential' > "$FW_KEYFILE"
# The runner also FAILS FAST if the key is unset, but check here so the failure
# is one clear line instead of two dead shards.
FW_KEYFILE="${FW_KEYFILE:?set FW_KEYFILE to the path of the 0600 Fireworks key file}"
export FIREWORKS_API_KEY="${FIREWORKS_API_KEY:-$(cat "$FW_KEYFILE" 2>/dev/null)}"
if [ -z "$FIREWORKS_API_KEY" ]; then
  echo "FATAL: FIREWORKS_API_KEY unset and 1Password read failed." >&2
  exit 1
fi
echo "kimi3-fireworks probe launch $(date +%H:%M:%S), opencode $(opencode --version), 2 shards"

EXP=experiments-local/experiment-mu-kimi3-fireworks
RUN="retort run --phase screening --config $EXP/workspace.yaml \
     --design $EXP/design.csv --replicates 1 --resume"
T=2
pids=()
$RUN --shard "0/$T" > /tmp/kimi3_fw_shard0.log 2>&1 &
pids+=($!); echo "  shard 0/$T -> pid ${pids[-1]}"
# Shard 0 creates the db; the rest must not race it.
while [ ! -f $EXP/retort.db ]; do sleep 1; done; sleep 4
for ((i=1;i<T;i++)); do
  $RUN --shard "$i/$T" > "/tmp/kimi3_fw_shard${i}.log" 2>&1 &
  pids+=($!); echo "  shard $i/$T -> pid ${pids[-1]}"
done

echo "waiting on ${#pids[@]} shards..."
fail=0
for p in "${pids[@]}"; do wait "$p" || fail=$((fail+1)); done
echo "=== kimi3-fireworks probe done $(date +%H:%M:%S), ${fail} shard(s) non-zero ==="
grep -hE 'Done:' /tmp/kimi3_fw_shard*.log 2>/dev/null || echo "(no Done lines)"
