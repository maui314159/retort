# SandboxRunner: ephemeral per-cell execution on AWS Batch/Fargate

**One experiment cell = one ephemeral container.** `SandboxRunner` implements the existing
`PlaypenRunner` protocol against AWS Batch on Fargate. This document names each component, says
exactly what is implemented versus advisory versus planned, records the lane's contract and known
defects, and lays out the plan for making it a first-class runner. Where a claim is inferred rather
than observed it is marked **[HYPOTHESIS]**; direct observations are **[DIRECT]**. Everything below
was verified against the code, the ECR/Batch state and the run archives on 2026-09-04.

Fork-only for now (`maui314159/retort`, branch `feat/cloud-lane`, worktree `../retort-cloudlane`).
Upstream's README lists *"a CloudRunner (the `cloud` runner name in the schema falls through to
Docker)"* under **Not yet** — this is that runner, under the name `sandbox` (see §8).

| # | Component | Lives in | Status |
|---|---|---|---|
| 1 | **The `sandbox` playpen runner** | `src/retort/playpen/sandbox_runner.py` | Implemented; selected by `playpen.runner: sandbox` + a `playpen.sandbox` block; `check_design()` preflight refuses factor levels the lane cannot honour (Phase 0, 2026-09-04) |
| 2 | **Per-language images** | `sandbox/Dockerfile.*` → ECR `retort-sandbox` | Implemented for python, go, typescript (opencode + prime-agent); **rebuild provenance incomplete** (§4) |
| 3 | **In-container entrypoint + watchdog** | `sandbox/entrypoint.sh` (inline Python) | Implemented; a **second implementation** of the local progress guard (§5.3) |
| 4 | **In-container scoring** | `sandbox/score_full.py`, `score_gate.py` → `_container_scores.json` | **Advisory only.** The authoritative `scores.json` is computed on the HOST (§3.4) |
| 5 | **Image identity in provenance** | `sandbox_image_digest[_effective]`, `sandbox_job_definition`, `_sandbox_meta.json` witnesses | **Verified per job** against Batch's container image since Phase 0 (2026-09-04); mismatch or unverifiable pin fails the cell as HARNESS (§5.1) |
| 6 | **Parallelism** | `retort run --shard i/N` processes sharing one `retort.db` | Implemented; design point **16 concurrent cells** (§6) |
| 7 | **Bootstrap** | `scripts/sandbox_bootstrap_aws.sh` | Implemented; registers job-defs **by digest** (Phase 0); still hard-codes the account id (Phase 4) |
| 9 | **Transcript readers** | `src/retort/playpen/agent_log.py` | Bounded, `.gz`-aware, streaming (Phase 0); prime transcripts compacted at write time, 193 MB → 21 MB measured (§5.5) |
| 10 | **`docker` backend** (local lane) | `SandboxRunner(backend="docker")`, `playpen.sandbox.backend: docker` + `docker_images` | Implemented 2026-09-04 (Phase 1.2b): same image + entrypoint under `docker run`, bind-mounted workspace, no AWS; stamps `runner_lane=docker-local` (never pooled). Replaces `DockerRunner`, which is deleted once this lane has run a real cell |
| 8 | **Parity harness** | `sandbox/parity_check.py` | Implemented; caught three would-be false-zero bugs before the first grid |

---

## 1. What this is, and why it exists

API-model experiments (opencode or prime-agent × OpenRouter) are API-bound, yet retort's
one-experiment-at-a-time rule serialises them: wall-clock is a first-class response and a shared
machine corrupts it. Moving a cell into its own environment dissolves that contention, and with it a
recurring family of environment bugs (playpen-path refusals, global-config leakage, orphan processes).
The pre-registered methodology is [future-experiments.md §0c](future-experiments.md).

**Scope is deliberately narrow: API-model experiments only.** The local oMLX spine cannot move.

Design choices worth preserving: it shells out to the `aws` CLI rather than taking a boto3
dependency (one seam, `_aws`, monkeypatched in tests); the agent's wall-clock is measured
**in-container** on a monotonic clock, so queue and provisioning time are recorded separately and
never folded into `duration`; secrets reach the container through the job definition's Secrets
Manager wiring and never touch the runner, S3 or provenance.

**Standing rule, load-bearing:** never pool `duration` / `build_time` across runner lanes. Lane is
a provenance field (`runner_lane`). Pass rates are comparable; timings are not.

