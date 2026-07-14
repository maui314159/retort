# experiment-15 results — open-weight models via OpenRouter (pilot)

**Pilot scope:** `language=[python] × model=[8 OpenRouter models] × tooling=[none]`,
1 replicate, on `rest-api-crud` (easy task), through the open-source `omp` harness.
Purpose: (a) do the 8 models each drive omp to a built-and-tested project, and
(b) validate per-run cost against OpenRouter billing. Run 2026-06-13. See
[`PILOT.md`](PILOT.md) for the design, auth model, and build log.

**Headline:** 5/8 pass. All 3 failures are GENUINE (`retort diagnose`: 0 TOOLING).
omp under-reported the pilot's cost **97%** ($0.069 reported vs **$2.41 billed**) —
a per-turn-vs-last-turn accounting bug (fixed; see findings). Cost below is the
**billed** figure reconciled from OpenRouter's `/api/v1/generation`, not omp's.

## Capability & quality

| # | Model | Result | CodeQual | TestCov | Defect | Maint | Speed |
|--:|---|:--:|--:|--:|--:|--:|--:|
| 1 | kimi-k2.7-code | ✅ pass | 0.77 | 0.99 | 1.00 | 1.00 | 202 s |
| 2 | minimax-m3 | ✅ pass | 0.82 | 0.98 | 0.93 | 0.88 | 247 s |
| 4 | deepseek-v3.2 | ✅ pass | 0.67 | 0.93 | 0.94 | 0.95 | **882 s** |
| 5 | qwen3.7-plus | ✅ pass | 0.62 | 0.91 | 1.00 | 1.00 | 191 s |
| 8 | **opus-4.8** (baseline) | ✅ pass | 0.83 | 0.99 | 1.00 | 0.94 | 114 s |
| 3 | mimo-v2.5 | ❌ genuine | — | — | — | — | 81 s |
| 6 | nemotron-3-ultra:free | ❌ genuine | — | — | — | — | 275 s |
| 7 | owl-alpha (stealth) | ❌ genuine | — | — | — | — | 111 s |

The 3 failures hit the mechanical gate (tests did not run on the produced code);
`retort diagnose` classified all three **GENUINE** (0 TOOLING) — real model
failures, not scorer false-fails. The two $0 infra-risk models (nemotron:free,
owl-alpha) both failed, as flagged pre-run; mimo-v2.5 (cheapest paid) also failed.

## Cost reconciliation — omp vs OpenRouter billing

`billed$` = sum of `GET /api/v1/generation` over the run's generation ids (the
authoritative figure). `omp$` = what retort recorded before the fix (last turn
only). `sumturns$` = sum of omp's per-turn costs.

| # | Model | turns | omp $ | sumturns $ | **billed $** | Δ omp | upstream |
|--:|---|--:|--:|--:|--:|--:|---|
| 1 | kimi-k2.7-code | 14 | 0.00969 | 0.13986 | **0.13986** | −93% | Moonshot AI |
| 2 | minimax-m3 | 25 | 0.00375 | 0.10333 | **0.10333** | −96% | Minimax |
| 3 | mimo-v2.5 | 6 | 0.00029 | 0.00713 | **0.00713** | −96% | Xiaomi |
| 4 | deepseek-v3.2 | 59 | 0.00382 | 0.32731 | **0.66190** | −99% | Baidu, SiliconFlow |
| 5 | qwen3.7-plus | 8 | 0.00000 | 0.05173 | **0.05173** | — | Alibaba |
| 6 | nemotron:free | 10 | 0 | 0 | **0** | — | Nvidia |
| 7 | owl-alpha | 5 | 0 | 0 | **0** | — | Stealth |
| 8 | opus-4.8 (baseline) | 18 | 0.05168 | 1.44554 | **1.44554** | −96% | Anthropic |
| | **TOTAL** | | **0.069** | 2.234 | **2.409** | **−97%** | |

(Account `/credits` total_usage at reconcile time: $119.18 of 123. `/activity`
per-model returned $0 — the daily aggregate for the run date had not posted yet;
the per-run `/generation` reconcile is authoritative and matched on every billed run.)

## Findings

1. **The omp cost bug (fixed, contributed upstream as [adrianco/retort#21]).**
   omp emits usage *per turn*; retort recorded only the *last* turn → −93% to −96%
   under-count. For runs 1, 2, 3, 5, 8 the **summed** omp cost matched `/generation`
   **exactly**, proving summing is correct. Fix: sum cost+tokens across turns.

2. **omp's cost is unreliable for some models even after summing → `/generation` is
   the cost source of record.** Two cases the reconcile exposed:
   - **deepseek-v3.2**: summed-omp ($0.327) is *half* the billed ($0.662) — the run
     was split across **two upstreams** (Baidu + SiliconFlow) and omp's cost math
     didn't track the mix.
   - **qwen3.7-plus**: omp reported **$0** cost *and* 0 tokens (Alibaba's upstream
     returns neither to omp); billed $0.052. Its `token_efficiency=1.00` is an
     artifact of the 0-token fallback path, not a real result.

3. **Value signals.** deepseek-v3.2 is the worst value — slowest (882 s, 59 turns)
   *and* priciest open-weight ($0.66). minimax ($0.10) and kimi ($0.14) are the
   cheap-and-reliable picks. The opus-4.8 baseline is correct but expensive
   ($1.45/run) — the anchor, not a value option.

## Implications for the full grid

- **Roster:** drop `owl-alpha` (stealth + genuine fail, not reproducible) and
  `mimo-v2.5`; retry the **paid** `nvidia/nemotron-3-ultra` once before dropping it.
  Keep the 5 passers.
- **Cost source:** record billed `/generation` cost, not omp's (per finding 2).
- **Budget:** at billed rates ($0.05–0.66 open-weight, $1.45 baseline), a full grid
  (~5 langs × ~5 models × 3 reps ≈ 75 runs) is **tens of dollars**, baseline-dominated
  — set per-model budget-cap keys before launching.
