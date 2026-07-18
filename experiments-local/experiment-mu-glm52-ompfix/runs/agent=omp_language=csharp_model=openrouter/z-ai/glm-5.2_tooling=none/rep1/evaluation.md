# Evaluation: agent=omp language=csharp model=openrouter/z-ai/glm-5.2 tooling=none · rep 1

## Summary

- **Factors:** language=csharp, model=openrouter/z-ai/glm-5.2, agent=omp, tooling=none
- **Status:** ok — passes the mechanical gate, with correctness defects in the aggregation queries
- **Requirements:** 9/12 implemented, 3 partial (R6, R9, R11), 0 missing
- **Tests:** 45 passed / 0 failed / 0 skipped (45 effective)
- **Build:** pass — from `test_coverage=0.9479` in `retort.db` (tests executed, so the build succeeded)
- **Lint:** pass — `code_quality=1.0` in `retort.db`, 0 warnings
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 3 high, 2 medium)

The run is a genuine, working MCP server: it builds, all 45 tests pass, nothing is
skipped, and lint is clean. The three `partial` requirements share **one root cause** —
the six bundled CSVs are loaded into a single flat match list with no deduplication,
and the Serie A seasons 2014–2022 exist in three of those files at once. Every
aggregation over an unscoped match set is therefore inflated by up to 3x. This is a
data-modelling miss, not a harness false-failure: it burned 35 minutes and $1.88 of
model time and produced a complete, compiling, tested implementation.

**A note on grading.** The pinned `REQUIREMENTS.json` `how_to_verify` for R6/R9/R11
asks only that the tool *returns* aggregated W/L/D, or that standings are *computed*
from matches rather than hardcoded — read literally, all three pass. I graded them
`partial` because each requirement's numeric output is materially wrong (standings
built from 1712 matches instead of 380; head-to-head reporting 6 meetings instead of
2), and a query tool that returns confidently wrong numbers has not delivered the
capability. A reviewer applying `how_to_verify` strictly would score 12/12; the
evidence for either reading is in `findings.jsonl`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools | ✓ implemented | `Program.cs:31-33` `AddMcpServer().WithStdioServerTransport().WithToolsFromAssembly()`; `[McpServerToolType]` on `Tools/MatchTools.cs:21`, `Tools/SoccerTools.cs:16` |
| R2 | Loads datasets in `data/kaggle/` | ✓ implemented | `Services/SoccerDataService.cs:52-57` loads all six CSVs; `Services/DataPathResolver.cs` resolves the dir |
| R3 | Match query by team (home/away/either) | ✓ implemented | `Tools/MatchTools.cs:41-50` → `SoccerDataService.cs:295-299` `MatchesForTeam` |
| R4 | Filter by date range and/or season | ✓ implemented | `Tools/MatchTools.cs:54-59` — `season`, `fromDate`, `toDate` filters (header formatting bug filed separately) |
| R5 | Filter by competition | ✓ implemented | `Tools/MatchTools.cs:52-53`; labels assigned at `SoccerDataService.cs:80` (Brasileirão), `:107` (Copa do Brasil), `:132` (Copa Libertadores) |
| R6 | Team W/L/D + goals for/against | ~ partial | `SoccerDataService.cs:312-344` `StatsForTeam` — correct shape, but counts each real fixture up to 3x (no dataset dedup) |
| R7 | Search players by name | ✓ implemented | `Tools/SoccerTools.cs:34-35` name filter over `LoadFifaPlayers` data (`SoccerDataService.cs:216-267`) |
| R8 | Filter players by nationality/club with ratings | ✓ implemented | `Tools/SoccerTools.cs:36-45` nationality/club/position/minOverall, sorted by `Overall`; `GetClubPlayers` at `:55` |
| R9 | Season standings computed from results | ~ partial | `SoccerDataService.cs:347-382` computes points/positions from matches (not hardcoded), but `:353` `Contains()` merges Série A/B/C + historical and triple-counts Serie A |
| R10 | Aggregate stats | ✓ implemented | `Tools/SoccerTools.cs:104-131` avg goals/match, home vs away win rate; `:133` `GetBiggestVictories` |
| R11 | Head-to-head between two teams | ~ partial | `SoccerDataService.cs:302-309` + `Tools/MatchTools.cs:105-135` — returns W/L/D, but 6 meetings where the truth is 2 |
| R12 | Automated tests covering the queries | ✓ implemented | 45 xunit tests across 4 BDD files; `test_coverage=0.9479` (tests execute) |

