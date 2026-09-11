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
| 2 | **Per-language images** | `sandbox/Dockerfile.{python,go,typescript}`, `sandbox/build_images.sh`, `sandbox/images.lock.json` → ECR `retort-sandbox` | **v5 generation built 2026-09-10** on the x86_64 box (§9.1) from one reproducible recipe per language (Phase 4): OCI labels carry commit/dirty/prime version/bundle sha; the lock file records every pushed digest with its inputs; no account id in the tree |
| 3 | **In-container entrypoint + watchdog** | `sandbox/entrypoint.sh` (inline Python) | Implemented; a **second implementation** of the local progress guard (§5.3) |
| 4 | **In-container scoring** | `sandbox/score_full.py`, `score_gate.py` → `_container_scores.json` | **Authoritative for container lanes since Phase 2 (2026-09-05):** `cli._collect_scores` takes the file as `scores.json`; the host never rescores; a completed cell with no file is HARNESS BROKEN (§3.4). `score_in_container` defaults on |
| 5 | **Image identity in provenance** | `sandbox_image_digest[_effective]`, `sandbox_job_definition`, `_sandbox_meta.json` witnesses | **Verified per job** against Batch's container image since Phase 0 (2026-09-04); mismatch or unverifiable pin fails the cell as HARNESS (§5.1) |
| 6 | **Parallelism** | `retort run --shard i/N` processes sharing one `retort.db` | Implemented; design point **16 concurrent cells** (§6) |
| 7 | **Bootstrap** | `scripts/sandbox_bootstrap_aws.sh` | Implemented; registers job-defs **by digest** (Phase 0); derives the account id at run time (no id in the tree since Phase 4) |
| 9 | **Transcript readers** | `src/retort/playpen/agent_log.py` | Bounded, `.gz`-aware, streaming (Phase 0); prime transcripts compacted at write time, 193 MB → 21 MB measured (§5.5) |
| 10 | **`docker` backend** (local lane) | `SandboxRunner(backend="docker")`, `playpen.sandbox.backend: docker` + `docker_images` | Implemented 2026-09-04 (Phase 1.2b): same image + entrypoint under `docker run`, bind-mounted workspace, no AWS; stamps `runner_lane=docker-local` (never pooled). **$0 echo cell passed 2026-09-05** on python-v4c with the new entrypoint mounted in (file round-trip, meta written, S3 skipped). **Real agent cell passed 2026-09-08** (opencode × GLM-5.3-flash × python on `retort-sandbox:python-local` under Colima+Rosetta: 15/15 tests, coverage 0.98, 160 s, `scored_lane=docker-local`, witnesses `cpu_arch=x86_64`). `DockerRunner` deleted the same day; `runner: docker` is now the alias for this backend |
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
`RunnerType.docker` **was the schema default** (flipped to `local` 2026-09-10, along with the
`retort init` template), and `cli.py`'s `else` branch used to construct a
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

### 3.4 Where scoring happens — in-container is authoritative (Phase 2, 2026-09-05)

**Now:** `cli._collect_scores` decides per cell. Local lane: the host collector, unchanged.
Container lanes (`runner_lane` ∈ {`sandbox`, `docker-local`}): `_container_scores.json` **is**
`scores.json`; the host does not rescore. A `null` in the file is a scorer's "not applicable"
(left NULL, as the collector would); an absent metric is recorded as `scored_missing` and left
NULL (images built before 2026-09-05 omit N/A metrics instead of writing `null`; `score_full.py`
now writes every requested key). A cell that completed but left no file is **HARNESS BROKEN** and
stops the run — never a silent host fallback. A crashed cell scores on the host, stamped
`scored_lane=host`, and is a retry, not a data point. `retort rescore` stamps
`rescored_lane: host` into a container-lane archive's `_meta.json`. `score_in_container` defaults
to true. Six unit tests pin the branches.

