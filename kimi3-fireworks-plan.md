# exp-mu-kimi3-fireworks — local experiment plan + probe result

Local-only (fork). Kept OUT of the tracked `docs/future-experiments.md`: that file is
upstream's queue, and local fork experiments there would conflict on every upstream sync.
See `.git/info/exclude`, which lists the other local write-ups.

## 0d. exp-mu-kimi3-fireworks — pin the SERVING layer for Kimi K3  — GATE PROBE (2026-08-01)

**Why.** Not a new model. OpenRouter's `moonshotai/kimi-k3` resolves to canonical slug
`kimi-k3-20260715`; the July 2026 runs (`experiment-mu-kimi3-easy` 2026-07-18,
`experiment-mu-kimi3-brazil` 2026-07-18/19) hit that same and only snapshot. Fireworks
registered its copy 2026-07-19. **Same weights — what differs is the serving layer.**

**The flaw this exposes.** OpenRouter fans `kimi-k3` out across ~9 upstream endpoints at
*differing quantization* — Moonshot AI and Modal at `mxfp4`, BaseTen and Wafer at `fp8`,
Fireworks/Morph/DigitalOcean/Together unreported — in two price tiers (\$3/\$15 standard,
\$4.50/\$22.50 premium). The July runs used the bare string `openrouter/moonshotai/kimi-k3`
with **no provider pin**, and `upstream_provider` is empty for every run (opencode's event
stream carries no `upstreamProvider`; omp's does). So each of those 9 brazil cells may have
been served by a different upstream at a different quantization, **and it cannot be
reconstructed after the fact.** Their "7/9 at \$3.08 / 44 min" is a *mixture over an
uncontrolled stack factor*, not a measurement of K3. Quantization and serving layer are
named factors in the stack definition — this is precisely the confound the harness exists
to catch, and we shipped it.

**Hypothesis (recorded up front).** Going direct to Fireworks *pins* the serving layer. The
two July crashes were 60-min wall-timeouts — slowness, not incapability — so:
**H1** the `-fast` router (+50% price, measured 108.6 vs 58.7 tok/s on a trivial probe)
converts wall-timeout crashes into completions; **H2** pass-proportion at fixed weights
moves with serving tier, i.e. the serving layer is a real factor, not bookkeeping. A null
(identical pass and duration across tiers) is equally publishable — it would say the
aggregator's routing was harmless and the July numbers stand.

**Gate probe first (this entry).** brazil-bench × python × {`kimi-k3`, `kimi-k3-fast`} × 1 rep
= **2 runs**, to measure real cost / wall-time / pass on a *pinned* stack before sizing the
grid. Full screen (3 languages × 3 reps × 2 tiers = 18 runs) is gated on this.

**Harness work landed with it** (all verified, not just set):
- opencode can now address a non-native provider as an OpenAI-compatible endpoint
  (`--pure` disables the models.dev catalog, so baseURL + key must come from the workspace
  config). Key written as `{env:FIREWORKS_API_KEY}`, **never inlined** — that file is
  archived and committed.
- **Cost is derived** from tokens against `FIREWORKS_PRICING` (\$3.00/\$15.00; cached input
  \$0.30): opencode reports `cost: 0` for a custom provider, verified by probe, which would
  have silently zeroed the cost and token_efficiency responses.
- **Fast-mode landmine fixed.** `_is_fast_mode_model` matched any `-fast` suffix, so
  `accounts/fireworks/routers/kimi-k3-fast` would have taken Anthropic's 2× fast-mode
  multiplier *on top of* the +50% tier — 3× the true spend. It was dormant only because the
  multiplier is guarded by `cost_usd > 0`; adding derived pricing is exactly what would have
  armed it. Now scoped to Claude ids, with a regression test.
- **Serving attribution recorded** on every opencode run (`serving_provider`,
  `serving_model_id`, `serving_endpoint`, `serving_upstream`). A brokered run is explicitly
  stamped `unrecorded` / `unavailable:opencode` rather than left silently ambiguous.
- Missing provider key now **fails up front** instead of 401-ing per turn into a
  content-free run indistinguishable from a model that wrote nothing.

**PROBE RESULT (2026-08-01, n=1 per arm, python/brazil-bench).** Both cells cleared the
mechanical gate; **0 crashes** (baseline: 2/9, though none in python). Spec gate NOT yet run
— `evaluation.enabled: false`, so there is no `requirement_coverage` verdict comparable to
the baseline's 1.0. The mechanical gate only proves the tests ran.

| arm | wall | cost | tokens | steps | mean ctx |
|---|---|---|---|---|---|
| fireworks standard | 38.0 min | \$6.61 | 14.7M | 135 | 108K |
| fireworks fast | 23.3 min | \$8.63 | 12.7M | 121 | 104K |
| baseline OR unpinned (python ×3) | 25.9 / 28.6 / 41.5 min | \$2.03 / 2.28 / 3.00 | 3.4–4.8M | 51–58 | 66–81K |

- **H1 — weakly supported.** The fast router is **1.63× faster** wall-clock and neither arm
  hit the 60-min wall. But the baseline's *python* cells never crashed either (the 2 crashes
  were other languages), so "converts crashes into passes" is **not** yet demonstrated.
