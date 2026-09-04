# Cloud execution (SandboxRunner) — handoff and upstream-contribution plan

**Status:** built, validated, and in production use on this fork. Not yet offered upstream.
**Audience:** whoever picks up the harness work, and — for the sections marked *upstream* — adrianco.
**Written:** 2026-09-04. **Fork state at writing:** `main` is 21 commits ahead of `upstream/main`, 24 behind.

This document exists so that harness work can be handed off independently of experiment
execution. Everything below was verified against the code and the run archives on the date
shown, not recalled. Where a claim is inferred rather than observed it is marked
**[HYPOTHESIS]**; direct observations are **[DIRECT]**.

---

## 1. What this is, and why it exists

`SandboxRunner` (`src/retort/playpen/sandbox_runner.py`, 590 lines) implements the existing
`PlaypenRunner` protocol against **AWS Batch on Fargate**: one experiment cell = one ephemeral
container. It exists because API-model experiments are API-bound, yet retort's
one-experiment-at-a-time rule serialises them — wall-clock is a first-class response and a
shared machine corrupts it. Moving a cell into its own environment dissolves that contention,
and with it a recurring family of environment bugs (playpen-path refusals, global-config
leakage, orphan processes).

**Scope is deliberately narrow: API-model experiments only.** The local oMLX spine cannot move
and is unaffected.

Components:

| file | lines | role |
|---|---:|---|
| `src/retort/playpen/sandbox_runner.py` | 590 | the runner: provision → execute → teardown |
| `scripts/sandbox_bootstrap_aws.sh` | 186 | one-time ECR repo, S3 bucket, Batch queue, IAM roles |
| `sandbox/entrypoint.sh` | 176 | in-container: pull workspace, run agent, score, push artifacts |
| `sandbox/parity_check.py` | 161 | rescore an archived local workspace in-container, compare |
| `sandbox/score_full.py` / `score_gate.py` | 59 / — | in-container scoring entry points |
| `sandbox/Dockerfile.*` | — | per-language images (see §3) |

Design choices worth preserving: it shells out to the `aws` CLI rather than taking a boto3
dependency; wall-clock is measured **in-container** on a monotonic clock so provisioning and
queue time are recorded separately and never folded into `duration`; scorers run
**in-container**, because otherwise `build_time` stops being comparable.

### Validation evidence (all [DIRECT])

- All four pre-registered §0c smokes passed: S3 artifact round-trip; agent reaches OpenRouter
  from inside the container with a secret-hygiene grep; in-container timing separated from job
  span; **scorer parity** — an archived local workspace rescored in-container matches its local
  scores.
- A real `retort run --config` drive on Fargate with zero host-side fixes; 2/2 cells judged
  `requirement_coverage` 1.0.
- In-container stall watchdog live-verified: 60 s window, kill at 60.1 s, `kill_reason=stall`
  surfaced exactly like the local guard.
- Shard/resume semantics proven over Batch with zero duplicate submissions.
- Shakedown agreed with the local lane 3/3.
- Parity checking caught **three would-be false-zero bugs** before they could touch a result.
- First production family (`exp-mu-primeagent`, 24 runs, 3 languages, 2 tasks) ran on this lane
  — see [past-experiments](past-experiments.md).

**Standing rule, load-bearing:** never pool `duration` / `build_time` across runner lanes. Lane
is a provenance field. Pass rates are comparable; timings are not.

---

## 2. Prior art: there was never a cloud runner upstream

Checked across upstream's full history, not just its current tree.

- Files ever added under `src/retort/playpen/`: `local_runner.py`, `docker_runner.py`,
  `metaharness_runner.py`, `graphify_hook.py`, `repo_pr.py`, `runner.py`, `stack_reload.py`,
  `swiftlet_shim.py`, `task_loader.py`, `toolchains.py`, `prompt_builder.py`. **Nothing cloud,
  batch, Fargate, Modal, E2B or remote — ever added, and none deleted** (the only file ever
  removed from `playpen/` was `prompt_builder.py`, in the M1 dead-code pass).