**Before (the finding that motivated it):** [DIRECT] After `execute()` returned, the run loop
called the host `ScoreCollector` on the pulled workspace for **every** lane, and that result was
`scores.json`. The container's `_container_scores.json` was written by `score_full.py` and
**consumed by nothing** in `src/`; its own docstring said promoting it was "a host-side pipeline
decision deliberately NOT made here".

Consequences: a sandbox run's `build_time` is a **host** measurement of a workspace built elsewhere;
the host still needs every language toolchain (a `csharp` image does not remove the need for
`dotnet` on the M4); and scoring re-introduces the host contention the lane exists to remove — one
`go test` / `pytest` / `npm test` per returning cell, on the shared machine. Making the in-container
scores authoritative is Phase 2 of the plan (§7).

### 3.5 Provenance — the per-run metadata was never persisted at all (fixed 2026-09-05)

[DIRECT] `provenance.json` for a sandbox experiment has keys `agent_config, agents, harness, host,
models, retort, serving, stack_presets, tools` — no image digests, job-definition revisions, vCPU
or memory, and `host` describes the M4, not the lane.

Worse, and found only while wiring Phase 2: **`RunArtifacts.metadata` was not written anywhere.**
The DB row (`experiment_runs`) keeps status, timestamps and `run_config_json`; `run_results` keeps
metric values; `_meta.json` kept four fields (`visibility`, `run_config`, `replicate`,
`succeeded`). A grep of the whole `exp-mu-primeagent-easy` tree for `sandbox_image_digest` or
`runner_lane` finds **nothing**. So the handoff's "the digest lands in every run's provenance" was
false: image digest, job id, queue seconds, vCPU/memory, `kill_reason`, `tool_refusal`,
`wrote_nothing` and the usage breakdown existed only in process memory for every cell ever run
on either lane. Only `_sandbox_meta.json` inside the workspace (written by the container, not the
runner) survived, which is what the earlier spot-check read.

