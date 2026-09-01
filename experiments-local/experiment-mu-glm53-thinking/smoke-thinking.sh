#!/usr/bin/env bash
# §0e REQUIRED smoke: prove the thinking off-switch takes effect through
# opencode, and that a thinking-starved model still emits well-formed tool
# calls. PASS criteria (pre-registered):
#   off arm: total reasoning tokens across step_finish == 0, >=1 completed
#            tool call, calc.py exists in the workspace
#   on  arm: total reasoning tokens > 0
# Exits 0 only if both arms pass. ~$0.15 of glm-5.3.
set -uo pipefail
BASE=$(mktemp -d "${TMPDIR:-/tmp}/glm53-think-smoke.XXXXXX")
PROMPT='Create calc.py with add(a,b) and sub(a,b), then run: python3 -c "import calc; print(calc.add(2,3))"'
fail=0
for ARM in on off; do
  WS=$BASE/$ARM; mkdir -p $WS
  python3 - "$WS" "$ARM" <<'EOF'
import json, sys
ws, arm = sys.argv[1], sys.argv[2]
opts = {"provider": {"order": ["parasail"], "allow_fallbacks": False}}
if arm == "off":
    opts["reasoning"] = {"max_tokens": 1}
perm = {t: "allow" for t in ("read","edit","glob","grep","list","bash","task")}
perm["external_directory"] = {"*": "allow"}
cfg = {"$schema": "https://opencode.ai/config.json", "permission": perm,
       "provider": {"openrouter": {"models": {"z-ai/glm-5.3": {"options": opts}}}}}
open(ws + "/opencode.json", "w").write(json.dumps(cfg))
EOF
  OPENCODE_CONFIG=$WS/opencode.json OPENCODE_DB=$WS/oc.db timeout 420 \
    opencode run --pure --format json --dir $WS \
    --model openrouter/z-ai/glm-5.3 "$PROMPT" > $WS/stdout.json 2> $WS/stderr.log
  rc=$?
  verdict=$(python3 - "$WS" "$ARM" "$rc" <<'EOF'
import json, os, sys
ws, arm, rc = sys.argv[1], sys.argv[2], int(sys.argv[3])
reasoning = 0; tools_completed = 0
for line in open(ws + "/stdout.json"):
    line = line.strip()
    if not line.startswith("{"): continue
    try: ev = json.loads(line)
    except Exception: continue
    p = ev.get("part", {})
    if ev.get("type") == "step_finish":
        reasoning += p.get("tokens", {}).get("reasoning", 0)
    if p.get("type") == "tool" and p.get("state", {}).get("status") == "completed":
        tools_completed += 1
calc = os.path.exists(ws + "/calc.py")
ok = (rc == 0 and calc and tools_completed >= 1
      and (reasoning == 0 if arm == "off" else reasoning > 0))
print(f"{'PASS' if ok else 'FAIL'} rc={rc} reasoning={reasoning} "
      f"tools_completed={tools_completed} calc_py={calc}")
sys.exit(0 if ok else 1)
EOF
) || fail=1
  echo "arm=$ARM: $verdict"
done
echo "smoke-thinking overall: $([ $fail -eq 0 ] && echo PASS || echo FAIL)"
exit $fail