- **Naming trap:** `cloud/` directories in upstream experiment data (e.g.
  `experiments/adrianco/experiment-49-versions/cloud/`) mean *the model was a hosted API model*,
  with execution still local. That is a different axis from execution locus.

### `DockerRunner` is not prior art, and is a live footgun

`docker_runner.py` is 211 lines, essentially untouched since Phase 1 (`a853aaee`, 2026-04-10).
When `docker` is not on PATH, `execute()` falls through to `_simulate_run()`, which sleeps 10 ms
and returns **random** metrics:

```python
exit_code=0 if random.random() > 0.1 else 1,
token_count=random.randint(500, 5000),
```

And `RunnerType.docker` is the **schema default** (`config/schema.py:292`), with `cli.py`
constructing a `DockerRunner` for it — yet **all 76 of upstream's own experiment
`workspace.yaml` files set `runner: local`.** Zero use the default.

> ***upstream:*** this is worth a small issue independent of everything else — the default
> runner path, taken on a machine without Docker, silently yields simulated results with random
> token counts and a 10% random failure rate. It should fail closed. It is not a hypothetical
> for a newcomer who runs `retort init` and then `retort run`.

`SandboxRunner` does **not** build on `DockerRunner`: no import, no subclassing, no reuse. The
only occurrence of "docker" in `sandbox_runner.py` is a docstring line noting the shared
subprocess-over-SDK choice. Given `_simulate_run`, not inheriting was correct.

---

## 3. Image versioning — what `v2` / `v3` actually mean

**They are ECR image *tag generations*, not versions of a Dockerfile.** The `retort-sandbox` ECR
repo is immutable, so every rebuild must push a new tag. `Dockerfile.python`'s own header states
the contract:

> *"The ECR repo is IMMUTABLE: each rebuild pushes a NEW tag (python-v2, python-v3, …) and
> registers a new job-definition revision."*

The **digest** is the tuning parameter. It is passed as
`SandboxRunner(image_digests={...})`, recorded at `sandbox_runner.py:352` as
`sandbox_image_digest`, and lands in every run's provenance. The tag is a human label for
"which rebuild".

Lineage as committed:

- **python** — one file edited in place across generations (`a399e2d4` → `12f3719c` → `cd151cea`,
  whose header now says build as `python-v3`). `Dockerfile.python-v4` then layers prime-agent
  **on top of** the v3 digest. **This chain is complete from source.**
- **go / typescript** — created once (`12ed60ee`), headers still say `go-v1` / `typescript-v1`.
  But `Dockerfile.go-v3` builds `FROM` a digest it describes as **go-v2**, and `71b90cbf` refers
  to "v2 scoring bases". No committed change corresponds to that generation.

### The actual defect: image identity depends on a commit nobody records

`Dockerfile.go:18-22` (and its siblings) build retort itself from the worktree:

```dockerfile
FROM python:3.12-slim AS wheel
COPY pyproject.toml README.md* ./
COPY src ./src
RUN pip wheel --no-deps --no-build-isolation -w /wheels .
```

So **image identity = (Dockerfile, source commit)**. [HYPOTHESIS] `go-v2` is `Dockerfile.go`,
unchanged, rebuilt against a later worktree carrying the undecodable-file scorer fix — nothing
needed to change in the Dockerfile for a new generation to exist. This is more insidious than a
missing file: the recipe is present, but the commit it was built from is recorded nowhere.
Provenance captures *which* image ran, not *how to rebuild it*.

**Fix (small, and a hard prerequisite for the PR):** stamp the build commit into the image —
`LABEL org.opencontainers.image.revision` or a build-arg — and record it in provenance beside
the digest. Then digest → commit → exact rebuild.

**Open task:** determine which commit each in-use digest corresponds to. Digests used by the
`exp-mu-primeagent` grid:

| language | digest |
|---|---|
| python | `sha256:f59c3b0b9a8adcc0e18a781ab1bc7041d6a6e063f69385686a85fdfb9a6e72b0` |
| go | `sha256:27dddbf657430b8ae6e54cd6faa31f9dc9c3c5b0bc3f537ee6a75e7488cbdbaf` |
| typescript | `sha256:e002fd8ebe2090b83f6f7014b6689b2e1051699454616fcee54d0dfca1e7e980` |