- **Unexpected: cost went the WRONG way** — 2.7–3.5× the baseline. Cause identified as
  **more turns, not bigger turns**: ~128 steps vs ~55 (2.3×) at ~1.4× mean context = the 3.3×
  token blow-up. Verified not a metering artifact: opencode reported \$0.0000 for both (the
  cost gap is real), derived cost reproduces the recorded figures exactly, the fast arm is
  1.5× (not 3× — fast-mode landmine confirmed defused in a live run), and the baseline counts
  cache reads identically so the token comparison is apples-to-apples. Cache reads dominate
  (14.4M cached vs 228K fresh); the \$0.30/Mtok cached tier is what keeps this affordable.
- **BLOCKER for the screen — sampling is unverified across provider paths.** Neither path
  sets temperature explicitly, so each inherits its own default: opencode's *native* OpenRouter
  integration vs the `@ai-sdk/openai-compatible` wrapper. A sampling difference alone could
  produce a 2.3× turn-count difference, in which case the screen would be measuring **plumbing,
  not serving tier**. Resolve before spending on 18 runs. (opencode exposes no temperature flag;
  `--variant` sets provider reasoning effort. Both are unset today — i.e. unrecorded, the exact
  failure mode this file exists to prevent.)
- **`playpen.max_turns` is INERT for `agent=opencode`** — `--max-turns` is passed only to the
  claude-code harness, and `opencode run` has no turn-cap flag at all (checked `--help`). The
  Fireworks arms ran 135/121 steps against a nominal cap of 100. This affects **every**
  opencode experiment, not just this one; only the wall-clock timeout actually bounds them.
  Drop the factor or document it as unenforceable — do not leave it implying a bound.

## CONCLUSION (2026-08-01) — CLOSED. Screen CANCELLED; stay on OpenRouter.

**Spec gate: both cells PASS at `requirement_coverage = 1.0`** (judge pinned
`claude-opus-5`, 2/2 matched, 0 orphaned) — the same 1.0 the unpinned OpenRouter
baseline recorded.

**H2 is a NULL: serving tier does not move pass-proportion.** Same weights, same 1.0,
whether brokered through OpenRouter or pinned to either Fireworks tier. What the serving
layer moves is speed and cost, not correctness.

**H1 is untested, and now moot.** The fast router is 1.63× faster and neither arm hit the
wall — but the baseline's *python* cells never crashed either (the 2 crashes were other
languages), so "converts crashes into passes" was never demonstrated on this cell.

