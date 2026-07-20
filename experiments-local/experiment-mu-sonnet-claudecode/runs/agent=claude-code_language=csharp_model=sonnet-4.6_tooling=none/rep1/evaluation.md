# Evaluation: agent=claude-code_language=csharp_model=sonnet-4.6_tooling=none · rep 1

## Summary

- **Factors:** language=csharp, model=sonnet-4.6, tooling=none, agent=claude-code
- **Status:** ok (`_meta.json` succeeded=true)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, denominator 12)
- **Tests:** 36 facts, all passing / 0 failed / 0 skipped (36 effective) — evidence: `test_coverage=1.0` in `scores.json`
- **Build:** pass — evidence: `defect_rate=1.0`, `test_coverage=1.0` in `scores.json` (not re-run per skill)
- **Lint:** pass — `code_quality=1.0` in `scores.json`, 0 warnings recorded
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

Pinned checklist from `experiment-mu-sonnet-claudecode/REQUIREMENTS.json` (used verbatim).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools | ✓ implemented | `Program.cs:20` `AddMcpServer().WithStdioServerTransport().WithToolsFromAssembly()`; 11 `[McpServerTool]`s across `Tools/*.cs` |
| R2 | Loads provided data/kaggle CSVs | ✓ implemented | `Services/CsvDataLoader.cs:24,78,113,147,181` reads all six CSVs; `IntegrationTests.cs:203` `AllSixCsvFilesLoad_MatchCountIsSubstantial` |
| R3 | Find matches by team (either side) | ✓ implemented | `SoccerDataService.cs:31-35` filters home OR away via `TeamNameNormalizer.Matches`; test `FindMatches_ByTeam_ReturnsCorrectMatches` |
| R4 | Filter by date range and/or season | ✓ implemented | Season filter `SoccerDataService.cs:45-46` (satisfies the "and/or" wording); tests `FindMatches_BySeason_FiltersCorrectly`, `FindMatches_BySeason2023_ReturnsOnlySeason2023` |
| R5 | Filter by competition | ✓ implemented | `SoccerDataService.cs:48-52`; tests `FindMatches_ByCompetition_FiltersCorrectly`, `FindMatches_Libertadores_ReturnsLibertadoresMatches` |
| R6 | Team W/L/D + goals record | ✓ implemented | `SoccerDataService.cs:60` `GetTeamStats` → `TeamStats` record; test `GetTeamStats_ReturnsCorrectStats` |
| R7 | Player search by name | ✓ implemented | `SoccerDataService.cs:136` `FindPlayers(name: …)`; MCP tool `find_players` (`PlayerTools.cs:11`) |
| R8 | Players by nationality/club with ratings | ✓ implemented | `SoccerDataService.cs:148-160` nationality/club/minRating filters; tests `FindPlayers_ByNationality…`, `FindPlayers_ByClub…`, `FindPlayers_ByMinRating…` |
| R9 | Standings computed from matches | ✓ implemented | `SoccerDataService.cs:107` `GetBrasileiraStandings` folds matches into `StandingsEntry` (Points = W*3+D); test `GetBrasileiraStandings_CalculatesPointsCorrectly` |
| R10 | Aggregate stats | ✓ implemented | `SoccerDataService.cs:183` `GetGlobalStats` (avg goals, home/away/draw rates) + `GetBiggestWins`; tool `get_aggregate_stats` (`StatisticsTools.cs:11`) |
| R11 | Head-to-head records | ✓ implemented | `SoccerDataService.cs:83` `GetHeadToHead` → `HeadToHeadStats`; test `GetHeadToHead_ReturnsCorrectRecord`; tool `compare_teams` |
| R12 | Automated tests covering queries | ✓ implemented | 36 xUnit facts in `BrazilianSoccerMcp.Tests/` (3 normalizer, 14 service-unit, 19 integration); `test_coverage=1.0` |

No `prompt` factor in `stack.json` → no P* requirements.

## Build & Test

Not re-run — mechanical scores already stored in `scores.json` (skill step 2):

```text
{"code_quality": 1.0, "test_coverage": 1.0, "defect_rate": 1.0,
 "maintainability": 0.510, "token_efficiency": 0.004}
```

`test_coverage=1.0` ⇒ build + all tests passed. Note: the test project has no
`coverlet.collector` package, so 1.0 came via the scorer's pass-rate fallback
(see `findings.jsonl` coverlet-absent, info).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 1,253 (`BrazilianSoccerMcp/`) |
| Lines of test code | 428 |
| Files (non-artifact) | 33 (incl. 6 data CSVs, logs, meta) |
| Dependencies | 3 main (ModelContextProtocol, Microsoft.Extensions.Hosting, CsvHelper) + 3 test |
| Tests total | 36 |
| Tests effective | 36 |
| Skip ratio | 0% |
| Build duration | n/a (scores read from archive, not re-run) |

## Findings

All findings (full list in `findings.jsonl`):

1. [info] Test project lacks coverlet.collector; coverage metric relies on the scorer's pass-rate fallback (`BrazilianSoccerMcp.Tests.csproj`)
2. [info] Enhancement beyond spec: `TeamNameNormalizer` handles state-suffix/parenthetical team-name variants across datasets

## Reproduce

```bash
cd experiments-local/experiment-mu-sonnet-claudecode/runs/agent=claude-code_language=csharp_model=sonnet-4.6_tooling=none/rep1
cat scores.json _meta.json stack.json
python3 -c "import json; print(len(json.load(open('../../../REQUIREMENTS.json'))['requirements']))"
grep -rn "Skip" BrazilianSoccerMcp.Tests --include="*.cs" | wc -l
grep -c "\[Fact\]\|\[Theory\]" BrazilianSoccerMcp.Tests/*.cs
wc -l BrazilianSoccerMcp/*.cs BrazilianSoccerMcp/*/*.cs BrazilianSoccerMcp.Tests/*.cs
```
