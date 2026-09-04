# Cloud lane (SandboxRunner) — pressure test of the handoff, and the plan

**Written:** 2026-09-04, in worktree `../retort-cloudlane` (branch `feat/cloud-lane`).
**Scope:** pressure-tests [cloud-execution-handoff.md](cloud-execution-handoff.md) claim by claim against
the code, the ECR/Batch state and the run archives, then lays out the plan for making the Fargate lane
consistent with retort's existing patterns. Tags: **[DIRECT]** observed, **[HYPOTHESIS]** inferred.

The one-line verdict: the lane works and its validation evidence holds up, but the handoff
overstates where scoring happens, gets the prime-log rationale backwards, and misses the two defects
that matter most for this project's first principle — the sandbox lane **records a configured image
digest it never verifies**, and it **silently ignores design factors** it does not implement.

---

## 1. Handoff claims that are wrong or overstated

### 1.1 "Scorers run in-container, because otherwise build_time stops being comparable" — overstated

[DIRECT] The authoritative `scores.json` for a sandbox run is computed **on the host**:
`cli.py:1101` calls `collector.collect(artifacts, stack)` for every lane after `execute()` returns.
`_container_scores.json` is written in-container by `score_full.py` but **consumed by nothing** in
`src/` (its only mentions are inside `sandbox_runner.py`). Consequences the handoff does not draw:

- the `build_time` recorded for a sandbox run is a **host** measurement of a workspace built elsewhere;
- the host still needs every language toolchain installed (a `csharp` image does not remove the need
  for `dotnet` on the M4);
- host-side scoring re-introduces the very host contention and serialisation the lane exists to
  remove — `go test`, `npm test`, `pytest` all run on the shared machine, one cell at a time.

`score_full.py`'s own docstring says this plainly ("Promoting `_container_scores.json` to the
authoritative scores is a host-side pipeline decision deliberately NOT made here"). The handoff's §1
should say *advisory in-container scores; authoritative host scores*. That decision is Phase 2 below.

### 1.2 "stopReason/usage/cost appear ONLY on message_update, never on message_end" — wrong

[DIRECT] Streamed over the 193 MB brazil rep3 log (41,451 events): 182 `message_end` events, of which
the 91 with `role=assistant` **all carry `usage` (incl. `cost.total`), `stopReason`, `model` and
`responseId`**. The other 91 are `toolResult` messages, which never have usage anywhere.
`_parse_prime_usage` (`local_runner.py:1801`) reads `message_end` — exactly right — so dropping
**every** `message_update` at write time is safe for tokens, cost, turns, stop reasons and generation
ids. The handoff's "safe filter" (keep the last delta) is harmless but its rationale is inverted, and
the memory note derived from it was wrong. The final assistant content also lives on `message_end`
(`content` present on all 182). Filtering `message_update` entirely takes 193 MB → roughly 21 MB
(the 17.6 MB of `tool_execution_update` plus 3.4 MB rest); keep those for failure evidence.

### 1.3 Rebase conflicts "confined to cli.py and test_coverage.py" — wrong; and the counts are stale

[DIRECT] `git merge-tree --write-tree upstream/main main` today: `cli.py` and
`scoring/scorers/test_coverage.py` **auto-merge**. The only conflicts are `docs/future-experiments.md`
and `docs/past-experiments.md` (both sides append experiment entries). Auto-merge is mechanical, not
semantic — B's undecodable-file fix and upstream's `go test`-at-module-root fix both touch
`test_coverage.py` and must be re-read together — but the rebase is cheaper than the doc says.
Counts now: main is 21 ahead (matches), **33 behind** (doc: 24); upstream has **81** `runner: local`
workspaces (doc: 76). Upstream moves daily; do not pin numbers in the handoff.

### 1.4 PR dependency table: D does NOT stand alone, and D-as-committed contains E

[DIRECT] `SandboxRunner` reads `profile.model_options` and cli.py passes
`_oc_profile.model_options` — the field added by C (`3a276752`). **D depends on C.** And the prime
branch inside `sandbox_runner.py` (`harness == "prime"` in `_build_agent_command`) arrived with E
(`ea488015`), so a D PR cut from main ships part of E; either strip it or send E-local first. Revised
order in §3 Phase 5.

### 1.5 go-v2 hypothesis — confirmed, and there are more unrecorded generations

[DIRECT] ECR (`describe-images`, sorted by push time):

