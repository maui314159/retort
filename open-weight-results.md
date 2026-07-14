# Open-weight coding models via OpenRouter — experiments 15–19

A five-experiment arc testing open-weight models (via OpenRouter, driven by the
`omp` harness) against an `anthropic/claude-opus-4.8` baseline, across the
languages of a working portfolio. The headline is methodological: **easy
benchmarks mislead in both directions, and a "pass rate" on a hard task can
measure packaging hygiene as much as coding ability.**

Roster (all current flagships at time of run): `qwen3.7-plus`,
`kimi-k2.7-code`, `glm-5.1`, `minimax-m3`, `tencent/hy3-preview`,
`deepseek-v3.2`→`deepseek-v4-pro`, baseline `claude-opus-4.8`.

---

## exp-15 — rest-api-crud (the easy task): saturated

95 runs, 7 models × 5 languages (python/go/typescript/rust/java) × 1–3 reps.
Mechanical gate only (build + tests run).

| model | pass | $/run (billed) |
|---|---|---|
| qwen3.7-plus | 15/15 | $0.13 |
| kimi-k2.7-code | 15/15 | $0.28 |
| tencent/hy3-preview | 15/15 | **$0.05** |
| opus-4.8 (baseline) | 5/5 | $1.34 |
| minimax-m3 | 14/15 | $0.17 |
| glm-5.1 | 13/15 | $0.25 |
| deepseek-v3.2 | 12/15 | $0.34 |

**Total billed: $25.07.** Four models tied opus at 100%. The task **saturated** —
when everyone clears the bar, you learn who can do basic CRUD, not who is better.
By language, go/java were universal; rust was hardest for open-weight.

> The cheapest model (tencent, $0.05/run) and qwen ($0.13) matched the opus
> baseline ($1.34) — *on this task*. That conclusion did not survive a harder one.

---

## exp-16 — brazil-bench screening (the hard task): discriminates, but noisy

21 runs, 7 models × {python, typescript, csharp} × **1 rep**. brazil-bench builds
a Brazilian-soccer MCP server from a multi-file guide.

| model | pass |
|---|---|
| qwen3.7-plus | 3/3 |
| opus-4.8 | 3/3 |
| glm-5.1 | 2/3 |
| kimi-k2.7-code | 2/3 |
| tencent/hy3-preview | 1/3 |
| minimax-m3 | 1/3 |
| deepseek-v3.2 | 0/3 |

12/21 overall — the field spread out where CRUD couldn't. Two crossovers stand
out against exp-15:

- **tencent collapsed** (CRUD 100% → 1/3). Its CRUD perfection was a ceiling effect.
- **glm was *under*-rated by CRUD** (2nd-worst there → upper-middle here, beating
  tencent and minimax which both outscored it on CRUD).

