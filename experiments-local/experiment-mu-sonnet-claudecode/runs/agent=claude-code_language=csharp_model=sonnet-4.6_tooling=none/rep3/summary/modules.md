# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| BrazilianSoccerMcp/Program.cs | Host bootstrap: locates `data/kaggle`, loads DB, starts MCP stdio server | top-level program |
| BrazilianSoccerMcp/Models.cs | Data records | `Match`, `Player`, `TeamStats` (computed `Points`, `WinRate`, `GoalDiff`) |
| BrazilianSoccerMcp/DataLoader.cs | CsvHelper-based loaders for all 6 CSVs; date/int parsing; team-name normalization | `LoadBrasileiraoMatches`, `LoadCupMatches`, `LoadLibertadoresMatches`, `LoadBrFootballDataset`, `LoadHistoricalBrasileirao`, `LoadFifaData`, `NormalizeTeam`, `TeamMatches` |
| BrazilianSoccerMcp/SoccerDatabase.cs | In-memory store + query/aggregation layer | `Initialize`, `SearchMatches`, `CalculateTeamStats`, `GetStandings`, `SearchPlayers` |
| BrazilianSoccerMcp/SoccerTools.cs | The 10 MCP tools ([McpServerToolType]), text-formatted responses | `search_matches`, `get_head_to_head`, `get_team_stats`, `get_standings`, `search_players`, `get_biggest_wins`, `get_competition_summary`, `get_team_competitions`, `get_season_list`, `get_top_teams` |
| BrazilianSoccerMcp.Tests/UnitTest1.cs | xUnit suite: loader unit tests + DB integration tests against real CSVs + tool-output tests | `DataLoaderTests` (2 theories/10 cases), `SoccerDatabaseTests` (20 facts), `SoccerToolsTests` (12 facts) |