| pushed (UTC) | tag | digest | size |
|---|---|---|---:|
| 08-31 16:45 | python | 52dd5303 | 707 MB |
| 08-31 21:15 | python-v2 | f1b82a01 | 707 MB |
| 09-01 14:26 | python-v3 | 4d04fe10 | 723 MB |
| 09-01 15:17 | go-v1 / typescript-v1 | 48743d87 / e23e1a92 | 916 / 551 MB |
| 09-01 15:22 | **go-v2 / typescript-v2** | e54e89a5 / 3bc005ce | **916 / 551 MB** |
| 09-02 10:55 | **python-v4c** | f59c3b0b | 951 MB |
| 09-02 16:55 | go-v3 | 2e458f4b | 1145 MB |
| 09-02 16:57 | typescript-v3 | e002fd8e | 717 MB |
| 09-02 17:04 | **go-v3b** | 27dddbf6 | 1145 MB |

go-v2/ts-v2 were pushed five minutes after v1 at byte-identical sizes — consistent with the same
Dockerfile rebuilt against a later worktree (the undecodable-file scorer fix in `12ed60ee`). The
exp-mu-primeagent digests in the handoff resolve to **python-v4c, go-v3b, typescript-v3**. Batch job
definitions also carry `python-v4`, `python-v4b` (revisions 6, 7) and `go-v3` (rev 3): three more
generations that exist in AWS but correspond to no committed recipe. The "image identity =
(Dockerfile, source commit, staged prime bundle)" defect is real and bigger than one tag.

### 1.6 "Two mechanisms select a runner" — misdiagnosed

[DIRECT] `cli.py` uses the `RunnerRegistry` for **no** runner: `local` (`:843`), `sandbox` (`:872`),
`metaharness` (`:891`) and `docker` (`:897`) are all constructed directly with config-derived
arguments. The registry (`runner.py:create_default_runner_registry`) backs only `retort plugin
list/show` (`commands/utility.py:57-77`) and the pluggy `retort_register_runners` hook. So the cli
branch **is** the house pattern; the actual inconsistency is that `retort plugin list` cannot name
`sandbox`. Small fix (Phase 1.3), not a design question for the PR.

### 1.7 Missed: `RunnerType.cloud` has existed upstream since day one, and it is a footgun too

[DIRECT] `schema.py:156` has `cloud = "cloud"` from upstream's original config layer (`5170b787`,
2026-04-10), and `runner.py`'s module docstring names "CloudRunner (optional)". `runner: cloud` (and
any other unmatched value) falls through cli.py's `else` to `DockerRunner` → `_simulate_run()` →
random metrics. Two points for the upstream conversation: the original design **did** reserve a cloud
slot (naming ours `sandbox` beside a dead `cloud` needs a sentence), and the fall-through should fail
closed regardless of what happens to `DockerRunner`.

### 1.8 Confirmed as written

[DIRECT] `DockerRunner._simulate_run` random metrics; `RunnerType.docker` schema default; unbounded
`read_text()` in `agent_consulted` (`local_runner.py:1323`) and the diagnose helper (`cli.py:279`),
bounded tail at `cli.py:173`; validation evidence consistent with the archive (python rep1
`_sandbox_meta.json`: 12/12 tests, 95.83 % coverage, digest f59c3b0b); 30 unit tests in
`test_sandbox_runner.py`; **whole unit suite green** (`pytest tests/unit`, one skip: graphify not
installed). The single failure seen first was `VIRTUAL_ENV` leaking from an activated shell into
`_build_env`'s `os.environ.copy()` — a test-environment artifact, not a defect.

---

## 2. Defects the handoff does not list

Ordered by how directly each violates *"verify tuning parameters; effective value, not configured"*.

### 2.1 The recorded image digest is the configured one, never the effective one — **highest priority**

[DIRECT] The job definitions reference images **by tag**
(`…/retort-sandbox:python-v4c`), the runner submits `--job-definition retort-sandbox-<lang>` with
**no revision** (= latest ACTIVE), and both `sandbox_image_digest` in metadata and `image_digest` in
`_sandbox_meta.json` are copied from `playpen.sandbox.image_digests` in workspace.yaml. Nothing reads
what actually ran. Register revision 9 with a new image and forget the yaml, and every run records
v4c while v5 executes — the Hermes-context-length failure, verbatim. Today the only thing making
tag≈digest true is the ECR repository's IMMUTABLE setting, an out-of-band invariant no test checks.

Fix: (a) `describe-jobs` returns `container.image` and `jobDefinition` (with revision) — resolve the
tag to a digest via `ecr describe-images`, **assert equality with the configured digest, fail the cell
as HARNESS on mismatch**, record both the effective digest and the job-definition revision;
(b) register job definitions **by digest** (`repo@sha256:…`) so the yaml, the job-def and the running
image cannot disagree; (c) in-container, read the digest from the ECS task metadata endpoint
(`$ECS_CONTAINER_METADATA_URI_V4` → `ImageID`) into `_sandbox_meta.json` as a second witness.