### Validation evidence (all [DIRECT])

- All four pre-registered §0c smokes passed: S3 artifact round-trip; agent reaches OpenRouter from
  inside the container with a secret-hygiene grep; in-container timing separated from job span;
  **scorer parity** — an archived local workspace rescored in-container matches its local scores.
- A real `retort run --config` drive on Fargate with zero host-side fixes; 2/2 cells judged
  `requirement_coverage` 1.0.
- In-container stall watchdog live-verified: 60 s window, kill at 60.1 s, `kill_reason=stall`.
- Shard/resume semantics proven over Batch with zero duplicate submissions.
- Shakedown agreed with the local lane 3/3.
- First production family, `exp-mu-primeagent` (24 runs, 3 languages, 2 tasks) — see
  [past-experiments](past-experiments.md). Archive spot-check: python rep1 `_sandbox_meta.json`
  records 12/12 tests, 95.83 % coverage, digest `f59c3b0b…`.
- Whole unit suite green (`env -u VIRTUAL_ENV pytest tests/unit`; the one skip is graphify not
  installed). Running from an *activated* venv shell fails `test_non_python_workspace_gets_no_venv`
  because `VIRTUAL_ENV` leaks into `_build_env`'s `os.environ.copy()` — a shell artifact, not a defect.

---

## 2. Prior art: there was never a cloud runner upstream

Checked across upstream's full history, not just its current tree.

- Files ever added under `src/retort/playpen/`: `local_runner.py`, `docker_runner.py`,
  `metaharness_runner.py`, `graphify_hook.py`, `repo_pr.py`, `runner.py`, `stack_reload.py`,
  `swiftlet_shim.py`, `task_loader.py`, `toolchains.py`, `prompt_builder.py`. Nothing cloud, batch,
  Fargate, Modal, E2B or remote.
- **But the slot exists.** `RunnerType.cloud` has been in `config/schema.py` since upstream's
  original config layer (`5170b787`, 2026-04-10); `runner.py`'s docstring names "CloudRunner
  (optional)"; and upstream's README lists a CloudRunner under *Not yet*, noting that `cloud` falls
  through to Docker. [DIRECT]
- **Naming trap:** `cloud/` directories in upstream experiment data (e.g.
  `experiments/adrianco/experiment-49-versions/cloud/`) mean *the model was a hosted API model*,
  with execution still local. Different axis from execution locus — which is why this runner is
  named `sandbox`, not `cloud`.

### `DockerRunner` is not prior art, and is a live footgun

`docker_runner.py` (211 lines, untouched since Phase 1). When `docker` is not on PATH, `execute()`
falls through to `_simulate_run()`, which sleeps 10 ms and returns **random** metrics
(`exit_code=0 if random.random() > 0.1 else 1`, `token_count=random.randint(500, 5000)`).
`RunnerType.docker` is the **schema default**, and `cli.py`'s `else` branch used to construct a
`DockerRunner` for it *and for `cloud` and any other unmatched value* — yet all 81 of upstream's
`workspace.yaml` files set `runner: local`. `SandboxRunner` does not import, subclass or reuse it.
**On this fork since Phase 0 (2026-09-04), `retort run` fails closed:** `docker` without a docker
binary, `cloud`, and unknown names all raise before any cell runs; `_simulate_run` is unreachable
from the pipeline.

> ***upstream:*** worth a small issue on its own — the default runner path, and the documented
> `cloud` name, silently yield simulated results. They should fail closed.

**Decision (2026-09-04): do not repair `DockerRunner`; replace it.** Even with docker installed it
produces no data — stock images with no agent CLI, no auth, no usage parser, no in-container
scoring, so every cell exits non-zero and scores zero. Phase 1.2b gives `SandboxRunner` a local
`docker` backend that runs the sandbox images themselves, then deletes `docker_runner.py`. Upstream
gets two one-line asks independent of any AWS code: make `local` the schema default, and delete
`_simulate_run` (§8).

---

## 3. Components and the contract

### 3.1 Flow per cell

```
provision()  build the workspace locally (TASK.md, support files, stack.json, opencode.json)
             — LocalRunner's seeding minus host-only steps (venv, graphify)
execute()    tar → S3 → `aws batch submit-job` → poll DescribeJobs → pull out.tar.gz → unpack
             → read _sandbox_meta.json + _agent_stdout.log → parse usage with local_runner's parsers
teardown()   remove the local workspace, best-effort delete the S3 prefix
```

