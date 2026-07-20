# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/BrazilianSoccerMcp/Program.cs | Host bootstrap: DI, MCP server over stdio, data preload | top-level `Main` |
| src/BrazilianSoccerMcp/Models/MatchRecord.cs | Match row model (competition, teams, goals, date, season, round/stage) | `MatchRecord` |
| src/BrazilianSoccerMcp/Models/PlayerRecord.cs | FIFA player row model (ratings, club, position, skill stats) | `PlayerRecord` |
| src/BrazilianSoccerMcp/Services/DataService.cs | Loads all 6 CSVs (CsvHelper) into in-memory lists; per-file column mapping and date/number parsing | `DataService`, `LoadAsync()`, `Matches`, `Players` |
| src/BrazilianSoccerMcp/Services/TeamNameNormalizer.cs | Canonicalizes team names: ~80-entry alias table, state-suffix stripping, fuzzy `Matches()` | `TeamNameNormalizer.Normalize()`, `.Matches()` |
| src/BrazilianSoccerMcp/Tools/MatchTools.cs | MCP tools: match search, head-to-head, standings | `SearchMatches`, `GetHeadToHead`, `GetStandings` |
| src/BrazilianSoccerMcp/Tools/PlayerTools.cs | MCP tools: player search and rankings | `SearchPlayers`, `GetTopPlayers`, `GetBrazilianClubPlayers` |
| src/BrazilianSoccerMcp/Tools/TeamTools.cs | MCP tools: team stats, comparison, competition participation | `GetTeamStats`, `CompareTeams`, `GetTeamCompetitions` |
| src/BrazilianSoccerMcp/Tools/StatsTools.cs | MCP tools: aggregate statistics | `GetBiggestWins`, `GetCompetitionStats`, `GetTopTeams`, `GetDataSummary` |
| tests/BrazilianSoccerMcp.Tests/DataServiceTests.cs | Data-loading integration tests (9 facts) | 9 test methods |
| tests/BrazilianSoccerMcp.Tests/MatchQueryTests.cs | BDD-style match query tests (9 facts) | 9 test methods |
| tests/BrazilianSoccerMcp.Tests/PlayerQueryTests.cs | Player query tests (8 facts) | 8 test methods |
| tests/BrazilianSoccerMcp.Tests/TeamStatsTests.cs | Team/stats tool tests (10 facts) | 10 test methods |
| tests/BrazilianSoccerMcp.Tests/TeamNameNormalizerTests.cs | Normalizer unit tests (8 facts/theories, 14 inline cases) | 8 test methods |
