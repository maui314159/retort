# Evaluation: agent=omp_language=csharp_model=openrouter/z-ai/glm-5.2_tooling=none · rep 2

## Summary

- **Factors:** language=csharp, model=openrouter/z-ai/glm-5.2, agent=omp, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, denominator fixed at 12)
- **Tests:** 53 passed / 0 failed / 0 skipped (53 effective)
- **Build:** pass — from stored scores (`defect_rate=1.0`), not re-run
- **Lint:** pass — `code_quality=1.0` from `scores.json`; no compiler warnings in the agent log
- **Architecture:** `summary/` not generated — the `run-summary` skill was not invoked (time budget); structure is described inline below
- **Findings:** 8 items in `findings.jsonl` (0 critical, 1 high, 3 medium, 3 low, 1 info)

Scores read from `{run_dir}/scores.json` — build/test/lint were **not** re-run:

| Metric | Value |
|--------|-------|
| `test_coverage` | 0.8584 |
| `code_quality` | 1.0 |
| `defect_rate` | 1.0 |
| `maintainability` | 0.6381 |
| `token_efficiency` | 0.0026 |

`test_coverage=0.8584` (> 0) means the suite executed; `defect_rate=1.0` means build + tests
succeeded. The agent log corroborates: `Passed! - Failed: 0, Passed: 53, Skipped: 0, Total: 53`.
This is line coverage, not a pass rate — coverlet ran, so this run is **not** an instance of the
known C# coverlet false-fail mode.

## Requirements

Assessed against the pinned checklist; IDs and text are verbatim from `REQUIREMENTS.json`.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools | ✓ implemented | `src/BrazilianSoccerMcp/Program.cs:32-34` `AddMcpServer().WithStdioServerTransport().WithTools<SoccerTools>()`; 11 `[McpServerTool]` methods in `Tools/SoccerTools.cs` |
| R2 | Loads datasets in `data/kaggle/` | ✓ implemented | `Data/SoccerDataStore.cs:48-57` loads all 6 CSVs; test `Given_all_six_datasets_when_loaded_then_each_is_queryable` asserts every dataset is non-empty |
| R3 | Match query by team (home/away/either) | ✓ implemented | `SoccerQueryService.cs:52-57` filters home OR away; tool `search_matches` (`SoccerTools.cs:40`). See `norm-1`/`norm-2` — works, but the normalizer has edge-case defects |
| R4 | Filter by date range and/or season | ✓ implemented | `SoccerQueryService.cs:46-51` (`season`, `fromDate`, `toDate`); test `Given_match_data_when_filtering_by_season_2022_...` covers season. Date-range path is implemented but not directly tested |
| R5 | Filter by competition | ✓ implemented | `SoccerQueryService.cs:44-45` + `ParseCompetition` (`SoccerTools.cs:320`) spans all 5 match datasets; test `Given_match_data_when_filtering_by_competition_...` |
| R6 | Team W/L/D record and goals for/against | ✓ implemented | `SoccerQueryService.cs:111-139` `GetTeamStatistics`; tool `team_statistics`; tests `Given_match_data_when_requesting_palmeiras_stats_2022_...`, `..._home_venue_...` |
| R7 | Player search by name | ✓ implemented | `SoccerQueryService.cs:255-260` accent-insensitive name contains; test `Given_fifa_data_when_searching_neymar_then_finds_regardless_of_accent` |
| R8 | Players by nationality/club, with ratings | ✓ implemented | `SoccerQueryService.cs:261-282`; output carries `Overall` (`SoccerTools.cs:217`); tests for Brazil nationality, Santos club, position, min-overall |
| R9 | Season standings computed from matches | ✓ implemented | `SoccerQueryService.cs:145-189` accumulates 3/1/0 from match results, sorts by pts→GD→GF; test `Given_standings_when_computed_then_points_equal_3w_plus_d` proves it is derived, not hardcoded |
| R10 | Aggregate statistics | ✓ implemented | `GetGoalsOverview` (`SoccerQueryService.cs:206`) avg goals/match + home/away/draw rates; `GetBiggestWins` (`:232`); tests assert averages reasonable and biggest-wins ordering |
| R11 | Head-to-head between two teams | ✓ implemented | `SoccerQueryService.cs:76-105` `GetHeadToHead`; tool `head_to_head`; tests `..._head_to_head_palmeiras_santos_then_totals_match`, `..._both_teams_appear` |
| R12 | Automated tests covering query capabilities | ✓ implemented | 5 BDD test files, 34 `[Fact]`/`[Theory]` attributes → 53 executed cases, 0 skipped; `test_coverage=0.8584` |

