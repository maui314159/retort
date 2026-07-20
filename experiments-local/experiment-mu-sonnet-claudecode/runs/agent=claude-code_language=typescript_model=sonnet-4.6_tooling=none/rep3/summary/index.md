# Codebase summary — brazilian-soccer-mcp (rep3)

TypeScript MCP server (stdio transport) over the six bundled Kaggle CSVs, built on
`@modelcontextprotocol/sdk` + `csv-parse`, tested with vitest.

## Modules

| Module | Role |
|--------|------|
| `src/index.ts` | MCP server entrypoint. Registers 14 tools via `ListToolsRequestSchema` / dispatches via `CallToolRequestSchema` switch; per-call errors returned as `isError` text content. Pre-loads data on startup (`getDataStore()`), then connects `StdioServerTransport`. |
| `src/data-loader.ts` | Loads all 6 CSVs into one in-memory `DataStore` (lazy singleton). Per-file loaders normalize the heterogeneous schemas (Brasileirão, Copa do Brasil, Libertadores, BR-Football extended, historical `novo_campeonato_brasileiro`, FIFA players) into common `Match`/`Player` shapes. Also exports `normalizeTeamName` (strips `-SP`-style state suffixes against a real state whitelist) and `teamMatches` (case-insensitive substring match), plus multi-format date parsing (ISO, ISO+time, DD/MM/YYYY). |
| `src/types.ts` | `Match` / `Player` interfaces; `competition` is a closed union (`brasileirao`, `copa_do_brasil`, `libertadores`, `extended`, `historical`). |
| `src/tools/match-tools.ts` | `searchMatches` (team/homeTeam/awayTeam/team2, competition, season, dateFrom/dateTo, limit), `getHeadToHead` (W/D/L + match list between two teams), `getBiggestWins` (largest goal margins). |
| `src/tools/team-tools.ts` | `getTeamStats` (W/L/D, GF/GA, home/away-only), `getStandings` (points table computed from match results), `compareTeams`, `getBestHomeRecord`. |
| `src/tools/player-tools.ts` | `searchPlayers` (name/nationality/club/position/minOverall/maxAge), `getPlayerDetails`, `getTopPlayers`, `getBrazilianPlayersAtBrazilianClubs` (grouped by club with avg rating). |
| `src/tools/stats-tools.ts` | `getAggregateStats` (avg goals/match, home win rate, …), `getSeasonComparison`, `getMostGoals`. |

## Flow

stdio MCP request → `index.ts` switch → tool function → filters over the shared
in-memory `DataStore` arrays → formatted text block returned as MCP text content.
No external network calls; data source is exclusively `data/kaggle/*.csv`.

## Tests

5 vitest files / 77 tests mirroring the tool modules: data-loader normalization +
load integrity, and behavioral tests per tool family (filters, sorting, limits,
head-to-head content, no-result paths). No skipped tests.