### Should the local and cloud image builds be unified?

In principle yes; the target is **one recipe per language, buildable from source, pinned by
digest, multi-arch**. Two caveats:

1. **Do not unify on `DockerRunner`'s images.** It names *mutable* stock tags
   (`python:3.12-slim`, `node:20-slim`, `golang:1.22-bookworm`, …). A mutable tag is an
   unrecorded tuning parameter that moves under you — the exact failure the project's first
   principle exists to prevent. Note our v1 images already start `FROM python:3.12-slim`, so the
   lineage does converge at the bottom; the divergence is the agent/scorer/toolchain layers,
   which is precisely what `DockerRunner` never solved.
2. **Architecture is a real obstacle.** Sandbox images build `--platform linux/amd64` for
   Fargate; the dev host is arm64 (M4 Max). One shared image means emulation — which corrupts
   wall-clock, a first-class response — or a multi-arch manifest. Multi-arch is correct but is
   genuine work, and the cross-lane rule means durations never pool anyway.

Priority: close the rebuild gap (§3) before unifying (§3 last). Unifying with `DockerRunner` is
cosmetic — it is simulating code that 0 of 76 upstream workspaces select.

---

## 4. Known defects and rough edges

1. **Image rebuild provenance** — §3. Blocker for upstream.
2. **Two mechanisms select a runner.** `SandboxRunner` is *not* in `runner.py`'s registry (which
   still holds only `docker`, `local`, `metaharness` at lines 198–200); selection is a direct
   branch at `cli.py:854` → import → construct at `872`. Defensible — the constructor needs a
   `SandboxSpec` the zero-arg registry pattern cannot supply — but a reviewer will notice. Either
   register a factory or state the rationale in the PR.
3. **Hard-coded AWS account id.** The account number appears in `sandbox/Dockerfile.*` `FROM`
   lines and in docs. **Parameterise before any upstream PR.**
4. **Unbounded log reads.** `agent_consulted()` (`local_runner.py:1337`) and the diagnose
   classifier (`cli.py:279`) call `read_text()` on the whole `_agent_stdout.log`; only the
   live-context reader (`cli.py:173`) is bounded, at `read_bytes()[-400_000:]`. With prime-agent
   producing 193 MB logs this is a memory hazard, not a style nit — on a machine whose memory
   ceiling already voided exp-62's rust grid.
5. **Log volume at source.** See §5.
6. **Remaining before broader use:** claude-code on the lane (needs an API-key billing decision),
   live-triggered second chance on Fargate, and a `csharp` image.

---

## 5. The large-log problem, with the measurement

prime-agent's `--mode json` emits the full event stream. One brazil run's `_agent_stdout.log` is
**193 MB**; two exceeded GitHub's 100 MB per-file limit, so the data branch could not be pushed
raw. Breakdown of that file (41,451 events) [DIRECT]:

| event | count | MB |
|---|---:|---:|
| `message_update` | 31,515 | **172.3** |
| `tool_execution_update` | 9,207 | 17.6 |
| everything else | 729 | 3.4 |

Each `message_update` is a **full snapshot of the accumulating message**, re-emitted as it grows
— hence an 88× gzip ratio. **Do not naively drop them:** `stopReason`, `usage` and `cost` appear
*only* on `message_update`, never on `message_end`, so dropping them breaks `_parse_prime_usage`
and destroys failure evidence.

**Safe filter, measured on the real file:** buffer `message_update`, flush the last one when
`message_end` arrives. **193.3 MB → 21.8 MB (11.3%)**, retaining all 91 terminal deltas with
usage/cost/stop-reason and final content intact.

**Interim archive convention (already applied to the data branch, commit `85b3b2ed`):** stdout
logs over 1 MB are stored as `_agent_stdout.log.gz` — 708 MB → 8.8 MB, verified byte-identical.
**The working tree keeps them uncompressed on purpose**, because the readers in §4.4 open the
file by exact name with no `.gz` branch. After a fresh clone of the data branch, `gunzip -k`
before rescoring.

