#!/usr/bin/env bash
# Smoke test: claude-code CLI driving GLM-5.2 via OpenRouter's Anthropic endpoint.
# Pass = greet.py + test_greet.py written by tool calls, pytest 2/2, result event sane.
set -uo pipefail
SD="$(mktemp -d /tmp/cc-glm-smoke.XXXXXX)"
cd "$SD"
export ANTHROPIC_API_KEY="$(op read 'op://Private/OpenRouter - Initial Retort Key/credential')"
export ANTHROPIC_BASE_URL="https://openrouter.ai/api"
export ANTHROPIC_SMALL_FAST_MODEL="z-ai/glm-5.2"
export CLAUDE_CODE_NON_INTERACTIVE=1
echo "smoke dir: $SD"
timeout 300 claude -p "Create greet.py with greet(name) returning 'Hello, <name>!' and test_greet.py with two pytest tests. Use your file-writing tools." \
  --model z-ai/glm-5.2 --output-format stream-json --verbose --max-turns 15 \
  --dangerously-skip-permissions > out.jsonl 2> err.log
echo "rc=$?"
ls -la
echo "--- result event ---"
tail -1 out.jsonl | python3 -c "import json,sys;d=json.loads(sys.stdin.read());print({k:d.get(k) for k in ('type','subtype','total_cost_usd','num_turns','is_error')})" || tail -2 out.jsonl
echo "--- pytest ---"
[ -f test_greet.py ] && python3 -m pytest -q test_greet.py