### 2.2 Design factors silently ignored on the sandbox lane

[DIRECT] `SandboxRunner._build_agent_command` calls `_local._build_agent_prompt(stack)` with **no
`prompt_injection`** and cli.py passes no `prompts_dir`; `LocalRunner` loads `prompts/<level>.md` for
`prompt != none` in every harness branch (`local_runner.py:953, 1079`). A sandbox design with
`prompt: [none, bdd, tdd]` runs the plain prompt three times and records three levels. Likewise the
`tooling=graphify` pre-run hook (`local_runner.py:547`) never runs, while `_build_agent_prompt` still
tells the agent to consult `graphify-out/`; `stack` presets / `LCM_CONTEXT_THRESHOLD` are not
exported. None of this is exercised by current experiments (all `prompt`/`tooling` = none), which is
exactly why it is dangerous: the first experiment that varies one will produce confident nulls.

Fix: fail closed. A `supported_factor_levels()` on each runner, checked once at `retort run` start
beside the judge preflight: any design level the lane cannot honour aborts the run with the list.
Then implement `prompt` (trivial once command building is shared, Phase 1).

### 2.3 Duplicated harness logic — the actual "pattern inconsistency"

[DIRECT] `SandboxRunner` re-implements `_resolve_harness`, `_model_for`, `_model_options_for`,
`_write_opencode_config`, and the opencode + prime branches of `_build_agent_command` (each a copy of
the `LocalRunner` branch with `/workspace` substituted). The container's watchdog is a second
implementation of `_run_with_progress_guard` (`local_runner.py:161-293`, 130 tested lines) as inline
Python inside `entrypoint.sh`, with a **different kill vocabulary** (`timeout` vs the local guard's
`hard_wall`) that diagnose and crash accounting must now know about twice. `score_full.py`,
`score_gate.py` and the watchdog live outside the package, copied to `/` in the image, even though
the image installs retort itself. The precedent for sharing is already in the tree —
`metaharness_runner.py` imports `_copy_support_files`/`_clone_org_repo` from `local_runner`, and
`sandbox_runner.py` imports `_build_agent_prompt`/`_parse_agent_usage` — it just stopped short.

### 2.4 Serial execution; "cells run wide" only via N processes

[DIRECT] The run loop (`cli.py:1035-1311`) is provision → execute → teardown per cell and
`execute()` blocks on `_poll_job` (15 s polls). One `retort run` on the sandbox lane runs one Fargate
task at a time. Parallelism comes from launching several `retort run --shard i/N` processes sharing a
`retort.db` — which works (shard/resume was proven) but is N host processes, N pollers, and an
operator convention rather than a feature. The pre-registered §0c design said "a design grid IS an
array job"; that was not built. The constraint is the synchronous `PlaypenRunner` protocol.

### 2.5 Fargate hardware is heterogeneous and unrecorded

[DIRECT] `_sandbox_meta.json` records nothing about the host: no CPU model, no availability zone.
[HYPOTHESIS] Fargate places tasks on mixed instance generations, so within-lane `duration` and
`build_time` carry an unrecorded hardware factor. Cheap to close: read `/proc/cpuinfo` model name and
the task metadata `AvailabilityZone` into the meta file, and record the Fargate task cost
(vCPU-seconds × price) as infra cost beside token cost, which is currently absent from every response.

### 2.6 A third unbounded log read, inside the runner itself

[DIRECT] `sandbox_runner.py::_read_text` loads the entire `_agent_stdout.log` into
`RunArtifacts.stdout` (193 MB as a Python `str`, then held through scoring and archiving). The handoff
counts two readers; this is the third, and it is on the hot path of every cell.

### 2.7 Experiment-level provenance has no sandbox section

[DIRECT] `experiment-mu-primeagent-easy/provenance.json` keys: `agent_config, agents, harness, host,
models, retort, serving, stack_presets, tools` — no image digests, job-definition revisions, vCPU or
memory. The lane's tuning parameters exist only in per-run metadata. `provenance.py` should emit a
`sandbox:` block (and `host` should state the lane, so nobody reads the M4's specs as the run's hardware).

---

## 3. The plan

