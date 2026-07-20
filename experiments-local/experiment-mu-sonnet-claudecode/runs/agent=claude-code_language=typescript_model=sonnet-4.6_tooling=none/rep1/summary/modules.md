# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/index.ts | MCP server entrypoint: loads data at startup, registers 8 tools over stdio | `server`, tool handlers for `search_matches`, `get_team_stats`, `head_to_head`, `get_standings`, `search_players`, `get_global_stats`, `get_biggest_wins`, `get_extended_match_stats` |
| src/data-loader.ts | CSV loading (csv-parse/sync) for all 6 Kaggle files, team-name normalization, unified match model | `loadBrasileiraoMatches()`, `loadCupMatches()`, `loadLibertadoresMatches()`, `loadExtendedMatches()`, `loadHistoricalMatches()`, `loadFifaPlayers()`, `normalizeTeam()`, `teamMatches()`, `buildNormalizedMatches()` |
| src/query-engine.ts | Pure query/aggregation functions over the in-memory `Database` | `searchMatches()`, `getTeamStats()`, `headToHead()`, `getStandings()`, `searchPlayers()`, `getGlobalStats()`, `getBiggestWins()`, `getExtendedStats()` |
| src/types.ts | TypeScript interfaces for raw CSV rows, `NormalizedMatch`, `FifaPlayer`, `TeamStats` | `NormalizedMatch`, `FifaPlayer`, `TeamStats`, `ExtendedMatch`, per-CSV row types |
| src/tests/data-loader.test.ts | Loader + normalization unit tests | 10 test functions |
| src/tests/query-engine.test.ts | Query-function tests against the real CSV data | 24 test functions |
