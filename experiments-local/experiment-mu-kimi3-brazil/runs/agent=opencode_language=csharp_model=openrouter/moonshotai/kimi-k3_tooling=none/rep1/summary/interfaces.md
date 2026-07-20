# Interfaces

## HTTP routes

(none — the server speaks JSON-RPC over stdio, not HTTP)

## MCP protocol methods (JSON-RPC over stdio)

| Method | Returns | Handler |
|--------|---------|---------|
| initialize | protocolVersion 2024-11-05, capabilities, serverInfo, instructions | `McpServer.cs:HandleInitialize` |
| ping | `{}` | `McpServer.cs:HandleMessage` |
| tools/list | 11 tool schemas | `ToolRegistry.cs:ListTools` |
| tools/call | `{content:[{type:text,...}], isError}` | `ToolRegistry.cs:CallTool` |
| notifications/* | (no response) | `McpServer.cs:HandleMessage` |

## MCP tools

| Tool | Purpose | Handler |
|------|---------|---------|
| find_matches | Matches by team/opponent/competition/season/date range/round | `ToolRegistry.cs:HandleFindMatches` |
| head_to_head | Recent meetings + all-time W/D/L between two teams | `ToolRegistry.cs:HandleHeadToHead` |
| team_statistics | W/D/L, goals for/against, win rate (season/competition/venue filters) | `ToolRegistry.cs:HandleTeamStatistics` |
| team_competitions | Competitions a team has played in | `ToolRegistry.cs:HandleTeamCompetitions` |
| season_standings | League table computed from results; champion + relegation tags | `ToolRegistry.cs:HandleSeasonStandings` |
| search_players | FIFA players by name/nationality/club/position/min rating | `ToolRegistry.cs:HandleSearchPlayers` |
| top_players | Highest-rated players with filters | `ToolRegistry.cs:HandleTopPlayers` |
| match_statistics | Avg goals/match, home/draw/away rates, biggest wins | `ToolRegistry.cs:HandleMatchStatistics` |
| biggest_wins | Largest-margin victories | `ToolRegistry.cs:HandleBiggestWins` |
| find_derbies | Matches between 16 hardcoded traditional rivalries | `ToolRegistry.cs:HandleFindDerbies` |
| list_datasets | Loaded CSVs with row counts and coverage | `ToolRegistry.cs:HandleListDatasets` |

## CLI commands

`BrazilianSoccerMcp [--data-dir <path>]` — data dir falls back to `BRAZILIAN_SOCCER_DATA_DIR` env var, then upward directory discovery of `data/kaggle`.

## Data schema

Unified `MatchRecord`: date, season, competition (5 canonical names), round/stage, home/away team (raw + canonical), goals, source file. `PlayerRecord`: name, age, nationality, overall, potential, club, position, jersey number. Loaded from the 6 provided CSVs; cross-file duplicates (same pair + competition, dates within 2 days) removed.
