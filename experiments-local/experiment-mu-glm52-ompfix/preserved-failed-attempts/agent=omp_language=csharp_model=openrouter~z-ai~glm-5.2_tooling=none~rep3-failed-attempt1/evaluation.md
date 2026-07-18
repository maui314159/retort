# Evaluation: agent=omp language=csharp model=openrouter/z-ai/glm-5.2 tooling=none · rep 3 (failed-attempt1)

## Summary

- **Factors:** language=csharp, model=openrouter/z-ai/glm-5.2, agent=omp, tooling=none
- **Status:** failed (infrastructure) — agent aborted mid-run; OpenRouter stream stalled (`stream_interrupted_after_content`) and auto-retries failed. Only the empty project scaffold was written.
- **Requirements:** 0/12 implemented, 0 partial, 12 missing
- **Tests:** 0 passed / 0 failed / 0 skipped (0 effective) — no test `.cs` files exist
- **Build:** not meaningfully assessable — 3 empty `.csproj` compile to empty assemblies; `Server` declares `OutputType=Exe` but has no `Program.cs`
- **Lint:** n/a — no source to lint
- **Architecture:** none — empty scaffold, `run-summary` skipped (nothing to summarize)
- **Findings:** 6 items in `findings.jsonl` (3 critical, 3 high)

> **Do not trust this archive's `scores.json`.** It reports `test_coverage=0.7892 / code_quality=1.0 / defect_rate=1.0 / requirement_coverage=1.0`, but those numbers are **carried over from the successful `rep3/` retry** (DB `experiment_runs` id=11, status=completed — same values). This empty archive would rescore `0.0`. This is the known second-try score/archive mismatch.

## What happened

This is the **first attempt** for replicate 3. The omp harness driving GLM-5.2 over OpenRouter died mid-generation:

- `stopReason=error`, `stopDetails.type=stream_interrupted_after_content` — *"OpenAI responses stream stalled while waiting for the next event"*.
- `auto_retry` fired (attempt 1/10) and also errored (*"Was there a typo in the url or port?"*), then `agent_end`.

At abort time the agent had created only the three `.csproj` files and the `.slnx` — no `.cs` implementation, no tests. The run was correctly retried into the sibling **`rep3/`** directory, which succeeded with 10 real `.cs` files (`Program.cs`, `SoccerDataRepository.cs`, `TeamNormalizer.cs`, `Tools/SoccerTools.cs`, `Models.cs`, and 4 test files + `TestBase.cs`) and is the `completed` row in the DB.

**Classification:** GENUINE infrastructure failure (streaming/transport), not a model capability or spec-conformance miss. It failed fast for effectively $0 model work on the aborted attempt — the tell of a harness/infra failure rather than a real spec miss.

## Requirements

Pinned checklist from `REQUIREMENTS.json` (12 items, constant denominator). Every item is **missing** for a single root cause: no source was written before the stream stalled.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server + tools/handlers | ✗ missing | no `Program.cs`/MCP SDK usage; `Server.csproj` Exe with no source |
| R2 | Load provided kaggle CSVs | ✗ missing | `data/kaggle/` present but no `.cs` reads it |
| R3 | Match query by team | ✗ missing | no implementation `.cs` |
| R4 | Match query by date/season | ✗ missing | no implementation `.cs` |
| R5 | Match query by competition | ✗ missing | no implementation `.cs` |
| R6 | Team W/L/D + goals record | ✗ missing | no implementation `.cs` |
| R7 | Player search by name | ✗ missing | no implementation `.cs` |
| R8 | Player filter by nationality/club | ✗ missing | no implementation `.cs` |
| R9 | Standings from match results | ✗ missing | no implementation `.cs` |
| R10 | Aggregate statistics | ✗ missing | no implementation `.cs` |
| R11 | Head-to-head records | ✗ missing | no implementation `.cs` |
| R12 | Automated tests | ✗ missing | test project has 0 test `.cs`; `test_coverage` effective = 0 |

## Build & Test

Not re-run — there is nothing to build or test beyond empty scaffolds. Evidence is from the archive contents and the agent log, not a fresh toolchain run.

```text
# hand-written source (excl obj/ bin/)
find src tests -name '*.cs' -not -path '*/obj/*' -not -path '*/bin/*'  =>  0 files

# agent abort (tail of _agent_stdout.log)
stopReason: error
stopDetails.type: stream_interrupted_after_content
errorMessage: "OpenAI responses stream stalled while waiting for the next event"
auto_retry_start attempt=1 ... -> "Was there a typo in the url or port?" -> agent_end
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source `.cs`, excl obj/bin) | 0 |
| Config/scaffold lines (`.csproj` + `.slnx`) | 56 |
| Hand-written `.cs` files | 0 |
| Tests total | 0 |
| Tests effective | 0 |
| Skip ratio | n/a (0 tests) |
| Build duration | n/a |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [critical] Agent aborted mid-run (OpenRouter stream stall); only empty scaffold written — `_agent_stdout.log`
2. [critical] `scores.json` here is stale — belongs to the successful `rep3/` retry (DB id=11); archive rescores 0.0
3. [critical] R12: no automated tests — test project has zero `.cs`
4. [high] R1: no MCP server implementation — `Server.csproj` Exe with no `Program.cs`
5. [high] R2: no dataset-loading code despite `data/kaggle/` present

## Reproduce

```bash
cd experiments-local/experiment-mu-glm52-ompfix/runs/agent=omp_language=csharp_model=openrouter/z-ai/glm-5.2_tooling=none/rep3-failed-attempt1

# 1. archive has no implementation and no tests
find src tests -name '*.cs' -not -path '*/obj/*' -not -path '*/bin/*' | wc -l   # => 0

# 2. why it failed (stream stall + failed retry)
tail -30 _agent_stdout.log

# 3. scores.json is the retry's numbers, not this archive's
cat scores.json
sqlite3 -readonly ../../../../retort.db \
  "SELECT er.id, er.replicate, er.status, rr.metric_name, rr.value
   FROM experiment_runs er JOIN run_results rr ON rr.run_id=er.id
   WHERE json_extract(er.run_config_json,'\$.language')='csharp'
     AND json_extract(er.run_config_json,'\$.model')='openrouter/z-ai/glm-5.2'
     AND json_extract(er.run_config_json,'\$.tooling')='none' AND er.replicate=3;"

# 4. the successful retry lives here
find ../rep3 -name '*.cs' -not -path '*/obj/*' -not -path '*/bin/*'
```