The Batch attempt timeout is derived per submission from `playpen.timeout_minutes` (+ 600 s
margin), never from the job definition's baked-in value.

### 3.2 Runner → container (environment on the job)

| variable | meaning |
|---|---|
| `RETORT_S3_IN` / `RETORT_S3_OUT` | input workspace tarball / where to upload artifacts |
| `RETORT_AGENT_CMD` | JSON array: the headless agent command (opencode or prime-agent) |
| `RETORT_ENV_ID`, `RETORT_LANGUAGE`, `RETORT_MODEL` | cell id, language factor, served model id |
| `RETORT_IMAGE_DIGEST` | the **configured** digest, copied from workspace.yaml (see §5.1) |
| `RETORT_AGENT_TIMEOUT_SECONDS`, `RETORT_STALL_SECONDS` | hard wall and stall guard (0 = off) |
| `RETORT_SCORE_IN_CONTAINER`, `RETORT_RESPONSES` | run scorers in-container; metric list |
| `OPENROUTER_API_KEY` | injected by the job definition from Secrets Manager; written to opencode's `auth.json`, never logged |

### 3.3 Container → runner (`_sandbox_meta.json`, then `RunArtifacts.metadata`)

`_sandbox_meta.json`: `agent_exit`, `agent_seconds` (THE duration), `image_digest`, `env_id`,
`language`, `model`, `scored`, and when the python gate ran `tests_passed`, `tests_total`,
`coverage_pct`; `kill_reason` (`stall` | `timeout`) when the watchdog fired.

Metadata keys on every sandbox run: `runner_lane=sandbox`, `sandbox_job_id`,
`sandbox_image_digest`, `sandbox_vcpu`, `sandbox_memory_mb`, `sandbox_queue_seconds`, plus
`sandbox_tests_passed` / `sandbox_tests_total` / `sandbox_coverage_pct` and
`sandbox_container_scores=_container_scores.json` when present, plus the usage keys from the shared
parsers. Watchdog kills surface as exit 124 + `kill_reason`, like the local guard.

### 3.4 Where scoring happens — advisory in-container, authoritative host

[DIRECT] After `execute()` returns, the run loop (`cli.py:1101`) calls the host `ScoreCollector`
on the pulled workspace for **every** lane, and that result is `scores.json`. The container's
`_container_scores.json` is written by `score_full.py` and **consumed by nothing** in `src/`; its
own docstring says promoting it is "a host-side pipeline decision deliberately NOT made here".

Consequences: a sandbox run's `build_time` is a **host** measurement of a workspace built elsewhere;
the host still needs every language toolchain (a `csharp` image does not remove the need for
`dotnet` on the M4); and scoring re-introduces the host contention the lane exists to remove — one
`go test` / `pytest` / `npm test` per returning cell, on the shared machine. Making the in-container
scores authoritative is Phase 2 of the plan (§7).

### 3.5 Experiment-level provenance

[DIRECT] `provenance.json` for a sandbox experiment has keys `agent_config, agents, harness, host,
models, retort, serving, stack_presets, tools` — no image digests, job-definition revisions, vCPU
or memory, and `host` describes the M4, not the lane. The lane's tuning parameters exist only in
per-run metadata today.

---

## 4. Image lineage and rebuild provenance

**`v2` / `v3` are ECR image *tag generations*, not versions of a Dockerfile.** The `retort-sandbox`
repository is IMMUTABLE, so every rebuild pushes a new tag and registers a new job-definition
revision. The **digest** is the tuning parameter, passed as `playpen.sandbox.image_digests`.

ECR, sorted by push time [DIRECT]:

| pushed (UTC) | tag | digest | size |
|---|---|---|---:|
| 08-31 16:45 | python | 52dd5303 | 707 MB |
| 08-31 21:15 | python-v2 | f1b82a01 | 707 MB |
| 09-01 14:26 | python-v3 | 4d04fe10 | 723 MB |
| 09-01 15:17 | go-v1 / typescript-v1 | 48743d87 / e23e1a92 | 916 / 551 MB |
| 09-01 15:22 | go-v2 / typescript-v2 | e54e89a5 / 3bc005ce | 916 / 551 MB |
| 09-02 10:55 | python-v4c | f59c3b0b | 951 MB |
| 09-02 16:55 | go-v3 | 2e458f4b | 1145 MB |
| 09-02 16:57 | typescript-v3 | e002fd8e | 717 MB |
| 09-02 17:04 | go-v3b | 27dddbf6 | 1145 MB |

