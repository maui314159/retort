# Evaluation: agent=opencode_language=csharp_model=openrouter/moonshotai/kimi-k3_tooling=none · rep 1

## Summary

- **Factors:** agent=opencode, language=csharp, model=openrouter/moonshotai/kimi-k3, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned REQUIREMENTS.json, constant denominator)
- **Tests:** 102 passed / 0 failed / 0 skipped (102 effective)
- **Build:** pass — from stored scores (defect_rate=1.0, test_coverage>0 ⇒ build + tests ran); not re-run
- **Lint:** pass — code_quality=1.0 from scores.json; 0 warnings
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

Scores were read from `scores.json` (inline gate artifact) and cross-checked against `retort.db` run_id=10 (identical values); build/test/lint were **not** re-run per skill policy. test_coverage=0.8286 is line coverage from coverlet — the agent log shows `Passed! - Failed: 0, Passed: 102, Skipped: 0, Total: 102`, so the test gate is fully green.

## Requirements

Pinned checklist from `experiments-local/experiment-mu-kimi3-brazil/REQUIREMENTS.json` (12 items). No `prompt` factor in stack.json, so there are no P* requirements.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `src/BrazilianSoccerMcp/Mcp/McpServer.cs` (JSON-RPC 2.0 stdio: initialize/ping/tools/list/tools/call, protocol 2024-11-05); `Tools/ToolRegistry.cs` registers 11 tools; `McpServerTests`, `McpEndToEndTests.GivenServerProcess_WhenClientSpeaksMcp_ThenToolsAnswerOverStdio` |
| R2 | Loads and uses data/kaggle CSVs | ✓ implemented | `Data/DataLoader.cs:26-75` loads all 6 required files; `RealDataIntegrationTests.GivenCsvFiles_WhenLoaded_ThenAllSixDatasetsAreQueryable` |
| R3 | Matches by team (home/away/either) | ✓ implemented | `Services/SoccerDataService.cs:113-149 FindMatches` (team/opponent, either side); `FindMatches_ByTeam_ReturnsHomeAndAwayFixtures` |
| R4 | Filter by date range and/or season | ✓ implemented | `SoccerDataService.cs:137-142` (Season, From, To); `FindMatches_ByDateRange_FiltersCorrectly`, `GivenMatchData_WhenSearchingByDateRange_ThenRespectsTheWindow` |
| R5 | Filter by competition | ✓ implemented | `SoccerDataService.cs:74-91 ResolveCompetition` (Brasileirão A/B/C, Copa do Brasil, Libertadores synonyms); `FindMatches_ByCompetitionAndSeason_FiltersCorrectly` |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `SoccerDataService.cs:185-213 GetTeamStatistics` (venue filter too); `GetTeamStatistics_ComputesWinDrawLossAndGoals`, `GivenMatchData_WhenRequestingCorinthiansHomeRecord2022_ThenReturnsNineteenHomeMatches` |
| R7 | Player search by name | ✓ implemented | `SoccerDataService.cs:380-402 SearchPlayers` (case-insensitive substring); `GivenFifaData_WhenSearchingNeymar_ThenReturnsThePlayer` |
| R8 | Players by nationality/club with ratings | ✓ implemented | `SoccerDataService.cs:386-396` (nationality, club, position, min_overall), `TopPlayers`; `SearchPlayers_ByNationalityAndClub_FiltersAndSortsByRating`, `GivenFifaData_WhenFilteringGremioPlayers_ThenReturnsSquad` |
| R9 | Season standings computed from matches | ✓ implemented | `SoccerDataService.cs:302-366 GetStandings` (points/W/D/L/GF/GA, tie-breaks, per-season source selection); `GivenMatchData_WhenRequesting2019Standings_ThenFlamengoAreChampions`, `..._2003Standings_ThenCruzeiroAreChampions` |
| R10 | Aggregate stats (avg goals, home vs away, biggest wins) | ✓ implemented | `SoccerDataService.cs:435-474 GetMatchStatistics`/`BiggestWins`; `GetMatchStatistics_ComputesAveragesAndWinRates`, `GivenMatchData_WhenRequestingBiggestWins_ThenMarginsAreDescending` |
| R11 | Head-to-head between two teams | ✓ implemented | `SoccerDataService.cs:227-258 HeadToHead`; `head_to_head` tool; `HeadToHead_SummarizesAllTimeRecord`, `GivenMatchData_WhenComparingPalmeirasAndSantos_ThenReturnsHeadToHeadSummary` |
| R12 | Automated tests covering the queries | ✓ implemented | 6 test files, 102 test cases, 0 skipped, all passing (test_coverage=0.8286 > 0); `RealDataIntegrationTests` exercises the spec's sample questions against the real CSVs |

**Enhancements beyond spec:** `find_derbies` (16 hardcoded rivalries), `team_competitions`, `biggest_wins`, `list_datasets` tools; cross-file fixture deduplication; team-name ambiguity errors with candidate suggestions; UTF-8/accent-insensitive resolution (`GivenAccentedNames_WhenResolvingWithoutAccents_ThenStillMatches`); Brazilian DD/MM/YYYY date parsing verified (`GivenHistoricalData_WhenQueryingOldSeasons_ThenBrazilianDateFormatWasParsed`).

## Build & Test

Not re-run (skill policy: stored scores stand in).

```text
Stored scores (scores.json, = retort.db run_id=10):
  code_quality     = 1.0     (lint clean)
  test_coverage    = 0.8286  (coverlet line coverage; tests all pass)
  defect_rate      = 1.0     (build + test succeeded)
  maintainability  = 0.6164
  token_efficiency = 0.0094
```

```text
dotnet test (from _agent_stdout.log, final runs):
Passed!  - Failed: 0, Passed: 102, Skipped: 0, Total: 102, Duration: ~950 ms - BrazilianSoccerMcp.Tests.dll (net10.0)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, *.cs) | 2,043 |
| Lines of test code (*.cs) | 1,197 |
| Files (excl. build artifacts/logs) | 34 |
| Dependencies | 0 runtime NuGet packages (4 test-only: coverlet.collector, Microsoft.NET.Test.Sdk, xunit, xunit.runner.visualstudio) |
| Tests total | 102 |
| Tests effective | 102 |
| Skip ratio | 0% |
| Run duration (agent) | 2,279 s |
| Tokens / cost | 5,473,162 tokens / $3.19 |

## Findings

Top 3 by severity (full list in `findings.jsonl`):

1. [low] Line coverage 82.86% — untested paths remain (all tests pass; coverage shortfall only)
2. [info] Tools beyond spec: find_derbies, team_competitions, biggest_wins, list_datasets
3. [info] Cross-file fixture deduplication (±2-day window) beyond spec

## Reproduce

```bash
cd "experiments-local/experiment-mu-kimi3-brazil/runs/agent=opencode_language=csharp_model=openrouter/moonshotai/kimi-k3_tooling=none/rep1"
cat scores.json
sqlite3 -readonly ../../../../retort.db "SELECT metric_name, value FROM run_results WHERE run_id=10;"
grep -aoE "(Passed!|Failed!)[^\"]*" _agent_stdout.log | tail -2
grep -c '\[Fact\]\|\[Theory\]' tests/BrazilianSoccerMcp.Tests/*.cs
```
