# experiment-15 — Open-weight models via OpenRouter (pilot scope)

Open-weight coding models, run through the open-source **omp** harness against
**OpenRouter**, on the languages of our portfolio. This doc scopes the **pilot**
that de-risks the full grid. Design principle: **inspect omp's raw JSON *first*,
then commit to a cost-attribution architecture** — don't build attribution on an
assumption about what omp emits.

## Build status (2026-06-13)
- ✅ **Installs** — omp 15.12.3, go 1.26.4, maven 3.9.16; full supported-5 toolchain ready.
- ✅ **omp OpenRouter provider** — `~/.omp/agent/models.yml`, 8 models, key via env (1Password).
- ✅ **Step 0 probe** — path live; attribution = generation-id reconcile.
- ✅ **retort code** — `_parse_omp_usage` captures `responseId`s + `upstreamProvider` and **sums
  cost+tokens across turns** (fixes the bug below); `_store_run_result` persists the generation
  ids to `_cost_usd.metadata_json`. Tests updated; full runner suite green.
- ✅ **Validator** — `validate_openrouter_spend.py`: per-run `/generation` reconcile + `/credits`
  + `/activity` (mgmt key). Clean, proven on real data.
- 🐞 **BUG FOUND + FIXED — omp cost was per-turn, recorded as last-turn only.** retort's
  `_cost_usd` under-counted multi-turn runs **~14–25×** (−93 to −96%). The validator's
  `/generation` sum **matched the summed cost exactly** on every run, so the fix (sum, not last)
  is verified against OpenRouter billing. Pilot-so-far: omp reported $0.014 vs **$0.250 billed**.
  Also affected the live `retort monitor` display and the `_tokens`/`token_efficiency` metric.