`exp-mu-primeagent` ran on **python-v4c, go-v3b, typescript-v3**. Batch job definitions also carry
`python-v4`, `python-v4b` (revisions 6, 7) and `go-v3` (rev 3) — generations that exist in AWS but
correspond to no committed recipe.

### The defect: image identity depends on inputs nobody records

The Dockerfiles build retort itself from the worktree (`COPY src ./src; pip wheel …`), and the
prime layer copies a **staged, uncommitted** dist bundle (`sandbox/prime-pkg/`). So image identity
= (Dockerfile, source commit, staged bundle). go-v2 and typescript-v2 were pushed five minutes after
v1 at byte-identical sizes — the same Dockerfile rebuilt against a later worktree carrying the
undecodable-file scorer fix (`12ed60ee`). Nothing needed to change in the recipe for a new
generation to exist, and the commit it was built from is recorded nowhere. Provenance captures
*which* image ran, not *how to rebuild it*.

### Unifying with `DockerRunner`'s images — no

It names *mutable* stock tags (`python:3.12-slim`, `node:20-slim`, …): an unrecorded tuning
parameter that moves under you. Our images share the `python:3.12-slim` base but pin everything
above it by digest. Architecture is the other obstacle: sandbox images are `linux/amd64` for
Fargate; the dev host is arm64. One shared image means emulation (corrupts wall-clock) or a
multi-arch manifest (real work, and durations never pool across lanes anyway). Deferred.

---

## 5. Known defects, in priority order

Ordered by how directly each violates *"verify tuning parameters — the effective value, not the
configured one"*.

### 5.1 The recorded image digest is the configured one, never the effective one — FIXED 2026-09-04

**Fix (Phase 0.1):** `execute()` reads `container.image` and the job-definition revision from
`describe-jobs`, resolves a tag to its digest via `ecr describe-images`, records
`sandbox_image_digest_effective` + `sandbox_job_definition`, and fails the cell as HARNESS when a
pinned digest differs or cannot be verified. Unpinned stays allowed and now records what ran. The
bootstrap registers job definitions by digest. `entrypoint.sh` writes the ECS agent's `ImageID`, CPU
model and AZ into `_sandbox_meta.json` as independent witnesses (§5.4). The original finding follows.

[DIRECT] Job definitions reference images **by tag** (`…/retort-sandbox:python-v4c`); the runner
submits `--job-definition retort-sandbox-<lang>` with **no revision** (= latest ACTIVE); and both
`sandbox_image_digest` and `_sandbox_meta.json`'s `image_digest` are copied from workspace.yaml.
Nothing reads what actually ran. Register revision 9 with a new image and forget the yaml, and every
run records v4c while v5 executes — the Hermes-context-length failure, verbatim. Today the only
thing making tag≈digest true is the ECR repository's IMMUTABLE setting, an out-of-band invariant no
test checks.

### 5.2 Design factors silently ignored on the sandbox lane — REFUSED since 2026-09-04

**Mitigation (Phase 0.2):** `SandboxRunner.check_design()` lists every level the lane cannot honour
(`prompt`, `tooling`, `stack`, `effort`, `thinking`, unsupported agents) and `retort run` refuses the
grid with the list before any cell runs. Honouring `prompt`/`effort` is Phase 1.1. The finding:

[DIRECT] `SandboxRunner._build_agent_command` calls `_build_agent_prompt(stack)` with **no
`prompt_injection`**, and cli.py passes no `prompts_dir`; `LocalRunner` loads `prompts/<level>.md`
for `prompt != none` in every harness branch. A sandbox design with `prompt: [none, bdd, tdd]` runs
the plain prompt three times and records three levels. Likewise the `tooling=graphify` pre-run hook
never runs while the prompt still tells the agent to consult `graphify-out/`; `stack` presets and
`LCM_CONTEXT_THRESHOLD` are not exported. No current experiment varies these — which is exactly why
it is dangerous.

### 5.3 Duplicated harness logic