Goal, as I read it: **make the Fargate lane a first-class retort runner that follows the codebase's
patterns** — one source of truth for harness logic, fail-closed on unverified parameters, scores
honest to the environment that built them — so it is trustworthy for our experiments first and
offerable upstream second. Work happens in `../retort-cloudlane` (`feat/cloud-lane`); nothing here
edits the main checkout while experiments run. Each phase ends with unit tests plus **one paid
one-cell smoke on Fargate** (queued behind any live run, per the one-experiment rule).

### Phase 0 — fail closed (small, do first; ~1 day)

0.1 **Effective image identity** (§2.1): record + assert digest and job-def revision from
`describe-jobs`; job-defs registered by digest in the bootstrap script; ECS metadata witness in
`_sandbox_meta.json`. Test: monkeypatched `_aws` returning a mismatching image → cell fails HARNESS.
0.2 **Unsupported-factor preflight** (§2.2): `supported_factor_levels()` on `LocalRunner`,
`SandboxRunner`, `MetaHarnessRunner`; `retort run` aborts listing the unsupported levels.
0.3 **Runner fall-through fails closed** (§1.7): unknown / `cloud` / `docker`-without-docker →
`ClickException`, never `_simulate_run`. (Also the standalone upstream issue.)
0.4 **Bounded, gz-aware log readers** (§1.8, §2.6): one helper (`tail_agent_log(path, max_bytes)`
that opens `.log` or `.log.gz`), used by `agent_consulted`, the diagnose helper, the live-context
reader and `sandbox_runner`; usage parsers consume the file as a line stream, and
`RunArtifacts.stdout` carries a bounded tail for sandbox runs.

### Phase 1 — one source of truth (the consistency work; ~2–3 days)

1.1 **Shared harness module** — `playpen/harness.py`: `resolve_harness`, `resolve_model`,
`resolve_model_options`, `write_opencode_config`, `build_agent_command(harness, stack, task, *,
workspace, prompts_dir, max_turns, timeout_minutes, …)` lifted out of `LocalRunner` (the 250-line
`_build_agent_command` and the four `_*_for` helpers) and called by both runners; `SandboxRunner`
passes `workspace=Path("/workspace")`. This is what makes `prompt`, `effort`, per-task `max_turns`
land on the lane for free and removes the drift risk. `LocalRunner` behaviour is unchanged —
assert with a golden test of the commands it builds today for every harness.
1.2 **In-container entry as a package module** — `retort/playpen/sandbox_entry.py`, run as
`python -m retort.playpen.sandbox_entry` (retort is already installed in the image; the `retort`
console script is not usable there because `cli.py` imports the design stack). It replaces the inline
watchdog, `score_gate.py` and `score_full.py`: reuse `_run_with_progress_guard` (same `hard_wall` /
`stall` vocabulary as local), reuse `ScoreCollector`, write `_sandbox_meta.json` +
`_container_scores.json`, plus the hardware/cost fields from §2.5. `entrypoint.sh` shrinks to
pull → exec module → push. Unit-testable on the host with a directory standing in for S3.
1.3 **Registry visibility**: register `sandbox` via a factory so `retort plugin list/show` names it;
keep the cli branch (that is the pattern for all four runners). Add `sandbox` to the README command
reference and `workspace.yaml` docs (currently only in `docs/*experiments.md`).
1.4 **Experiment-level provenance** `sandbox:` block (§2.7): digests, job-def revisions, vCPU/memory,
lane. The `host` block states the lane.

### Phase 2 — in-container scores become authoritative for the lane (~1 day + parity smoke)

2.1 In the run loop: when `runner_lane == sandbox` and `_container_scores.json` covers every metric in
`responses`, **that is `scores.json`**; the host does not rescore. Missing metric → HARNESS failure,
not a silent host fallback. `retort rescore` keeps working but stamps `rescored_lane: host` so a
host-rescored sandbox run is never mistaken for an in-container one.
2.2 Re-run the §0c parity check per image as the acceptance gate, and record the parity result
digest-by-digest in `sandbox/images.lock.json` (Phase 4).

### Phase 3 — parallelism inside the pipeline (design decision; ~2–3 days if approved)

Two options. **(A) Keep sharding**, add `scripts/sandbox_drive.sh` that launches N shards and reaps
them — zero protocol change, documents the current reality. **(B) Extend the protocol** with an
optional async pair (`submit(env_id, …) -> handle`, `collect(handle) -> RunArtifacts`) and teach the
run loop to submit every owned cell first, then collect as they finish, keeping strict sequential
semantics for `local`. B is the right shape for "a grid is a batch"; it touches the core pipeline in
`cli.py`, so I would do it only after Phases 0–2 land and with a design note in
`future-experiments.md`. Recommendation: A now, B as its own PR later.

### Design point: 16 simultaneous cells (user decision, 2026-09-04)

