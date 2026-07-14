#!/bin/bash
cd /Users/maui/dve/experiments/retort
source .venv/bin/activate
export ANTHROPIC_API_KEY="$(op read 'op://Private/Anthropic Oh-My-Pi API Key/credential')"
if [ "${#ANTHROPIC_API_KEY}" -lt 20 ]; then echo "ABORT: ANTHROPIC_API_KEY empty (op locked?) — not launching"; exit 1; fi
echo "anthropic key len=${#ANTHROPIC_API_KEY} — launching native Sonnet, 3 shards"
export PYTHONPATH=../retort-firmrun/src
RUN="retort run --phase screening --config experiment-19/workspace.yaml --design experiment-19/design.csv --replicates 3 --resume"
$RUN --shard 0/3 > experiment-19/shard0.log 2>&1 &
while [ ! -f experiment-19/retort.db ]; do sleep 1; done; sleep 6
for i in 1 2; do $RUN --shard $i/3 > experiment-19/shard$i.log 2>&1 & done
wait
echo "=== EXP-19 DONE ==="
grep -hE "Done:" experiment-19/shard*.log
sqlite3 experiment-19/retort.db "SELECT status, COUNT(*) FROM experiment_runs GROUP BY status;"