[DIRECT] `SandboxRunner` re-implements `_resolve_harness`, `_model_for`, `_model_options_for`,
`_write_opencode_config`, and the opencode + prime branches of `_build_agent_command` (copies of the
`LocalRunner` branches with `/workspace` substituted). The container's watchdog is a second
implementation of `_run_with_progress_guard` (`local_runner.py:161-293`, tested) as inline Python
in `entrypoint.sh`, with a **different kill vocabulary** (`timeout` vs the local guard's
`hard_wall`). `score_full.py`, `score_gate.py` and the watchdog live outside the package, copied to
`/` in the image, even though the image installs retort. The precedent for sharing is already in
the tree (`metaharness_runner.py` imports from `local_runner`; so does `sandbox_runner.py`) — it
just stopped short.

### 5.4 Fargate hardware is heterogeneous and unrecorded

[DIRECT] `_sandbox_meta.json` records no CPU model or availability zone. [HYPOTHESIS] Fargate
places tasks on mixed instance generations, so within-lane `build_time` carries an unrecorded
hardware factor; agent `duration` is dominated by API latency and less exposed. Fargate stays the
right choice (zero idle cost, per-task-second billing, already validated) **until measured**: record
the hardware, group `build_time` by CPU model after the next grid, and if the spread is material
switch the Batch compute environment to EC2 with a single pinned instance type — same queue, same
job definitions, same runner; spin-up lands in `sandbox_queue_seconds`. Spot is out (interruptions
corrupt timing). Fargate task cost is also not recorded beside token cost.

### 5.5 Unbounded log reads — FIXED 2026-09-04

**Fix (Phase 0.4):** `retort.playpen.agent_log` — `find_agent_log` (`.log` or `.log.gz`),
`read_tail`, `search`, `contains_any`, all streaming or bounded — now backs `agent_consulted`, the
diagnose refusal scan, the live-context tail and `SandboxRunner`; sandbox `RunArtifacts.stdout` is
bounded like the local lane's. `compact_prime_log` drops `message_update` events in place: on the
real 193 MB log, **193.3 → 21.0 MB in 0.6 s with `_parse_prime_usage` output identical**. Applied
post-run locally, in-container by `entrypoint.sh`, and on extraction by the runner. `gunzip -k` is no
longer needed after a data-branch clone. The finding:

[DIRECT] `agent_consulted()` (`local_runner.py:1323`) and the diagnose helper (`cli.py:279`)
`read_text()` the whole `_agent_stdout.log`; `sandbox_runner.py::_read_text` loads it into
`RunArtifacts.stdout` on the hot path of every cell; only the live-context reader (`cli.py:173`) is
bounded. One prime brazil log is **193 MB**.

**Log volume at source.** prime-agent's `--mode json` emits the full event stream. Breakdown of
that 193 MB file (41,451 events) [DIRECT]:

| event | count | MB |
|---|---:|---:|
| `message_update` | 31,515 | **172.3** |
| `tool_execution_update` | 9,207 | 17.6 |
| everything else | 729 | 3.4 |

Each `message_update` is a full snapshot of the accumulating message. The 91 **assistant
`message_end` events carry `usage` (incl. `cost.total`), `stopReason`, `model`, `responseId` and the
final `content`** (the other 91 `message_end` are `toolResult` messages); `_parse_prime_usage` reads
exactly those. So **dropping every `message_update` at write time is safe** for tokens, cost, turns,
stop reasons and generation ids — 193 MB → ~21 MB. Keep `tool_execution_update` and the rest: they
are the evidence that identified the `exp-mu-primeagent` zero-write failure. **Do not truncate.**

**Interim archive convention (data branch, commit `85b3b2ed`):** stdout logs over 1 MB are stored
as `_agent_stdout.log.gz` (708 MB → 8.8 MB, byte-identical). The working tree keeps them
uncompressed because the readers open the file by exact name with no `.gz` branch; `gunzip -k`
after a fresh clone before rescoring.

### 5.6 Smaller

- Two mechanisms *appear* to select a runner, but `cli.py` constructs **all four** runners directly
  (`local`, `sandbox`, `metaharness`, `docker`); the `RunnerRegistry` backs only `retort plugin
  list/show`. The cli branch is the house pattern; the gap is that `plugin list` cannot name `sandbox`.