The compute environment caps at 32 vCPUs (`sandbox_bootstrap_aws.sh:132`); at 2 vCPU per cell that
is **16 concurrent cells**, and the user has fixed that as the design point rather than O(100).
Aggregation stays host-side and per-process: each cell's artifacts come back through the
`retort run` that submitted it, which scores, judges, archives and commits one `RunResult` row to
the experiment's SQLite (WAL, 30 s busy timeout). Fan-out is `--shard i/N` processes sharing one
`retort.db`, ownership by deterministic hash, no coordination through the DB.

What 16 does and does not require, in order of the limit you would hit:

| concern | at 16 | needed |
|---|---|---|
| Batch capacity | exactly the 32-vCPU cap | nothing; raise `maxvCpus` only with a new design point |
| polling | 16 `aws batch describe-jobs` subprocesses per 15 s ≈ 1/s | nothing; batched poller (Phase 3B) unnecessary |
| SQLite writers | 16 rows landing over minutes | nothing; WAL + busy_timeout already cover it |
| host memory | 16 × full stdout strings (one prime log was 193 MB) | **Phase 0.4** bounded reads |
| host-side scoring | 16 concurrent `go test`/`pytest`/`npm test` on the M4 | **Phase 2** — the only real blocker; without it 16 cells corrupt each other's `build_time` on the host |
| judge | up to 16 concurrent `claude -p` judge calls | pace through a small pool or accept retries; watch the account rate limit on the first 16-wide grid |

Consequence for the phases: **Phase 3 resolves to option A** (a shard driver script that launches
and reaps 16 `retort run --shard` processes). The async `submit`/`collect` protocol extension (3B) is
shelved unless the design point changes. Phases 0.4 and 2 remain the prerequisites for running 16
wide; Phase 1 is consistency work and is not on the scaling path.

### Phase 4 — image reproducibility (~1 day)

One Dockerfile per language with the prime layer as a build stage/arg (instead of `-v4`/`-v3`
files `FROM` a hard-coded digest); `LABEL org.opencontainers.image.revision=<commit>` and
`…source=<repo>`; `ECR_REGISTRY` as a build-arg (removes the account id from the tree); a build script
that appends `{tag, digest, commit, dirty, prime_bundle_sha256, parity}` to a committed
`sandbox/images.lock.json`, which `image_digests` in workspace.yaml is validated against. Multi-arch
deferred — durations never pool across lanes anyway.

### Phase 5 — upstream (after Phases 0–2, and after asking Q1)

Revised decomposition: **A → C → B → F-reader** unchanged and independent; **D depends on C** and is
cut from a branch with the prime branch stripped (or **E-local lands first** and D follows E); D
ships with Phases 0–1 in, not the current shape — a reviewer reading `sandbox_runner.py` today sees
copied `LocalRunner` code and an unverified digest. Docs conflicts only on rebase. Ask adrianco Q1
(does he want an AWS dependency at all) *before* investing in D's PR polish; the answer changes
whether D is a PR or a documented fork feature.

### Order and effort

| phase | days | unblocks |
|---|---:|---|
| 0 fail-closed | 1 | trustworthy runs now; upstream footgun issue |
| 1 one source of truth | 2–3 | `prompt`/`effort` factors on the lane; claude-code and csharp lanes become branch-free |
| 2 authoritative in-container scores | 1 | host contention gone; honest `build_time` |
| 4 image reproducibility | 1 | D PR prerequisite |
| 3 parallelism | 0.5 (A) / 2–3 (B) | wide grids without operator scripts |
| 5 upstream | per PR | — |

Phases 0, 1 and 4 are independent of each other and can be separate PRs onto this fork's `main`.

---

## 4. Decisions I am assuming (say if any is wrong)

1. **Goal includes upstream eventually, but fork trustworthiness comes first.** Phases 0–2 are
   worth doing even if adrianco never takes D.
2. **In-container scores should become authoritative for the sandbox lane** (Phase 2). The
   alternative — keep host scoring, accept host `build_time` — keeps the lane's timing claims soft.
3. ~~Parallelism: sharding stays for now; the protocol extension is a later, separate decision.~~
   **Decided 2026-09-04: 16 concurrent cells is the design point; sharding + a driver script is
   the mechanism; the protocol extension is shelved.**
4. **Keep the name `sandbox`; retire `RunnerType.cloud`** (or make it a deprecation error) rather
   than renaming — `cloud` already means "hosted model" in upstream's data.
5. **The prime-log fix is "drop `message_update` at write time"**, not "keep the last delta" — the
   parser never needed them.
