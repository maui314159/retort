# experiment-mu-sandbox-shakedown — §0c SandboxRunner shakedown (2026-08-31)

rest-api-crud x openrouter/z-ai/glm-5.3-flash x n=3, run through the AWS
Batch/Fargate sandbox lane (`SandboxRunner`, branch feat/sandbox-runner
@ 12f3719c), all three cells CONCURRENTLY, z-ai provider pin, in-container
v1 mechanical gate (pytest+coverage).

Stack (tuning parameters, identical across cells):
- image: retort-sandbox:python-v2
  digest sha256:f1b82a01d678ca9268665a817f885c30670dbc98eded80b55407e988dbbd78a6
  (opencode 1.18.20 pinned)
- job definition retort-sandbox-python revision 2, 2 vCPU / 8192 MB Fargate
- opencode --pure headless, OpenRouter provider pin {order:[z-ai],
  allow_fallbacks:false}

## Results (results.json)

| rep | mech gate | tests | coverage | agent_s | queue_s | tokens | cost |
|----:|:--|:--|--:|--:|--:|--:|--:|
| 1 | PASS | 22/22 | 91.18% | 427.5 | 50.0 | 236,173 | $0.0083 |
| 2 | PASS | 7/7 | 95.72% | 296.7 | 52.9 | 198,083 | $0.0071 |
| 3 | PASS | 27/27 | 94.79% | 526.9 | 55.9 | 469,884 | $0.0141 |

**Mechanical pass 3/3 — agrees with the local lane** (exp-mu-glm53-easy's
flash cells: 3/3 completed, coverage 0.92–0.99). Durations are NOT compared
across lanes (different hardware; recorded only). Spec-gate judging
(requirement_coverage) has not been run on these cells.

DO NOT aggregate this directory into master-local.* or the root master.db —
it is a methodology validation, not an experiment.