- Hard-coded AWS account id in `sandbox/Dockerfile.*-v3/-v4` `FROM` lines and the bootstrap script.
- Remaining before broader use: claude-code on the lane (API-key billing decision), live-triggered
  second chance on Fargate, a `csharp` image.

---

## 6. Design point: 16 simultaneous cells (decided 2026-09-04)

The compute environment caps at 32 vCPUs (`sandbox_bootstrap_aws.sh:132`); at 2 vCPU per cell that
is **16 concurrent cells**, fixed as the design point rather than O(100). Aggregation stays
host-side and per-process: each cell's artifacts come back through the `retort run` that submitted
it, which scores, judges, archives and commits one `RunResult` row to the experiment's SQLite (WAL,
30 s busy timeout). Fan-out is `--shard i/N` processes sharing one `retort.db`; ownership is a
deterministic hash of (cell, replicate), so shards never coordinate through the DB.

| concern | at 16 | needed |
|---|---|---|
| Batch capacity | exactly the 32-vCPU cap | nothing; raise `maxvCpus` only with a new design point |
| polling | 16 `aws batch describe-jobs` subprocesses per 15 s ≈ 1/s | nothing |
| SQLite writers | 16 rows landing over minutes | nothing; WAL + busy_timeout cover it |
| host memory | 16 × full stdout strings (193 MB each, worst case) | done — Phase 0.4 bounded reads + compaction |
| host-side scoring | 16 concurrent `go test`/`pytest`/`npm test` on the M4 | **Phase 2** — the only real blocker |
| judge | up to 16 concurrent `claude -p` judge calls | pace or accept retries; watch on the first 16-wide grid |

The pre-registered §0c design said "a design grid IS an array job". That was not built, and at 16 it
is not needed: an async `submit`/`collect` protocol extension is shelved unless the design point
changes. Wall-clock parallelism is honest here only because `duration` is measured in-container.

---

## 7. The plan

Goal: **make the Fargate lane a first-class retort runner that follows the codebase's patterns** —
one source of truth for harness logic, fail-closed on unverified parameters, scores honest to the
environment that built them — trustworthy for our experiments first, offerable upstream second.
Work happens in `../retort-cloudlane` (`feat/cloud-lane`); the main checkout is left alone while
experiments run. Each phase ends with unit tests plus **one paid one-cell smoke on Fargate**, queued
behind any live run per the one-experiment rule.

### Phase 0 — fail closed — DONE 2026-09-04 (`feat/cloud-lane`, four commits; unit suite green)

Smoke still owed: one paid one-cell Fargate run to see `sandbox_image_digest_effective`,
`sandbox_job_definition` and the container witnesses land in a real archive, and to confirm the
in-container compaction once an image is rebuilt with the new `entrypoint.sh`.

- **0.1 Effective image identity** (§5.1): read `container.image` + `jobDefinition` revision from
  `describe-jobs`, resolve tag → digest via `ecr describe-images`, **assert equality with the
  configured digest and fail the cell as HARNESS on mismatch**; record both; register job
  definitions **by digest** in the bootstrap script; in-container, read `ImageID` from
  `$ECS_CONTAINER_METADATA_URI_V4` into `_sandbox_meta.json` as a second witness.
- **0.2 Unsupported-factor preflight** (§5.2): `supported_factor_levels()` on every runner, checked
  at `retort run` start beside the judge preflight; abort listing the levels the lane cannot honour.
- **0.3 Runner fall-through fails closed** (§2): unknown / `cloud` / `docker`-without-docker →
  `ClickException`, never `_simulate_run`. Also the standalone upstream issue.
- **0.4 Bounded, gz-aware log readers** (§5.5): one helper (`.log` or `.log.gz`, max bytes) for
  `agent_consulted`, the diagnose helper, the live-context reader and `sandbox_runner`; usage
  parsers consume a line stream; `RunArtifacts.stdout` carries a bounded tail for sandbox runs;
  drop `message_update` events at write time in the prime lane.

### Phase 1 — one source of truth (~2–3 days)

- **1.1 Shared harness module** `playpen/harness.py`: `resolve_harness`, `resolve_model`,
  `resolve_model_options`, `write_opencode_config`, `build_agent_command(harness, stack, task, *,
  workspace, prompts_dir, max_turns, timeout_minutes, …)` lifted out of `LocalRunner` and called by
  both runners (`SandboxRunner` passes `workspace=Path("/workspace")`). `prompt`, `effort` and
  per-task `max_turns` land on the lane for free. `LocalRunner` behaviour unchanged — golden test of
  the commands it builds today for every harness.
