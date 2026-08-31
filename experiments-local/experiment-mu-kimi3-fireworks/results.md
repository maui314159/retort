# exp-mu-kimi3-fireworks — pin the SERVING layer for Kimi K3 — GATE PROBE (2026-08-01, recovered from stash 2026-08-30)

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

**Next, in order:** (1) `retort reevaluate` these 2 cells for a real pass verdict; (2) settle
the sampling question; only then (3) size the 18-run screen.

**Open item:** pinning OpenRouter to a *named* upstream (`provider.only`) would let
quantization become a real factor (mxfp4 vs fp8 at fixed weights) rather than noise. Not
attempted yet — it needs OpenRouter routing body params through opencode, and the existing
openrouter auth path is known to break if given an `npm`/`options` override.

---

**CLOSE-OUT (2026-08-30, recovered from a 2026-08-01 stash; verdict from data-branch
commits `f9e589d1` and `7afdb830`).** The three "next" items resolved as follows, and the
arm was DROPPED:

1. `retort reevaluate` ran: **both cells PASS at requirement_coverage 1.0** (judge
   claude-opus-5) — identical to the unpinned OpenRouter baseline. Serving tier does not
   move pass-proportion; it moves speed and cost only.
2. The sampling question was settled by wire capture: opencode sends **temperature 0.7 on
   the openai-compatible path**, so the 2.3× step count is NOT a sampling artifact. It
   remains unexplained.
3. The 18-run screen was **cancelled**. Fireworks costs 2.7–3.5× the baseline for identical
   output, nothing in this program is time-critical, and the two baseline brazil crashes
   were wall-timeouts fixable for $0 with a bigger `timeout_minutes` (later refined: the
   csharp stall needed `stall_minutes=25`, not a longer wall — see the brazil close-out).

The residual finding that outlives the arm: the unpinned-OpenRouter baseline is a mixture
over ~9 upstreams at differing quantization (mxfp4 / fp8 / unreported) and cannot be
reconstructed after the fact. Filed upstream as a harness issue (record/pin the serving
provider). The `max_turns`-is-inert-for-opencode finding is documented on
`fix/serving-provider-plumbing`.