## Build & Test

Per the skill, build/test/lint were **not** re-run — the stored scorer results stand in.

```text
scores.json / retort.db (experiments-local/experiment-mu-glm52-ompfix/retort.db)
code_quality       1.0
test_coverage      0.9479      → tests executed; build + all tests passed
defect_rate        1.0         → build + test succeeded
maintainability    0.7303
token_efficiency   0.0027
_duration_seconds  2116.5
_cost_usd          1.8793
_tokens            9,227,771
```

```text
dotnet test (as recorded by the agent, _agent_stdout.log)
Passed!  - Failed: 0, Passed: 45, Skipped: 0, Total: 45, Duration: 4 s - BrazilianSoccerMcp.Tests.dll (net10.0)
```

Skip scan found **0** skipped or disabled tests (`grep -rE "Skip\s*=|\[Fact\(Skip|\[Theory\(Skip" tests/`).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (C#, source only) | 1223 (+455 comment, 14 files) |
| Files (excl. bin/obj/data/logs) | 29 |
| Dependencies | 7 PackageReference (CsvHelper 33.1.0, ModelContextProtocol 1.4.1, Microsoft.Extensions.Hosting 10.0.10; xunit 2.9.3, xunit.runner.visualstudio 3.1.4, Microsoft.NET.Test.Sdk 17.14.1, coverlet.collector 6.0.4) |
| Tests total | 45 |
| Tests effective | 45 |
| Skip ratio | 0% |
| Wall-clock duration | 2116.5s |
| Cost | $1.88 |

Note: `coverlet.collector` **is** present in the test csproj, so this run is not an
instance of the known C# coverlet scorer false-failure — the 0.9479 coverage is real.

## Findings

All 5 (full detail in `findings.jsonl`):

1. **[high] R9** — Standings merge Série A/B/C and triple-count overlapping datasets: `Standings('Brasileirão', 2019)` aggregates 1712 matches instead of 380.
2. **[high] R6** — Team W/L/D and goals for/against inflated ~3x by duplicate source datasets.
3. **[high] R11** — Head-to-head reports 6 Flamengo–Palmeiras meetings in 2019; the true answer is 2.
4. **[medium]** — `FindMatches` header always prints `from 0001-01-01 | to 0001-01-01`: `TryParse` into a non-nullable `DateTime` leaves `MinValue`, and the implicit `DateTime?` conversion makes `HasValue` always true (`Tools/MatchTools.cs:56-59,82-83`).
5. **[medium]** — MCP tool output tests assert shape, not values, which is why the standings defect passes. Ironically the regex `\d{4}-\d{2}-\d{2}` in `McpToolOutputBddTests.cs:44` is satisfied by the bogus `0001-01-01` from finding 4.

Findings 4 and 5 are code defects rather than requirement gaps; the skill's `kind`
vocabulary has no plain "bug" bucket, so they are filed as `lint_warning`.

## Reproduce

```bash
cd "experiments-local/experiment-mu-glm52-ompfix/runs/agent=omp_language=csharp_model=openrouter/z-ai/glm-5.2_tooling=none/rep1"

# Stored scores (no re-run of build/test/lint)
cat scores.json
sqlite3 -readonly ../../../../retort.db \
  "SELECT rr.metric_name, rr.value FROM run_results rr JOIN experiment_runs er ON er.id=rr.run_id
   WHERE json_extract(er.run_config_json,'\$.language')='csharp' AND er.replicate=1 AND er.status='completed';"

# Skip scan
grep -rnE "Skip\s*=|\[Fact\(Skip|\[Theory\(Skip" tests/ --include="*.cs"

# Agent's own test result
grep -aoE "Passed!.*" _agent_stdout.log | tail -1

# Dataset overlap that grounds findings 1-3 (2019 Flamengo v Palmeiras appears in all three files)
grep -c "" data/kaggle/Brasileirao_Matches.csv data/kaggle/BR-Football-Dataset.csv data/kaggle/novo_campeonato_brasileiro.csv

# Metrics
cloc . --exclude-dir=bin,obj,data,node_modules
```