- **1.2 In-container entry as a package module** `retort/playpen/sandbox_entry.py`, run as
  `python -m retort.playpen.sandbox_entry` (the `retort` console script is unusable in the slim
  image because `cli.py` imports the design stack). Replaces the inline watchdog, `score_gate.py`
  and `score_full.py`; reuses `_run_with_progress_guard` (same `hard_wall`/`stall` vocabulary) and
  `ScoreCollector`; writes `_sandbox_meta.json` + `_container_scores.json` + hardware/cost fields
  (§5.4). `entrypoint.sh` shrinks to pull → exec module → push. Unit-testable with a directory
  standing in for S3.
- **1.2b `docker` backend, replacing `DockerRunner`** (decision 2026-09-04). The images already
  *are* the cell; only S3 transfer and Batch submission are Fargate-specific. Add a `backend` seam to
  `SandboxRunner` — `batch` (today's path) and `docker` (`docker run --platform linux/amd64` with
  the workspace bind-mounted at `/workspace` and the same `RETORT_*` environment) — so the same
  image and entrypoint run locally. What it buys: a **$0 smoke of every entrypoint/image change**
  (the container side Phase 0 could not verify), an offline integration test of the container
  contract for CI, and one runner with two backends as the upstream story. Guardrails: the local
  backend stamps `runner_lane=docker-local` (arm64 emulating amd64 — timings are meaningless and
  must never pool), and it never touches AWS. When it passes the sandbox test suite, **delete
  `docker_runner.py`** and its two tests. Not chosen: repairing `DockerRunner` (it would re-solve
  agent install, auth, usage parsing and scoring the images already solved) or deleting it with no
  replacement (loses the smoke path).
- **1.3 Registry visibility**: register `sandbox` via a factory so `retort plugin list/show` names
  it; keep the cli branch. Add `sandbox` to the README command reference and `workspace.yaml` docs.
- **1.4 Experiment-level provenance** `sandbox:` block (§3.5): digests, job-def revisions,
  vCPU/memory, lane; `host` states the lane.

### Phase 2 — in-container scores become authoritative (~1 day + parity smoke)

- **2.1** When `runner_lane == sandbox` and `_container_scores.json` covers every metric in
  `responses`, **that is `scores.json`**; the host does not rescore. Missing metric → HARNESS
  failure, never a silent host fallback. `retort rescore` stamps `rescored_lane: host`.
- **2.2** Re-run the §0c parity check per image as the acceptance gate; record the result
  digest-by-digest in `sandbox/images.lock.json` (Phase 4).

### Phase 3 — parallelism (~0.5 day)

A shard driver script (`scripts/sandbox_drive.sh`) that launches and reaps 16 `retort run --shard`
processes. The protocol extension is shelved (§6).

### Phase 4 — image reproducibility (~1 day)

One Dockerfile per language with the prime layer as a build stage/arg (instead of `-v3`/`-v4`
files `FROM` a hard-coded digest); `LABEL org.opencontainers.image.revision=<commit>` and
`…source=<repo>`; `ECR_REGISTRY` as a build-arg (removes the account id from the tree); a build
script that appends `{tag, digest, commit, dirty, prime_bundle_sha256, parity}` to a committed
`sandbox/images.lock.json`, which `image_digests` in workspace.yaml is validated against.

### Order and effort

| phase | days | unblocks |
|---|---:|---|
| 0 fail-closed | 1 | trustworthy runs now; upstream footgun issue |
| 2 authoritative in-container scores | 1 | 16-wide grids (host contention gone); honest `build_time` |
| 1 one source of truth | 2–3 | `prompt`/`effort` on the lane; claude-code and csharp lanes branch-free |
| 4 image reproducibility | 1 | upstream PR D prerequisite |
| 3 shard driver | 0.5 | operator convenience |
| 5 upstream (§8) | per PR | — |

Phases 0, 1 and 4 are independent and can be separate PRs onto this fork's `main`. Phases 0.4 and 2
are the prerequisites for running 16 wide; Phase 1 is consistency work and not on the scaling path.

---

## 8. Upstream

Convention: outside contributors send **code-only** PRs. `experiments-local/`, `master-local.*`
and the `data/maui-experiments` branch never go upstream, and that branch is never a PR base.