No requirement is `partial` or `missing`: every `how_to_verify` in the pinned checklist is satisfied
with executing test evidence. The defects in `findings.jsonl` are quality issues *within* satisfied
requirements (the checklist has no team-name-normalization requirement), so they are filed as
defects rather than requirement failures.

**Enhancements beyond spec (not deductions):** extended BR-Football stats on the `Match` model,
`list_competitions`/`list_seasons`/`list_teams` discovery tools, and a home/away venue filter.

## Build & Test

Not re-run — stored scores used, per the skill's Step 2. Evidence from `_agent_stdout.log`:

```text
dotnet test
Passed!  - Failed:     0, Passed:    53, Skipped:     0, Total:    53, Duration: 3 s
          - BrazilianSoccerMcp.Tests.dll (net10.0)
```

The only verification I ran was a read-only probe of the shipped `TeamNameNormalizer.cs`, compiled
in a temp directory outside `run_dir` (see Reproduce), to ground-truth findings `norm-1`/`norm-2`:

```text
Athletic Club MG         -> ''
Ind. Santa Fe            -> 'ind. santa'
Botafogo - PB            -> 'botafogo'
Botafogo - RJ            -> 'botafogo'
TeamMatches(cand='Santa Cruz', query='Santa Fe')      = True    <-- wrong club
TeamMatches(cand='Athletic Club MG', query='Athletic Club MG') = False
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 1,402 C# (+41 MSBuild), 15 files |
| Files | 17 (excl. bin/obj) |
| Dependencies | ModelContextProtocol, Microsoft.Extensions.Hosting, CsvHelper, xunit, coverlet |
| Tests total | 53 |
| Tests effective | 53 |
| Skip ratio | 0% |
| Build duration | not measured (build not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. **[high] `norm-1`** — Unguarded 2-letter suffix strip: `NormalizeTeam("Santa Fe")` → `"santa"`,
   so `TeamMatches("Santa Cruz", "Santa Fe")` is `True`. Querying the Colombian club Santa Fe
   (52 rows in `Libertadores_Matches.csv`) silently returns Santa Cruz's matches.
2. **[medium] `norm-2`** — `"Athletic Club MG"` normalizes to `""`; the empty-key guard then makes
   the club unmatchable even against itself (1 row in `BR-Football-Dataset.csv`).
3. **[medium] `norm-3`** — `StateCodes` is declared and never read; it is exactly the guard whose
   absence causes `norm-1` and `norm-2`.
4. **[medium] `tool-1`** — `search_matches`/`search_players` `.Take(limit)` before reading `.Count`,
   so the header under-reports the number of matches found.
5. **[low] `h2h-1`** — `head_to_head` prints a total that includes unscored matches next to W/D/L
   tallies that exclude them, so the numbers do not sum.

Note on taxonomy: the skill's allowed `kind` values have no generic "defect", so the logic bugs
above are filed as `lint_warning` — the closest available fit. They are code defects, not linter
output (`code_quality=1.0`, no compiler warnings).

## Reproduce

```bash
cd experiments-local/experiment-mu-glm52-ompfix/runs/agent=omp_language=csharp_model=openrouter/z-ai/glm-5.2_tooling=none/rep2

# Stored scores (build/test/lint NOT re-run)
cat scores.json
grep -oE "Passed!.*" _agent_stdout.log | tail -1

# Skips and test counts
grep -rnE "Skip\s*=|\[Ignore" tests/ --include="*.cs"      # -> none
grep -rhoE "\[Fact\]|\[Theory\]" tests/ --include="*.cs" | wc -l

# Dead-code root cause of norm-1/norm-2
grep -rn "StateCodes" src/ --include="*.cs"                # -> declaration only

# Normalizer ground-truth (temp copy; run_dir untouched)
T=$(mktemp -d); mkdir -p $T/probe/Data
cp src/BrazilianSoccerMcp/Data/TeamNameNormalizer.cs $T/probe/Data/
# + minimal net10.0 console csproj calling NormalizeTeam/TeamMatches on the labels above
cd $T/probe && dotnet run
```
