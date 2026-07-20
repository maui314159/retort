# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/BrazilianSoccerMcp/Program.cs | Entry point: locate data dir, load data, build graph, run stdio MCP server | `Program.Main`, `ResolveDataDir` |
| src/BrazilianSoccerMcp/Mcp/McpServer.cs | JSON-RPC 2.0 line-delimited MCP server over stdio | `McpServer`, `HandleMessage`, `RunAsync` |
| src/BrazilianSoccerMcp/Tools/ToolRegistry.cs | MCP tool surface: 13 tools over the five required query categories | `ToolRegistry`, `ToolDef`, `Tools` |
| src/BrazilianSoccerMcp/Graph/KnowledgeGraph.cs | In-memory knowledge graph of teams/players/competitions/seasons/matches | `KnowledgeGraph`, `ResolveTeam`, `Stats` |
| src/BrazilianSoccerMcp/Data/DataLoader.cs | Loads the five kaggle CSVs into a unified `LoadResult` | `DataLoader.Load`, `LoadResult` |
| src/BrazilianSoccerMcp/Data/CsvParser.cs | Hand-rolled RFC-4180-ish CSV parser | `CsvParser.Load`, `Parse`, `CsvTable` |
| src/BrazilianSoccerMcp/Data/Models.cs | Unified `Match` record (all 5 sources) + FIFA `Player` record | `Match`, `Player` |
| src/BrazilianSoccerMcp/Data/TeamNameNormalizer.cs | Team-name canonicalization + cross-file alias table (state suffixes etc.) | `Normalize`, `CanonKey` |
| src/BrazilianSoccerMcp/Data/FlexibleDateParser.cs | Parses ISO and Brazilian date formats from CSVs and query filters | `Parse`, `ParseFilter` |
| src/BrazilianSoccerMcp/Services/MatchQueryService.cs | Match filtering/search + competition-name resolution | `MatchQueryService`, `MatchFilter`, `Find`, `Count`, `ResolveCompetition` |
| src/BrazilianSoccerMcp/Services/TeamAnalyticsService.cs | Team records, head-to-head, standings (3/1/0), biggest wins, competition stats | `TeamAnalyticsService`, `GetTeamRecord`, `GetHeadToHead`, `GetStandings`, `GetBiggestWins`, `GetCompetitionStats` |
| src/BrazilianSoccerMcp/Services/PlayerQueryService.cs | Player search/aggregation over the FIFA dataset | `PlayerQueryService`, `Search`, `GetClubPlayers`, `GetTopPlayers`, `GetBrazilianClubSummary` |
| tests/BrazilianSoccerMcp.Tests/TestData.cs | Shared test fixtures/helpers | (helper, 0 tests) |
| tests/BrazilianSoccerMcp.Tests/*.cs (12 files) | xUnit feature tests per area: CSV parsing, date parsing, name normalization, data loading, match/player queries, head-to-head, standings, team/competition stats, cross-file joins, MCP protocol | 68 Fact/Theory tests total |

Test file breakdown: McpProtocolFeatureTests (10), PlayerQueryFeatureTests (9), MatchQueryFeatureTests (7), CrossFileFeatureTests (6), DataLoadingFeatureTests (6), CompetitionStatsFeatureTests (5), CsvParserTests (5), StandingsFeatureTests (5), TeamStatsFeatureTests (5), TeamNameNormalizerTests (4), FlexibleDateParserTests (3), HeadToHeadFeatureTests (3).
