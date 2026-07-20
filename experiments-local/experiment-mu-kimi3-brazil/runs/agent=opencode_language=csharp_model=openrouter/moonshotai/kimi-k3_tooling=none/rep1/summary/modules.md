# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/BrazilianSoccerMcp/Program.cs | Entry point: resolve data dir, load CSVs, start stdio MCP server | top-level `Main` (`--data-dir` flag) |
| src/BrazilianSoccerMcp/Mcp/McpServer.cs | JSON-RPC 2.0 over stdio; initialize/ping/tools/list/tools/call | `McpServer`, `RunAsync()`, `HandleMessage()` |
| src/BrazilianSoccerMcp/Mcp/JsonRpc.cs | JSON-RPC message construction/serialization + error codes | `JsonRpc.Result`, `JsonRpc.Error`, `Serialize` |
| src/BrazilianSoccerMcp/Tools/ToolRegistry.cs | Defines the 11 MCP tools, arg parsing, answer formatting | `ToolRegistry`, `ListTools()`, `CallTool()` |
| src/BrazilianSoccerMcp/Data/DataLoader.cs | Loads all 6 Kaggle CSVs into unified records; cross-file dedup | `DataLoader.LoadAll()`, `ResolveDataDirectory()` |
| src/BrazilianSoccerMcp/Data/CsvParser.cs | RFC-4180-style CSV parser (quotes, escapes, CRLF, UTF-8) | `CsvParser.Parse` |
| src/BrazilianSoccerMcp/Data/TeamNameNormalizer.cs | Canonicalizes team names (state suffixes, accents, aliases) | `CanonicalName()`, `NormalizeKey()` |
| src/BrazilianSoccerMcp/Models/MatchRecord.cs | Unified match record (date, teams, goals, competition, source) | `MatchRecord`, `MatchResult`, `Describe()` |
| src/BrazilianSoccerMcp/Models/PlayerRecord.cs | FIFA player record | `PlayerRecord`, `Describe()` |
| src/BrazilianSoccerMcp/Services/SoccerDataService.cs | Query engine: matches, team stats, H2H, standings, players, aggregates, derbies | `SoccerDataService`, `FindMatches`, `GetTeamStatistics`, `HeadToHead`, `GetStandings`, `SearchPlayers`, `GetMatchStatistics` |
| tests/BrazilianSoccerMcp.Tests/CsvParserTests.cs | CSV parser edge cases | 7 test functions |
| tests/BrazilianSoccerMcp.Tests/TeamNameNormalizerTests.cs | Name normalization cases | test functions (theories) |
| tests/BrazilianSoccerMcp.Tests/SoccerDataServiceTests.cs | Query engine on synthetic fixtures | 17 test functions |
| tests/BrazilianSoccerMcp.Tests/McpServerTests.cs | Protocol-level tests (in-process JSON-RPC) | 10 test functions |
| tests/BrazilianSoccerMcp.Tests/RealDataIntegrationTests.cs | Spec sample questions against the real CSVs | 26 test functions |
| tests/BrazilianSoccerMcp.Tests/McpEndToEndTests.cs | Spawns the built server, speaks MCP over stdio | 1 end-to-end test |