**Decision: drop the Fireworks arm.** Speed was its only advantage; correctness is
identical and it costs 2.7–3.5× the baseline. **Nothing in this program is time-critical**
(user, 2026-08-01), so we would be paying a premium for the one thing we don't need. The
two baseline crashes were *wall-timeout* crashes, and the fix for those is a bigger
`timeout_minutes` — \$0, and it works for every model and language rather than just this
one. Paying +50%/token to finish sooner only pays when finishing sooner is worth something.

**The 18-run screen is cancelled**, not deferred: it was designed to test whether serving
tier moves pass, and pass is saturated at 1.0. Spending \$50–60 to re-confirm a null on a
saturated response is poor value.

### Sampling — partially settled, and it corrected an assumption

- **[DIRECT] opencode DOES send `temperature: 0.7`.** It is not unset, as first assumed.
  Captured on the wire against a mock OpenAI-compatible endpoint; full body is
  `{messages, model, temperature: 0.7}` — no top_p/top_k/max_tokens/seed/penalties.
- **[DIRECT] temperature comes from the agent and model, not the transport:**
  `model.capabilities.temperature ? agent.temperature ?? default(model) : undefined`.
- **[OPEN] whether the July OpenRouter runs also ran at 0.7.** opencode ignores a
  `baseURL` override for its *built-in* providers, so that path can't be intercepted, and
  the default is a function of the **model id** — which differs between the two paths
  (`moonshotai/kimi-k3` vs `accounts/fireworks/models/kimi-k3`). Parity is plausible
  (both are unlisted models under `--pure`, so the same fallback should apply) but
  **[HYPOTHESIS]**, not established.
- Consequence: the 2.3× turn gap is **not** explained by "one path sets temperature and
  the other doesn't". If it is ever worth chasing (~\$15, a temperature-pinned 2-cell
  repeat), the finding would be that the serving stack changes agent *behaviour* at fixed
  weights — interesting, but it buys no routing decision. Parked.
- Regardless: **pin `temperature` explicitly** in any future opencode workspace. That
  removes the variable by construction instead of arguing parity.

### What this probe actually bought, for ~\$15

Four live harness bugs, all fixed on `fix/serving-provider-plumbing` except the last:
dead provenance capture (nothing on this machine had written a `provenance.json` since
Hermes changed its config schema), the `-fast` suffix that would have triple-billed the
Fireworks router, opencode's `cost: 0` for custom providers, and `max_turns` being inert
for opencode (documented, not fixed). Two of those are still live upstream.

**Open item:** pinning OpenRouter to a *named* upstream (`provider.only`) would let
quantization become a real factor (mxfp4 vs fp8 at fixed weights) rather than noise. Not
attempted yet — it needs OpenRouter routing body params through opencode, and the existing
openrouter auth path is known to break if given an `npm`/`options` override.



---

## exp-mu-kimi3-brazil — CLOSE-OUT (2026-08-02). Final: 8/8 at 1.00, one cell carried as `stall`.

Step 2 of the K3 evaluation, closed the day after the Fireworks arm was dropped.

**Result: every completed run implements the spec.** 8 of 9 cells completed; all 8 score
`requirement_coverage = 1.0` (judge `claude-opus-5`). The ninth — csharp rep2 — never
produced a result and is carried as a **stall**, not a model failure.

| language | rep1 | rep2 | rep3 |
|---|---|---|---|
| python | 1.0 | 1.0 | 1.0 |
| typescript | 1.0 | 1.0 (36.3 min, $4.15) | 1.0 |
| csharp | 1.0 (38.0 min, $3.19) | **stall** | 1.0 (36.3 min, $2.59) |

### The csharp rep2 stall — and two wrong readings it survived

Full evidence in `runs/…language=csharp…/rep2-stalled/DIAGNOSIS.md`, preserved from the temp
workspace before cleanup.

