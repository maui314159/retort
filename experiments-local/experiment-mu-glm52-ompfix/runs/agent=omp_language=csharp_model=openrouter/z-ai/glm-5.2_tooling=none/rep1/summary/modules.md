# Modules

Task surface (from `TASK.md`): an MCP (Model Context Protocol) server exposing a
query interface over six bundled Kaggle CSV datasets of Brazilian soccer data —
five match files (Brasileirão, Copa do Brasil, Libertadores, an extended-stats
file, and a 2003–2019 historical file) and one FIFA player file. The server must
answer match, team, player, competition, and statistical-aggregate questions,
normalizing team-name variants ("Palmeiras-SP" vs "Palmeiras"), multiple date
formats, and UTF-8 Portuguese text.

## Source

| Path | Purpose | Entry points |
|------|---------|--------------|
| `src/BrazilianSoccerMcp/Program.cs` | Top-level-statement host: stdio MCP server, logging routed to stderr, `SoccerDataService` registered as a singleton, tools discovered via `WithToolsFromAssembly()` | (implicit `Main`) |
| `src/BrazilianSoccerMcp/Tools/MatchTools.cs` | MCP tool class for match, team-stats, and head-to-head queries | `MatchTools`, `FindMatches`, `GetTeamStats`, `CompareTeams` |
| `src/BrazilianSoccerMcp/Tools/SoccerTools.cs` | MCP tool class for player, competition, and aggregate-statistics queries | `SoccerTools`, `SearchPlayers`, `GetClubPlayers`, `GetStandings`, `GetChampion`, `GetAggregateStats`, `GetBiggestVictories`, `ListTeams` |
| `src/BrazilianSoccerMcp/Services/SoccerDataService.cs` | In-memory data store: CsvHelper loaders for all six CSVs, unified `Match` normalization, plus query/aggregate methods | `SoccerDataService`, `EnsureLoaded()`, `Matches`, `Players`, `MatchesForTeam()`, `HeadToHead()`, `StatsForTeam()`, `Standings()`, `BiggestVictories()`, `AllTeams()`, `DisplayName()`, `ResolveTeamKey()`, `ParseInt()`, `ParseDate()` |
| `src/BrazilianSoccerMcp/Services/TeamNameNormalizer.cs` | Collapses team-name spellings to a canonical key (lowercased, accent-stripped, punctuation-free, state/country suffix removed) | `TeamNameNormalizer`, `StripSuffix()`, `CanonicalKey()` |
| `src/BrazilianSoccerMcp/Services/DataPathResolver.cs` | Walks upward from `AppContext.BaseDirectory` (then CWD) to locate `data/kaggle` | `DataPathResolver`, `ResolveDataDirectory()` |
| `src/BrazilianSoccerMcp/Models/Match.cs` | Unified match record across the five match datasets, with computed result/goal properties and a `Summary` line | `Match`, `HomeWin`, `AwayWin`, `Draw`, `TotalGoals`, `GoalDifference`, `Summary` |
| `src/BrazilianSoccerMcp/Models/Player.cs` | Subset of FIFA player columns (~14 of ~75 retained) | `Player`, `Summary` |
| `src/BrazilianSoccerMcp/Models/TeamStats.cs` | Computed W/D/L + goal record, and the standings row type | `TeamStats`, `Points`, `WinRate`, `GoalsPerMatch`, `Format()`, `StandingsEntry` |
| `src/BrazilianSoccerMcp/BrazilianSoccerMcp.csproj` | net10.0 exe; CsvHelper 33.1.0, Microsoft.Extensions.Hosting 10.0.10, ModelContextProtocol 1.4.1 | — |
| `BrazilianSoccerMcp.slnx` | Solution file linking the src and test projects | — |

## Tests

| Path | Purpose | Entry points |
|------|---------|--------------|
| `tests/BrazilianSoccerMcp.Tests/MatchQueryBddTests.cs` | Given/When/Then scenarios for match search, season/competition filters, name normalization, recency | `MatchQueryBddTests` — 6 `[Fact]` |
| `tests/BrazilianSoccerMcp.Tests/TeamStatsBddTests.cs` | Scenarios for team stats, home/away partition, 2019 standings/champion, head-to-head, biggest victories | `TeamStatsBddTests` — 6 `[Fact]` |
| `tests/BrazilianSoccerMcp.Tests/PlayerQueryBddTests.cs` | Scenarios for FIFA player search by name/nationality/club/position/rating | `PlayerQueryBddTests` — 10 `[Fact]`/`[Theory]` |
| `tests/BrazilianSoccerMcp.Tests/McpToolOutputBddTests.cs` | Scenarios asserting the formatted string output of the MCP tool methods | `McpToolOutputBddTests` — 10 `[Fact]`/`[Theory]` |
| `tests/BrazilianSoccerMcp.Tests/AssemblyInfo.cs` | Disables xUnit parallelization (`CollectionPerAssembly`, `DisableTestParallelization = true`) | assembly attribute |
| `tests/BrazilianSoccerMcp.Tests/BrazilianSoccerMcp.Tests.csproj` | net10.0 test project; xunit 2.9.3, Microsoft.NET.Test.Sdk 17.14.1, coverlet.collector 6.0.4 | — |

Approx. 1,100 LOC across 10 source files; approx. 820 LOC across 5 test files
(32 test methods). `bin/`, `obj/`, and `data/` are excluded per instruction.