But with **1 rep**, the middle is language-luck: each of glm/kimi/tencent/minimax
passed a different single language (minimax's only pass was C#). All three
languages were exactly 4/7 — the new C# scorer behaves like a peer language, not
a broken one.

---

## exp-17 — brazil-bench firm pass (3 reps): the screening was optimistic — and *why*

45 runs, the exp-16 survivors (≥2/3) + `deepseek-v4-pro` (the flagship; v3.2's
0/3 was a stale-variant artifact), × {python, typescript, csharp} × **3 reps**.
Run from an integration build with all the harness fixes; serial rescore to
remove concurrency false-fails.

| model | firm (3 reps) | vs screening | billed | $/run |
|---|---|---|---|---|
| opus-4.8 | **7/9** | 3/3 | **$82.50** | **$9.17** |
| qwen3.7-plus | 3/9 | 3/3 | $3.18 | $0.35 |
| glm-5.1 | 3/9 | 2/3 | $5.84 | $0.65 |
| kimi-k2.7-code | 2/9 | 2/3 | $13.52 | $1.50 |
| deepseek-v4-pro | 1/9 | (v3.2: 0/3) | $21.96 | $2.44 |

**Total billed: $127.00** (omp self-reported $110 — a −13% undercount).

### Dep-fair re-measurement (the honest ranking)

The table above is *as-run* and confounded — exp-17 predates the dependency-handling
fix (PR #33). Re-scoring those same archives with the fix (no model calls, just
re-testing with the imports installed) recovered **10 hidden passes** and changed
the picture substantially:

| model | dep-fair | as-run | Δ |
|---|---|---|---|
| Claude Sonnet 4.6 (native) | **9/9** | (2/9 OpenRouter → 9/9 native) | — |
| opus-4.8 | **8/9** | 7/9 | +1 |
| glm-5.1 | **6/9** | 3/9 | **+3** |
| qwen3.7-plus | 5/9 | 3/9 | +2 |
| deepseek-v4-pro | 4/9 | 1/9 | **+3** |
| kimi-k2.7-code | 3/9 | 2/9 | +1 |

This **overturns the as-run conclusion** that open-weight models collapse on hard
tasks. With deps handled, glm (6/9) and qwen (5/9) sit close to opus (8/9) — the
chasm was *packaging hygiene*, not capability. glm gains the most (it writes working
code but omits `requirements.txt` most often — consistent with being CRUD-underrated
in exp-16). deepseek-v4-pro recovers to mid-pack (4/9) — the v3.2 0/3 was a stale
variant *and* the 1/9 was the confound. kimi is now the weakest kept model (3/9),
the inverse of its top-tier CRUD score. The remaining failures are mostly genuine
(rust/C#/TS build-and-config issues the python-only fix can't touch). (`retort.db.confounded`
preserves the as-run snapshot.)

Spot-checked the remaining failures to be sure they're real, not more artifacts:
opus's one miss (C#) **builds clean but ships a test project with no runnable
tests** (`dotnet test` → "No test is available") — a genuine incomplete deliverable.
Its recorded `code_quality=0` is *not* a scorer error: the collector intentionally
**zeros every metric when `test_coverage=0`** (no tests run ⇒ no evidence the code
works), so a building-but-untested project reads as 0 across the board by design.
So opus's 8/9 holds, and the dep-fair table is the final ranking.

### The catch: most failures are incomplete deliverables, not broken code

Before reading "the open-weight models collapsed," we verified the scoring is
trustworthy (it reproduces exp-16's passes exactly) and then ground-truthed the
failures. The dominant failure mode is **undeclared dependencies**: e.g.
qwen/python/rep1 ships correct source *and* a BDD test suite, but **no
`requirements.txt`**, and imports `mcp`/`pandas`/`pytest_bdd`. Nothing can install
and run it, so it fails the gate identically to garbage. (Same class: missing C#
test projects, build gaps.)

So the firm pass is partly measuring **"did the model ship a runnable
deliverable,"** not **"can the model code.** opus's edge (7/9) is as much
fastidiousness about complete, declared deliverables as raw skill — and it cost
**$82.50, 65% of the entire run**, at $9.17/cell vs the open-weight $0.35–2.44.

---

## exp-18/19 — Claude Sonnet level-set: the provider adapter decided everything

A second Anthropic reference point (`claude-sonnet-4.6`) on brazil-bench. The
headline is a *harness* finding, not a model one: **the same model went from 2/9
to 9/9 depending solely on which provider adapter drove it.**

**exp-18 — via OpenRouter (`openai-completions` adapter): 2/9.** Not capability —
omp aborts Sonnet's request immediately after the first tool call
(`stopReason: aborted`, `"Request was aborted"`, 0 tokens, no retry), so 4–7 of 9
cells produced no code at all. Verified Sonnet-specific (opus runs 25+ turns
through the *same* adapter) and filed as **oh-my-pi #2685**; root-caused to the
`openai-completions` adapter, not Anthropic.

**exp-19 — via native Anthropic (`anthropic-messages`, `ANTHROPIC_API_KEY`): 9/9.**
Routing the identical model through a different code path sidesteps the bug
entirely — every cell iterated the full task (3.2M–15.2M tokens, $1.7–6.5 each;
**$31.02 total**, billed to the Anthropic account) and passed.

So Sonnet is strong here — flawless under the fairest conditions we have. **Two
caveats keep it from a clean head-to-head with the exp-17 table:** (1) it ran on a
*different provider* (native Anthropic — forced, since OpenRouter aborts it), and
(2) its run included the dependency-handling fix (PR #33) that exp-17's runs
predated — so exp-17's numbers are depressed by undeclared-dep false-fails that
Sonnet's run didn't suffer. A fair comparison would dep-fix-rescore exp-17 first;
even then the provider axis differs. The honest one-liner: *Sonnet cleared every
cell it was allowed to run, on both providers — the OpenRouter adapter just refused
to let it run most of them.*

## What actually generalizes

1. **Easy benchmarks mislead both ways.** CRUD *over*-rated tencent (100% → 1/3)
   and *under*-rated glm (near-bottom → upper-middle). A floor test ranks nothing.

2. **Single-rep screening is optimistic.** qwen 3/3 → 3/9 isn't a skill collapse;
   it's that qwen *sometimes* ships a complete package and sometimes doesn't.
   3 reps exposed the inconsistency 1 rep hid — the entire point of replication.

3. **Use the flagship.** deepseek-v3.2 (6 months old) scored 0/3; the flagship
   `deepseek-v4-pro` reached 1/9 — still weakest, but the stale variant had
   *understated* it. Always check you're running the current top model.

4. **Cost is inverted and opus-dominated.** Across all three, the LLM API is
   ~30–60× the cloud-compute equivalent, and on the hard task opus alone is 65%
   of spend. omp's self-reported cost undercounts (−13% aggregate, −68% for
   deepseek's multi-upstream routing, $0 for qwen/tencent/glm) — `/generation`
   reconciliation is the source of truth.

5. **The deepest finding is a measurement confound — and it inverted the headline.**
   brazil-bench's gate conflated coding ability with **dependency-declaration
   hygiene** (the scorer only installed from `requirements.txt`). After fixing it
   (PR #33) and dep-fair re-scoring exp-17, **10 hidden passes** surfaced and the
   "open-weight collapses on hard tasks" conclusion evaporated: glm went 3/9→6/9,
   deepseek-v4-pro 1/9→4/9, qwen 3/9→5/9 — close to opus (8/9), not a chasm. The
   gap was packaging hygiene, not capability. *The confound wasn't a caveat on the
   result; it was most of the result.*

6. **The harness, not the model, is the top failure source.** Across the study,
   what looked like model weakness was repeatedly a harness artifact: undeclared-dep
   false-fails (#33), concurrency false-fails, a stale model variant, the SQLite
   race (#23), the cost undercount (#21), and — most starkly — omp's
   `openai-completions` adapter aborting Sonnet entirely (oh-my-pi #2685), which a
   provider swap (native Anthropic) turned from 2/9 into 9/9.

---

## Harness work this produced

The experiments surfaced (and fixed, as PRs to `adrianco/retort`) a string of
harness issues — most of which had nothing to do with model capability and
everything to do with trusting the numbers:

| PR | fix |
|----|-----|
| #21 | omp multi-turn cost summing + generation-id capture |
| #23 | SQLite shard-concurrency (cold-start race) |
| #25 | C# scorer (dotnet build/test + coverage) |
| #27 | rescore/reevaluate/evaluate broke on `/`-bearing model ids |
| #29 | TypeScript `node:test` runner support |
| #31 | `--design` row-index collision guard (silent 30-run overwrite) |
| #33 | install undeclared deps (the confound above) + `token_limit` budget |

---

## Bottom line

On easy CRUD, several open-weight models match opus at a fraction of the cost. On a
hard, multi-file task, the **dep-fair** ranking is opus 8/9 and Sonnet 9/9 (native)
at the top, with **glm (6/9) and qwen (5/9) genuinely competitive** and
deepseek-v4-pro mid-pack (4/9) — a much tighter field than the as-run numbers
suggested. The headline isn't a leaderboard, though: nearly every "model failure"
this study turned up was a **harness or measurement artifact** — undeclared-dep
false-fails, a stale variant, concurrency, the OpenRouter adapter aborting Sonnet
outright. Get the harness honest first (the seven retort PRs + oh-my-pi #2685), and
the open-weight field is far stronger on hard tasks than a naive run reports. Cost
stays inverted and opus-dominated (~$9/run, 65% of the hard-task spend), so for
cost-sensitive work the competitive open-weight models — glm and qwen especially —
are the value play, and a provider choice (native vs OpenRouter) can matter as much
as the model.