The cell crashed twice: once at a 60-min wall (2026-07-18), once at a 120-min wall
(2026-08-02). The second attempt did 12 steps of real work in 16 minutes, started step 13,
fired a `todowrite`, and then **went silent for 1h44m** — zero events, zero stdout bytes,
zero file writes, and not one `level=ERROR` line. `step_start` = 13, `step_finish` = 12: the
opencode↔OpenRouter stream hung and the hard wall was the only thing that ended it.

**Wrong reading #1 — "permission failure."** `error_message` in `retort.db` truncates at
`… action.permiss`, which reads like a denial. The full line is
`action.permission=bash action.action=allow` — permission being *granted*, in an INFO line.

**Wrong reading #2 — "wall-timeout, so raise `timeout_minutes`."** This is what drove the
60→120 bump, and it was the wrong remedy: it bought a second, longer idle burn. A stall is
invisible to `timeout_minutes` **by construction** — the wall measures elapsed time, and a
hung run and a slow run are identical to it. Only a *progress* signal tells them apart. The
same bump was right for typescript, which was genuinely slow-but-productive and completed in
36 min; one remedy, two cells, right for one and wrong for the other.

**Root cause of the waste: `playpen.stall_minutes` defaults to `0` = DISABLED.** The guard
that exists for precisely this failure was silently off, in all six local workspaces. Now set
to **25** in every one (the modal value across the repo's other 30 workspaces that set it),
and verified to reach the guard end-to-end: yaml → `PlaypenConfig.stall_minutes` →
`cli.py:789` → `LocalPlaypenRunner` → `stall_secs = 1500` → `_run_with_progress_guard`. At 25
this run would have died ~09:59 instead of 11:17 and been *labelled* `stall`.

This is the CLAUDE.md silent-parameter class, one notch worse than set-but-unverified: never
set at all, defaulting to off, and its absence invisible in the results.

### [DIRECT] `retort diagnose` recommended a false PASS on this cell

`retort recover` labelled the July csharp rep2 archive **TOOLING** — "tests now run and
measure 100% coverage — scorer false-failure (rescore recovers it)". It is wrong. That run
wrote 8 real source files but never got to tests before the wall; the only test in the
archive is the untouched xUnit scaffold:

```csharp
[Fact]
public void Test1() { }
```

An empty body makes `dotnet test` pass and coverage report degenerately — the known C#
false-PASS trap. Had `rescore` acted on the recommendation, the cell would have been recorded
as a **pass with zero real tests**. `rescore` recovered 0 runs, but by luck rather than by
design: the DB row is `crashed`, and `--only-failed` selects `failed`. **A `crashed` row that
diagnose calls TOOLING is a false-PASS waiting for someone to flip its status.**

### [DIRECT] Crashed runs under-report cost

The stalled run's own `step_finish` events carry usage across its 12 finished steps:
`cost $0.6388`, input 93,024, output 4,162, reasoning 12,734. `retort.db` records **$0.00**.
Real spend, absent from the ledger. Small here; crash-heavy experiments will understate cost
systematically, and cost is load-bearing for the published findings.

### [DIRECT] Every opencode run carries the operator's global skills

opencode startup loads `~/.claude/skills/` and `~/.agents/skills/` into the agent under test —
seven `gitnexus-*` skills, logged as duplicate-name warnings. `--pure` does not prevent it.
This is an uncontrolled, machine-specific tool surface that no `provenance.json` records, and
it affects **every** opencode experiment in this repo, not just this one.

### Where K3 stands after both steps

- easy grid (`exp-mu-kimi3-easy`): **15/15 at 1.0**
- hard task (`exp-mu-kimi3-brazil`): **8/8 completed at 1.0**, 1 stall
- serving layer (`exp-mu-kimi3-fireworks`): **null** — pinning the serving tier does not move
  pass-proportion; it moves speed and cost only. Arm dropped.

K3 does not miss the spec on either task. What it costs is time: ~30–40 min per brazil cell.