Recommended order: (a) make readers `.gz`-aware and bounded — cheapest, and it retires the
worktree/branch divergence; (b) filter deltas at write time — the 89% win, and it stops the
problem recurring; (c) keep gzip as the backstop. **Do not truncate or drop logs** — they are the
evidence that identified the `exp-mu-primeagent` zero-write failure.

---

## 6. Upstream contribution plan

Convention: outside contributors send **code-only** PRs. `experiments-local/`, `master-local.*`
and the `data/maui-experiments` branch never go upstream, and that branch must never be a PR base.

| | PR | size | depends on | conflict |
|---|---|---|---|---|
| **A** | provenance: tolerate Hermes ≥0.20 mapping-style `model:` key | 1 file, +8/−1 | — | none |
| **B** | scorer robustness (undecodable-file fix, 6 scorers) | 7 files, +73/−10 | — | `test_coverage.py` |
| **C** | opencode `model_options` (OpenRouter provider pin) + authoritative `OPENCODE_CONFIG` | 3 files, +61/−1 | — | none |
| **D** | **SandboxRunner** — the lane, images, bootstrap, in-container scoring | 15 files, **+2257** | — | `cli.py` (+35) |
| **E** | prime-agent harness — *splits*: local lane (`schema.py` + `local_runner.py`, +198) is independent; sandbox half (+62, `Dockerfile.python-v4`) needs D | — | E-sandbox → D | none |
| **F** | log handling — *splits*: reader fix standalone; delta filter needs E | — | F-filter → E | none |

**A, B, C and F-reader are independently useful to upstream even though they have no sandbox
lane**: A fixes a Hermes version he is running; C is the provider pin that produced the
`exp-mu-glm53-provider` result; B hardens local-lane scorers; F-reader fixes unbounded reads
regardless of which agent wrote the log.

**Suggested order:** A → C → B → F-reader (small, independently reviewable, shrink the rebase
surface), then D on its own thread, then E, then F-filter.

**Before anything: rebase on `upstream/main`** (24 behind). Conflicts are confined to `cli.py`
(D's wiring vs his graphify-guard move) and `test_coverage.py` (B vs his `go test`-at-module-root
fix) — small but real, and B's is in a file whose behaviour affects our go results.

### Questions for adrianco, worth asking *before* the D PR

1. **Do you want an AWS dependency in retort at all?** The project's spine is one local machine,
   and nothing in five months of history suggests you wanted execution to leave it. This may land
   better as an offer — here is the runner, the parity harness, and evidence it agrees with the
   local lane 3/3 — than as a fait accompli. It is additive: `runner: local` is untouched.
2. **Provider neutrality.** The provision/execute/collect seam was kept deliberately
   provider-neutral so an Azure Container Apps Jobs backend could follow. Is that worth keeping,
   or is one backend cleaner?
3. **The `DockerRunner` default** (§2) — fix it, remove it, or leave it?
4. **Image distribution.** Our images live in our ECR. Upstream use would need either a public
   registry or a documented build-your-own path. The Dockerfiles build from source, so
   build-your-own is viable once §3's commit-stamping lands.

---

## 7. How to verify these claims yourself

```bash
git fetch upstream
git log --oneline upstream/main..main                    # what we have that upstream doesn't
git diff --name-only main...upstream/main                # what upstream has that we don't
git log upstream/main --diff-filter=A --name-only \
    --format="" -- 'src/retort/playpen/*' | sort -u      # every runner ever added upstream
git grep -h "runner:" upstream/main -- '*/workspace.yaml' | sort | uniq -c
grep -in docker src/retort/playpen/sandbox_runner.py     # the single docstring mention
```

Related: [§0c in future-experiments](future-experiments.md) (the pre-registered methodology and
its IN USE status), [past-experiments](past-experiments.md) (`exp-mu-primeagent`, the first
production family on this lane).