| | PR | size | depends on |
|---|---|---|---|
| **A** | provenance: tolerate Hermes ≥0.20 mapping-style `model:` key | 1 file, +8/−1 | — |
| **B** | scorer robustness (undecodable-file fix, 6 scorers) | 7 files, +73/−10 | — |
| **C** | opencode `model_options` (OpenRouter provider pin) + authoritative `OPENCODE_CONFIG` | 3 files, +61/−1 | — |
| **D** | **SandboxRunner** — lane, images, bootstrap, in-container scoring | 15 files, +2257 | **C** (`profile.model_options`); as committed on main also contains E's prime branch in `sandbox_runner.py` — strip it, or land E-local first |
| **E** | prime-agent harness — local lane (`schema.py` + `local_runner.py`, +198) independent; sandbox half (+62, `Dockerfile.python-v4`) needs D | | E-sandbox → D |
| **F** | log handling — reader fix standalone; write-time filter needs E | | F-filter → E |
| **G** | runner hygiene: `local` becomes the schema default; `_simulate_run` deleted; `cloud`/unknown fail closed | 3 files, tiny | — (sends first; needs no AWS code and no opinion on D) |

A, B, C and F-reader are independently useful upstream: A fixes a Hermes version he runs; C is the
provider pin behind the `exp-mu-glm53-provider` result; B hardens local-lane scorers; F-reader
bounds reads regardless of which agent wrote the log.

**Order:** G → A → C → B → F-reader (small, independent), then D **after Phases 0–1 and 4** — a reviewer
reading `sandbox_runner.py` today sees copied `LocalRunner` code and an unverified digest — then E,
then F-filter. **Rebase on `upstream/main` first**: a trial `git merge-tree` shows `cli.py` and
`test_coverage.py` auto-merge; the only conflicts are `docs/future-experiments.md` and
`docs/past-experiments.md`. Auto-merge is mechanical: B's fix and upstream's `go test`-at-module-root
fix both touch `test_coverage.py` and must be re-read together. Upstream moves daily; do not pin
ahead/behind counts here.

### Questions for adrianco, before the D PR

1. **Do you want an AWS dependency in retort at all?** Your README lists a CloudRunner under *Not
   yet*; this fills that slot, additively (`runner: local` untouched), with a parity harness and
   evidence it agrees with the local lane 3/3. Offer, not fait accompli.
2. **Naming.** `sandbox` beside the dead `cloud` enum value — retire `cloud`, alias it, or rename?
   (`cloud` already means "hosted model" in your experiment data, so we avoided it.)
3. **The `DockerRunner` default and fall-through** (§2) — PR G proposes `local` as default and
   deleting `_simulate_run`; the lane PR later offers a working local `docker` backend in its place.
4. **Image distribution.** Our images live in our ECR. Upstream use needs a public registry or a
   documented build-your-own path; the Dockerfiles build from source, so build-your-own is viable
   once Phase 4 lands.
5. **Provider neutrality.** The provision/execute/collect seam was kept provider-neutral so an Azure
   Container Apps Jobs backend could follow. Worth keeping, or is one backend cleaner?

---

## 9. How to verify these claims yourself

```bash
git fetch upstream
git log --oneline upstream/main..main                    # what we have that upstream doesn't
git merge-tree --write-tree upstream/main main | grep CONFLICT
git log upstream/main --diff-filter=A --name-only \
    --format="" -- 'src/retort/playpen/*' | sort -u      # every runner ever added upstream
git grep -h "runner:" upstream/main -- '*/workspace.yaml' | sort | uniq -c
git show upstream/main:README.md | grep -n CloudRunner   # the "Not yet" line
grep -rn "_container_scores" src/                        # consumed only inside sandbox_runner.py
aws ecr describe-images --repository-name retort-sandbox --region us-east-1 \
    --query 'sort_by(imageDetails,&imagePushedAt)[].[imagePushedAt,imageTags,imageDigest]'
aws batch describe-job-definitions --job-definition-name retort-sandbox-python --status ACTIVE \
    --query 'jobDefinitions[].[revision,containerProperties.image]'   # by TAG, not digest
```

Related: [future-experiments.md §0c](future-experiments.md) (pre-registered methodology, IN USE),
[past-experiments](past-experiments.md) (`exp-mu-primeagent`, first production family on this lane).