- 🔄 **Step 1 run** — in progress: kimi ✓, minimax ✓, mimo-v2.5 ✗ (tests didn't run), deepseek…
  Then: reconcile all 8 → full grid. (The running pilot predates the summing fix, but its cost is
  fully recoverable via the validator; the fix lands for the full grid.)

## Pilot results (2026-06-13) — 5/8 pass, billed reconciled

> Full results (quality scores + per-run cost reconciliation + findings): **[`results.md`](results.md)**.

| Model | Cap | Cov | Turns | Speed | **Billed** | omp said |
|---|:--:|--:|--:|--:|--:|--:|
| kimi-k2.7-code | ✅ | 0.99 | 14 | 202s | $0.140 | $0.010 |
| minimax-m3 | ✅ | 0.98 | 25 | 247s | $0.103 | $0.004 |
| mimo-v2.5 | ❌ genuine | — | 6 | 81s | $0.007 | — |
| deepseek-v3.2 | ✅ | 0.93 | **59** | **882s** | **$0.662** | $0.004 |
| qwen3.7-plus | ✅ | 0.91 | 8 | 191s | $0.052 | **$0.000** |
| nemotron-3-ultra:free | ❌ genuine | — | 10 | 275s | $0 | — |
| owl-alpha (stealth) | ❌ genuine | — | 5 | 110s | $0 | — |
| **opus-4.8 (baseline)** | ✅ | 0.99 | 18 | 114s | **$1.446** | $0.052 |
| **TOTAL** | | | | | **$2.41** | $0.069 |

- **Capability:** 5/8 pass. The 3 failures (mimo, nemotron:free, owl-alpha) are all
  **GENUINE** per `retort diagnose` (0 TOOLING) — tests don't run on the produced code.
- **Cost:** omp under-reported the pilot **97%** ($0.069 vs **$2.41 billed**). Two omp
  cost-reliability issues *beyond* the summing bug: **deepseek** summed-omp ($0.33) is half
  billed ($0.66) — split across Baidu+SiliconFlow upstreams; **qwen** omp reported **$0**
  (Alibaba upstream returns no cost to omp). ⇒ **`/generation` billed is the cost source of
  record**, not omp, even after the summing fix.
- **Value signals:** deepseek-v3.2 = slowest *and* priciest open-weight (poor value);
  minimax ($0.10) and kimi ($0.14) cheap + reliable; opus baseline $1.45/run.
- `/activity` shows $0 (today's daily aggregate not yet posted); `/generation` per-run is
  authoritative and matched on every billed run.

## Two objectives

1. **Does the harness path work end-to-end?** For each of the 8 models: omp →
   OpenRouter auth works, the model actually *drives the tool loop* to a
   built-and-tested project (the exp-12 bar: tool-call format **and** agentic
   capability — advertised `tools` support is necessary, not sufficient), and
   retort records scores + cost.
2. **How do we attribute spend to a single run?** Decided by what omp's JSON
   actually contains (Step 0), not guessed.

## Models (8) — all live on OpenRouter, all advertise `tools`

| Model | In/Out $·Mtok | Note |
|---|---|---|
| `moonshotai/kimi-k2.7-code` | 0.95 / 4.00 | code-specialized; priciest open-weight |
| `minimax/minimax-m3` | 0.30 / 1.20 | |
| `xiaomi/mimo-v2.5` | 0.14 / 0.28 | cheapest paid |
| `deepseek/deepseek-v3.2` | 0.23 / 0.34 | 131k ctx (others ~1M) |
| `qwen/qwen3.7-plus` | 0.32 / 1.28 | ⚠ hosted "Plus" tier — **not** strictly open-weight |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | 0 / 0 | ⚠ `:free` — rate-limited, queued, prompts logged |
| `openrouter/owl-alpha` | 0 / 0 | ⚠ **stealth/cloaked** — undisclosed identity, ephemeral, logged |
| `anthropic/claude-opus-4.8` | 5.00 / 25.00 | **baseline** (proprietary; run via omp like the rest, *not* claude-code) |

The two $0 models are **infra risk, not free wins** (throttling/queueing surfaces
as failures that look like the model's fault); `owl-alpha` can also vanish
mid-grid. Treat both as exploratory, not stable benchmark subjects.

## Install (precise — from the host probe)

**Done (host fully toolchain-ready for the supported-5 grid):** omp 15.12.3,
go 1.26.4, maven 3.9.16 (pulled OpenJDK 26) all installed via brew; python+pytest+
coverage+ruff, node 22+npm, cargo 1.95+clippy, JDK 25, dotnet 10 already present.

**Still required — the only pilot blocker:** the OpenRouter API key in the
environment. Stored in 1Password as **"OpenRouter - Initial Retort Key"**
(`op://Private/OpenRouter - Initial Retort Key/credential`, a 73-char `sk-or-…`).

**Keys (1Password, vault Private):**
- inference — `op://Private/OpenRouter - Initial Retort Key/credential` (model calls, `/generation`, `/credits`)
- management — `op://Private/OpenRouter Management Key - Retort Experiments/credential`
  (`/activity` per-model breakdown — 403s on the inference key — and `/api/v1/keys` provisioning)

**Reconcile sources (all confirmed live):** `/generation?id=` (per-run, inference key,
authoritative billed cost) · `/credits` (aggregate `total_usage`, inference key) ·
`/activity` (per-model/day `usage`, **management key**).

**Auth model (resolved):** omp's `~/.omp/agent/models.yml` provider uses
`apiKey: OPENROUTER_API_KEY` (env-var form). A launcher resolves it **once per grid**
through 1Password, and retort copies `os.environ` into every omp subprocess, so all
cells inherit it — **one authorization for the whole run, never per-run or
per-iteration**, no mid-grid 1Password prompts:

```bash
export OPENROUTER_API_KEY="$(op read 'op://Private/OpenRouter - Initial Retort Key/credential')"
retort run … --config experiment-15/workspace.yaml
```

(`op` desktop integration is unlocked, so that single read is silent. One-off
interactive runs can instead set `apiKey: '!op read "op://…/credential"'`, which
invokes `op` once per omp process.)

Watch generated-Java + Maven plugin compatibility on the new JDK at the first Java run.

**Deferred — C#:** dotnet 10 is installed, but the scorers have no C# branch
(`dotnet build` / `dotnet test`+coverlet / `dotnet format`). That's a code build,
not an install — scheduled for the "more later" bucket alongside extra harnesses.

## Sequence

### Step 0 — the decision gate (one tiny omp call, ~$0)
Wire an OpenRouter `openai-completions` provider into `~/.omp/agent/models.yml`
(base `https://openrouter.ai/api/v1`, key = `OPENROUTER_API_KEY`), then:

```bash
omp -p --no-session --mode json --model openrouter/deepseek/deepseek-v3.2 "reply ok" | tee /tmp/omp_probe.jsonl
```

Inspect the captured JSON for:
- **(a) OpenRouter generation `id`** in any event — *this single fact picks the
  attribution architecture.*
- **(b) `usage.cost`** populated — does omp surface OpenRouter's now-automatic
  cost passthrough? If yes, **no hand-entered rate table needed** (a simplification
  over the Gemini-pricing approach).
- **(c)** auth/provider wiring is correct (a clean `message_end` with usage).
- **(d)** how omp takes the key — per-provider / env-expandable? — which decides
  whether per-run/per-model **keys** can be injected by retort's per-cell env
  (config) or need a wrapper (code).

### Step 0 outcome — RESOLVED (probe: deepseek-v3.2, 2026-06-13)
omp→OpenRouter path is **live** (auth via `op`, `openrouter/<id>` resolves, 33-event
clean run). Both gate questions answered:
- **(a) generation id IS present** as `message.responseId` (`gen-…`, OpenRouter's
  native format) → **attribution = generation-id reconcile.** Per-run keys NOT
  needed. (Keys stay available only as optional per-model budget caps.)
- **(b) omp surfaces a per-call cost** (`usage.cost.total`) → no rate table needed.
  **But it's ~8% low vs the billed `/generation total_cost`** (cache-read accounting
  differs). So: omp cost = live view; **`/generation` = dataset of record.**
- `/generation?id=…` lookup **verified live** — returns authoritative cost + native
  tokens + `provider_name`. The reconcile path is proven end-to-end.

Two design consequences:
- **A run has many turns → many `responseId`s.** `_parse_omp_usage` currently keeps
  only the *last* message_end usage; for a true per-run total we must capture **all**
  responseIds and **sum** their `/generation` costs (this also reveals/fixes any
  multi-turn under-counting in omp's aggregate).
- **`upstreamProvider` varies** (this call routed to *Baidu*; resolved model was
  `deepseek-v3.2-20251201`). For reproducibility, **pin OpenRouter provider routing**
  and record the resolved upstream + dated model per run.

Parallel sharding note (unchanged): a shared key can't be time-sliced, but with
generation-id reconcile that's moot — each call self-identifies by `responseId`.

> Per-model keys are **not** the attribution mechanism — they only resolve to the
> model. Keep them solely as cheap per-model **budget caps** + a coarse aggregate
> cross-check.

### Step 1 — capability pilot (8 runs, ~$1–2)
`language=[python] × model=[the 8] × tooling=none × rep=1` on **rest-api-crud**
(the easy task — open-weight models have a real shot at 1.00, and it's cheap).
Confirms each model drives the loop to a scored project; flag/drop models that
flake (free-tier + stealth are the likely casualties). retort records
code_quality / test_coverage / cost per cell.

### Step 2 — build attribution + validator
Implement the branch chosen in Step 0, then write `validate_openrouter_spend.py`
(sibling to `aggregate_findings.py`): reconcile the experiment DB's recorded cost
against OpenRouter via **three independent sources** — `/credits` delta (aggregate),
`/activity` (per-model/day), and the chosen per-run mechanism. Flag any cell off by
more than a threshold. Run it on the 8 pilot runs.

### Step 3 — scale to the full grid
After `brew install go maven`: `language=[python, go, typescript, rust, java] ×
model=[surviving 8] × tooling=none × rep=3` on rest-api-crud
(= up to 120 runs). Add the hard task (`brazil-bench`) and/or C# only after the
easy grid + attribution are proven. The Opus-4.8 baseline anchors every cell.

## Success / decision criteria
The pilot **passes** when, on the 8 runs:
- the attribution mechanism is **determined** (Step 0(a) answered), **and**
- a workable majority of models produce a **scored** run (we expect the paid
  open-weight 5 + baseline to clear it; the 2 free/stealth are bonus), **and**
- aggregate recorded cost **reconciles** with the `/credits` delta within ~a few %.

## Open items to confirm at pilot
- omp surfaces the OpenRouter generation `id`? → attribution branch.
- omp surfaces OpenRouter's automatic `cost`? → drop the rate table.
- omp key injection: per-provider/env (config) vs wrapper (code)?
- free-tier / stealth reliability under repeated calls.
- generated-Java + Maven on JDK 25 plugin compatibility.

## Cost frame
Pilot ≈ **$1–2** (8 easy-task runs; 5 cheap paid + 2 free + 1 baseline ~$0.5–1).
Full easy grid (≤120 runs) ≈ **$30–80** depending on survivors (most open-weight
< Claude rates). Hard task ≈ ~10× per-run if added later.
