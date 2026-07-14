# exp-15 addendum — GLM-5.2 and Nemotron-3-Ultra (paid) on the easy grid

Two models added to the exp-15 `rest-api-crud` easy grid (5 langs × 3 reps, omp →
OpenRouter, mechanical gate only). A mid-run **Mac reboot** killed the in-flight
processes; this packages what completed. All per-cell run artifacts (`scores.json`
+ generated source) survived on disk under `runs/`; the only loss was a handful of
un-checkpointed SQLite WAL rows (noted below). On-disk archives + the swarm logs
are authoritative here, not the partial `retort.db`.

---

## GLM-5.2 (`z-ai/glm-5.2`) — **effective 15/15**, ~$0.37/cell

Run as an **8-shard parallel swarm** (40 min wall vs ~2.5 h serial), `$1.20/$4.10`
per Mtok, 1M ctx.

| language | reps pass | test_coverage | code_quality | $/run (omp) |
|---|:--:|---|---|--:|
| python | 3/3 | 0.98–0.99 | 0.62–0.77 | $0.12–0.49 |
| go | 3/3 | 0.69–0.76 | **1.00** | $0.17–0.31 |
| typescript | **3/3** | 1.00 (2 scored); rep2 unmeasured¹ | 0.73 | $0.29–0.63 |
| rust | 3/3 | **1.00** | 0.83 | $0.49–0.73 |
| java | 3/3 | **1.00** | **1.00** | $0.14–0.38 |

**Billed: ~$6.6** (`/generation` reconcile: $6.01 for the 13 surviving rows +
~$0.60 omp-logged for the 2 WAL-lost reps). **~$0.44/cell.** Note: GLM-5.2 routes
across **six upstreams** (Cloudflare, Fireworks, Friendli, Phala, Wafer, Z.AI), so
omp **undercounts ~18%** (omp-logged $4.94 vs billed $6.01 on the 13 rows) — the
multi-upstream cost gap, not the ~1% single-upstream case. `/generation` is the
source of record.

¹ **TS rep2 is a scorer false-fail, not a GLM miss — ground-truthed.** GLM-5.2
scaffolded that rep as a pure **Bun** project (`bun:test`, `bun:sqlite`, `bun test`).
retort's TS coverage scorer (`scoring/scorers/test_coverage.py::_typescript_coverage`)
only detects **jest/vitest/node** and has no Bun branch, so it ran nothing →
`test_coverage=0` → the gate zeroed every metric. Running the archive's tests
directly: **`bun test` → 35 pass / 0 fail**. The code works; the harness couldn't
measure it. (rep1/rep3 passed because GLM used a node/vitest setup the scorer knows.)
So GLM-5.2's true easy-grid score is **15/15**, with one cell understated by a
harness gap. See [harness finding](#harness-finding-ts-scorer-has-no-bun-branch).

**Placement.** At an effective 15/15, GLM-5.2 sits with the easy-grid leaders
(qwen 15/15, kimi 15/15, opus 5/5) at **~$0.44/cell** — and its predecessor glm-5.1
was the dep-fair standout on the *hard* task (brazil-bench 6/9). Strong value-pass
candidate; the real test remains brazil-bench.

---

## Nemotron-3-Ultra 550B (paid, `nvidia/nemotron-3-ultra-550b-a55b`) — **dropped: capable but expensive + unreliable**

The exp-15 pilot's `:free` run GENUINE-failed; the **quick-settle** established the
failure was the free endpoint, not the model — paid nemotron **passes** the floor
task (see `experiment-nemotron-paid/`: python, complete deliverable, 35→tests ran,
**$0.97**). But the easy-grid attempt confirms it is **not a value candidate**:

| cell | result | time | $/run (omp) | note |
|---|---|--:|--:|---|
| settle (python) | ✅ pass | 412s | $0.97 | separate `experiment-nemotron-paid/` |
| grid python rep1 | ✅ pass | 608s | **$1.41** | cov 0.97 (on disk) |
| grid go rep1 | ❌ FAIL | **1810s** | — | hit the 30-min **timeout** |
| grid ts rep1 | ❌ FAIL | 183s | $0.19 | tests didn't run |
| grid rust+ | — | — | — | reboot-killed before running |

**Verdict:** ~**$1.4/cell** (≈ the opus baseline, ~**3× GLM-5.2**) and prone to
30-min timeouts on a *trivial* CRUD task. Token-heavy (2.8M tokens for one python
cell), `token_efficiency=0.00`. Capable but the worst value in the field — **not
carried forward.** The settle run already answered the only open question (the
`:free` failure was infra, not capability).

---

## Harness finding: TS scorer has no Bun branch

A second TypeScript false-fail class, alongside the known node:sqlite teardown crash
(both *understate* TS results):

- **Symptom:** a TS run whose tests pass under `bun test` is scored
  `test_coverage=0` and fails the gate.
- **Cause:** `_typescript_coverage` detects only jest/vitest/node; a `bun:test`
  project matches nothing and no tests are run.
- **Fix:** add a Bun branch — detect `bun.lock`/`"test": "bun test"`, run
  `bun test --coverage`, parse its coverage output. (Bun is arguably the *more*
  idiomatic modern TS choice, so this isn't an edge case.)
- **Impact here:** GLM-5.2 TS understated by 1/3 reps; true grid 15/15 not 14/15.

---

## State of the data (post-reboot)

- **On disk (authoritative):** all 15 GLM-5.2 cells + 3 nemotron grid cells have
  `scores.json` + source under `runs/`. Nothing generated was lost.
- **`experiment-15/retort.db` (partial):** lost 2 un-checkpointed GLM passes
  (go rep1, ts rep1) and nemotron python rep1 to the reboot's dropped WAL. To make
  the DB canonical without perturbing the kept-field numbers, rebuild from archives
  before `retort aggregate`. **Not yet done** — flagged so master.csv isn't rebuilt
  off the partial DB.
