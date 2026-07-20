# Codebase summary — BrazilianSoccerMcp (csharp · sonnet-4.6 · claude-code · rep1)

Two-project .NET 10 solution (`BrazilianSoccerMcp.sln`): an MCP server executable and an xUnit test project.

## Modules

- **`BrazilianSoccerMcp/Program.cs`** — host entrypoint. `Host.CreateApplicationBuilder` + `AddMcpServer().WithStdioServerTransport().WithToolsFromAssembly()` (ModelContextProtocol 1.4.1). Console logging routed to stderr so stdout stays clean for the stdio transport. `SoccerDataService` registered as a singleton loaded once from disk.
- **`DataPathFinder.cs`** — walks up from the working directory to locate `data/kaggle/`.
- **`Services/CsvDataLoader.cs`** (~200 LOC) — CsvHelper-based loaders for all six Kaggle CSVs (`Brasileirao_Matches`, `Brazilian_Cup_Matches`, `Libertadores_Matches`, `BR-Football-Dataset`, `novo_campeonato_brasileiro`, `fifa_data`), each mapped into the shared `UnifiedMatch` model plus `FifaPlayer`.
- **`Services/SoccerDataService.cs`** (~260 LOC) — the query core over in-memory lists: `FindMatches` (team1/team2/season/competition/limit), `GetTeamStats` (W/L/D + goals), `GetHeadToHead`, `GetBrasileiraStandings` (points/GD computed from match results), `FindPlayers` (name/nationality/club/position/minRating), `GetBiggestWins`, `GetGlobalStats` (home/away/draw rates, avg goals). Result shapes are records (`TeamStats`, `HeadToHeadStats`, `StandingsEntry`, `GlobalStats`) with derived properties (Points, WinRate, …).
- **`Services/TeamNameNormalizer.cs`** — normalizes Brazilian team-name variants (state suffixes, parentheticals) so cross-dataset team matching works.
- **`Tools/*.cs`** — five `[McpServerToolType]` classes exposing 11 MCP tools: `find_matches`, `get_recent_matches` (MatchTools); `get_team_stats`, `compare_teams` (TeamTools); `find_players`, `get_top_players_at_club` (PlayerTools); `get_standings`, `find_cup_matches` (CompetitionTools); `get_aggregate_stats`, `get_biggest_wins`, `get_top_scoring_teams` (StatisticsTools). Tools format service results into human-readable strings.

## Flow

stdio MCP request → tool method (constructor-injected `SoccerDataService`) → LINQ query over the in-memory dataset (loaded once at startup from CSV) → formatted string response.

## Tests (`BrazilianSoccerMcp.Tests`, 36 xUnit facts)

- `TeamNameNormalizerTests` — normalization/matching cases.
- `SoccerDataServiceTests` — unit tests on synthetic matches/players for every query path.
- `IntegrationTests` — load the real CSVs and exercise service + tool layers end-to-end (all six files load, standings for 2019 contain Flamengo, etc.).