**Fix:** `_archive_run_workspace` now writes `runner_lane`, `scored_lane` and the full
`metadata` dict into `_meta.json` — the archive is the durable record. An experiment-level
`sandbox:` block in `provenance.py` (digests, job-def revisions, spec) remains Phase 1.4.

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
  list/show`. The cli branch is the house pattern; `plugin list` names `sandbox` and `docker` since 2026-09-08.
- ~~Hard-coded AWS account id in `sandbox/Dockerfile.*-v3/-v4` `FROM` lines~~ — gone with Phase 4 (2026-09-10); the bootstrap and build scripts derive it at run time.
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

**Smoke DONE 2026-09-10** on the v5 images: three Fargate cells (python×prime, go×opencode,
typescript×opencode, GLM-5.3-flash, $0.07 total) all completed; every archive carries
`sandbox_image_digest_effective` equal to the pinned digest, `sandbox_container_image_id`,
`sandbox_cpu_arch=x86_64`, `sandbox_cpu_model` and `sandbox_az`. The witnesses already earned
their keep: the go cell ran on an **AMD EPYC 9R14** and the other two on **Xeon Platinum 8259CL**
(§5.4 is real, and now visible per cell). Prime's transcript came back at 90 KB (compacted
in-container).

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
  **Status 2026-09-05:** implemented (`f06dfb35`), 54 sandbox unit tests green. Echo-cell smoke
  passed against python-v4c with the new `entrypoint.sh` bind-mounted: `hello.txt` came back
  through the mount, `_sandbox_meta.json` written (`agent_seconds` 11.2 under emulation), S3
  transfers skipped cleanly, the in-container compaction guard held (`|| true`) when the old
  image lacked `retort.playpen.agent_log`. Learned: `work_dir` must be under a Docker-Desktop-shared
  path (`~/.retort-sandbox` is; `/private/tmp` mounts appear empty); an emulated `/proc/cpuinfo`
  has no `model name`, so `cpu_arch` is now recorded too.
  **2026-09-05, locally built image (`retort-sandbox:python-local`, this worktree's wheel):** the
  echo cell ran through the image's own entrypoint. First run **caught a real bug** the unit tests
  missed — the entrypoint passed a `str` to `compact_prime_log`, which `.stat()`-ed it; the
  `|| true` guard swallowed the crash and an 18 MB seed transcript came back uncompacted
  (`70d259e5` fixes and pins it). Second run: `compact_prime_log: 18002906 -> 506 bytes`, 0
  `message_update` lines left, both `message_end` events intact, `cpu_arch=x86_64` recorded,
  `agent_seconds` 10.5. This is exactly the $0 smoke the docker lane exists for. Three earlier
  rebuild attempts had died on PyPI/npm read timeouts (network, not the recipe).
  **2026-09-05, first real agent cell (opencode × glm-5.3-flash, rest-api-crud) through
  `retort run` on the docker lane — HARNESS failure, and two findings.** (1) opencode is a Bun
  binary and **Bun requires AVX**; the docker host here is Colima (aarch64 VM, Virtualization
  framework, sshfs mounts) emulating amd64 through QEMU user-mode, which exposes no AVX —
  opencode segfaulted at startup (`CPU lacks AVX support … Bun has crashed`) after one
  `step_finish` ($0.0004). So **the docker lane cannot run opencode cells under QEMU**; prime-agent
  (node) should be unaffected. Fix options, in order: enable Rosetta in Colima (`colima start
  --vz-rosetta`; Rosetta supports AVX2 on macOS ≥ 15 and is much faster) — a host setting, the
  user's call; or build arm64 images for the local lane (weakens "same image"). (2) The crashing
  runtime wrote a QEMU core file into the workspace at ~6 GB/min — **64 GB in ten minutes** — and
  the growing file counted as workspace progress, so the stall guard never fired; the cell was
  killed by hand. `entrypoint.sh` now sets `ulimit -c 0` (also protects Fargate's ephemeral disk
  and the artifact upload). The seeding, provision, `docker run` shape, secret forwarding and
  `retort run` wiring all worked; the cell died inside the agent binary. **Still owed:** the same
  cell after Rosetta is enabled (or with prime-agent), then `docker_runner.py` goes.
  **Status 2026-09-08: DONE.** Rosetta enabled in Colima (`rosetta: true`; AVX/AVX2 visible in an
  amd64 container; home-dir sshfs mounts unaffected; the VM restart took 30 s). The same cell then
  ran end to end on `retort-sandbox:python-local`: opencode × GLM-5.3-flash, 160 s, 15/15 tests,
  `_container_scores.json` = `scores.json` = {code_quality 0.67, test_coverage 0.98},
  `runner_lane=scored_lane=docker-local`, `sandbox_cpu_arch=x86_64`,
  `sandbox_cpu_model="VirtualApple @ 2.50GHz"`, `sandbox_image_digest_effective` = the local image
  id. `docker_runner.py` and its tests are deleted; `runner: docker` (no longer the schema default — `local` is, since
  2026-09-10) is now an alias for `runner: sandbox` with `backend: docker` and refuses to run without a
  `playpen.sandbox` block that says so. The integration test that relied on simulated cells uses
  a canned stub runner instead.
- **1.3 Registry visibility** — DONE 2026-09-08 for the registry half: `create_default_runner_registry`
  registers `sandbox` and `docker` (= `SandboxRunner(backend="docker")`) so `retort plugin list/show`
  names them; the cli branch stays. Still owed: `sandbox` in the README command reference and the
  `workspace.yaml` docs. Add `sandbox` to the README command reference and `workspace.yaml` docs.
- **1.4 Experiment-level provenance** `sandbox:` block (§3.5): digests, job-def revisions,
  vCPU/memory, lane; `host` states the lane.

### Phase 2 — in-container scores become authoritative — DONE 2026-09-05 (code), verified on Fargate 2026-09-10

Landed: `_collect_scores` (both collect sites in the run loop), `scored_lane`/`runner_lane` and
the **full per-run metadata** in `_meta.json` (§3.5 — it had never been persisted), the rescore
lane stamp, `score_in_container` default on, `score_full.py` writing explicit nulls.
**Verified 2026-09-10:** all three v5 Fargate cells archived `scored_lane=sandbox` with
`scores.json` equal to `_container_scores.json` (the retired `build_time` metric comes back
`null` in the file and is dropped as NULL on the host — list `_duration_seconds` telemetry
instead; a workspace that still names `build_time` gets a null column, not an error). Two
naming warts noticed, not bugs: `_sandbox_meta.json`'s `scored`/`tests_*` fields come from the
python-only pytest fast path (`score_gate.py`) and read false/absent for go and typescript even
though `score_full.py` scored them; the zone lands as `sandbox_az`.

- **2.1** When `runner_lane == sandbox` and `_container_scores.json` covers every metric in
  `responses`, **that is `scores.json`**; the host does not rescore. Missing metric → HARNESS
  failure, never a silent host fallback. `retort rescore` stamps `rescored_lane: host`.
- **2.2** Re-run the §0c parity check per image as the acceptance gate; record the result
  digest-by-digest in `sandbox/images.lock.json` (Phase 4).

### Phase 3 — parallelism (~0.5 day)

A shard driver script (`scripts/sandbox_drive.sh`) that launches and reaps 16 `retort run --shard`
processes. The protocol extension is shelved (§6).

### Phase 4 — image reproducibility — DONE 2026-09-10 (`473add27`, `a7eadd49`)

**Landed:** `Dockerfile.{python,go,typescript}` each carry the whole recipe (scorer suite,
opencode 1.18.20, node 22, prime-agent bundle + kernel venv, entrypoint) — the `-v3`/`-v4`
files `FROM` a hard-coded account digest are gone, and with them the account id in the tree
(the registry is derived at build time, so `ECR_REGISTRY` is an env override, not a
build-arg). `build_images.sh {stage|build|push} <gen> <lang>…` stages the bundle, passes
`RETORT_COMMIT/RETORT_DIRTY/PRIME_AGENT_VERSION/PRIME_BUNDLE_SHA256` as build-args into OCI
labels, pushes, and appends to `sandbox/images.lock.json`. v5 was built on the x86_64 box from
a tarball of the clean `473add27` tree (30 min for three images on a t3.medium). Not done:
validating `image_digests` in workspace.yaml against the lock file, and the `parity` field.

Original plan:

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

## 7b. Adversarial review — 2026-09-11 (PR #1 on the fork)

Two independent reviews of the branch at `6f14f781`: Claude Code's `/code-review` at high effort
(8 findings, all confirmed by its verifier, 4 reproduced) and `trusty-review` with GLM-5.2 via
Fireworks (24 raw findings; its Bedrock verifier failed on transport, so its `APPROVE*` verdict
was unverified — 2 of its findings were false positives, 1 was refuted by the Fargate run, 1 was
real and minor). Everything below is FIXED on the branch (`e7b990c6`, `7f2c5e40`, `c95b1e95`).

| # | finding | fix |
|---|---|---|
| 1 | Batch digest verified AFTER the job ran and artifacts were extracted; a mismatch became a crash row while the wrong-image `_container_scores.json` was still adopted | `check_design()` resolves each pinned language's job-definition image once BEFORE any submit and refuses the grid; the run loop stops on any `HARNESS:` artifact; a non-succeeded cell never has its container scores adopted |
| 2 | "HARNESS BROKEN" raised before archive → teardown deleted the evidence | `_HarnessStopError` + `_stop_with_evidence()`: archive, then stop, message names the archive |
| 3 | `score_full.py` scored with `exit_code=0`, no tokens, no duration → killed cells scored as success, `token_efficiency` fell back to transcript length | entrypoint passes `RETORT_AGENT_EXIT/SECONDS/KILL_REASON`; `score_full` mirrors `_collect` (parsed tokens, 124 on kill, bounded tails). Verified: in-container `token_efficiency` 0.0224 == host parsed value (fallback gave 1.0); simulated stall → exit 124, `runtime=null` |
| 4 | `_harness_failure` skip-list lacked harness-owned files → `retort diagnose` labelled zero-write sandbox cells GENUINE | `_harness_owned_file()` rule (underscore/dot prefix, explicit names, `.gz` forms) |
| 5 | pinned digest resolved via ECR per cell AFTER the job; `TimeoutExpired` uncaught | resolved once at preflight and cached; `_aws` converts timeouts to `RuntimeError` |
| 6 | `retort init` template and schema default still `runner: docker`, which now hard-fails | both default to `local` |
| 7 | truncated `.gz` transcripts raised `EOFError` past every `except OSError` | `agent_log.READ_ERRORS`; gz paths iterate by line (`GzipFile.read(n)` discards inflated bytes on EOFError) |
| 8 | hung docker daemon at `image inspect` escaped `execute()` | caught alongside `RuntimeError`, at preflight too |
| t4 | malformed `_container_scores.json` → bare traceback | HARNESS BROKEN via the same archive-first stop |

Also: `score_in_container: false` on a container lane is refused at preflight (the host never
rescores a container workspace); `_make_runner` in the sandbox tests refuses real AWS calls by
default — the first preflight test reached the account.

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

### 9.1 The x86_64 build/smoke box (`scripts/sandbox_buildbox_aws.sh`)

The Mac can only build the amd64 images under emulation and cannot run Bun/opencode at all
(Bun needs AVX, which Rosetta/QEMU do not provide), so image builds and one-cell smokes of the
`docker` backend at the Fargate shape (2 vCPU / 8 GB) run on a small x86_64 EC2 instance:
`retort-sandbox-build`, a t3.medium with a 30 GB gp3 root on the latest Amazon Linux 2023
x86_64 AMI (resolved at create time from the SSM public parameter), in the same region and
account as the ECR repo. Access is **SSM Session Manager only** — no key pair, no inbound
security-group rules. Its instance profile (`retort-sandbox-build`) carries
`AmazonSSMManagedInstanceCore`, `AmazonEC2ContainerRegistryPowerUser` (push/pull to
`retort-sandbox`) and `GetSecretValue` on `retort/openrouter-opencode` only, so a smoke cell can
fetch the same key the Fargate lane uses. User data installs docker, git, the buildx plugin and
the AWS CLI, and adds `ec2-user` to the docker group. **It is not part of any experiment lane**:
timings from it are docker-local, never pooled with Fargate cells.

```bash
scripts/sandbox_buildbox_aws.sh create    # role + profile + egress-only SG + instance (idempotent)
scripts/sandbox_buildbox_aws.sh status    # instance id, state, public IP, SSM PingStatus
scripts/sandbox_buildbox_aws.sh ssm       # prints the `aws ssm start-session` command
scripts/sandbox_buildbox_aws.sh stop      # stop when done — only the root volume bills
scripts/sandbox_buildbox_aws.sh start     # resume (new public IP; auto-shutdown re-arms)
scripts/sandbox_buildbox_aws.sh destroy   # terminate + delete role/profile/SG (asks first)
```

**4-hour auto-shutdown.** Every boot arms `shutdown -h +240`, so a forgotten box powers itself
off after four hours (`BUILDBOX_SHUTDOWN_MINUTES` overrides it at create time). A stopped
instance keeps its root volume and its docker layer cache; `start` brings it back with a fresh
four-hour budget. `AWS_REGION` defaults to `us-east-1`, matching `sandbox_bootstrap_aws.sh`.
Verify a fresh box before trusting it: `docker info` works for `ec2-user`, `grep -c avx
/proc/cpuinfo` is non-zero, and `docker buildx version` prints a version — the same three
checks the bootstrap run recorded.

Related: [future-experiments.md §0c](future-experiments.md) (pre-registered methodology, IN USE),
[past-experiments](past-experiments.md) (`exp-mu-primeagent`, first production family on this lane).
