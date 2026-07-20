# Interfaces

## HTTP routes

(none — this is a stdio MCP server, not an HTTP service)

## MCP tools

| Tool | Inputs (zod schema) | Returns | Handler |
|------|--------------------|---------|---------|
| `search_matches` | `team?`, `team2?`, `competition?`, `season?`, `date_from?`, `date_to?`, `limit?` | `{matches[], total}` sorted by date desc | `server.ts:18` → `tools.ts:searchMatches` |
| `get_team_stats` | `team`, `competition?`, `season?` | `TeamStats` (W/L/D, goals for/against, points, win rate) | `server.ts:50` → `tools.ts:getTeamStats` |
| `head_to_head` | `team1`, `team2`, `competition?` | `HeadToHeadResult` (per-team wins, draws, recent matches) | `server.ts:71` → `tools.ts:headToHead` |
| `search_players` | `name?`, `nationality?`, `club?`, `position?`, `min_overall?`, `limit?` | player list with ratings/attributes | `server.ts:98` → `tools.ts:searchPlayers` |
| `get_standings` | `competition?`, `season` | ranked points table computed from match results | `server.ts:126` → `tools.ts:getStandings` |
| `get_top_stats` | `stat` (biggest wins / averages / home records), `competition?`, `season?` | aggregate statistics record | `server.ts:148` → `tools.ts:getTopStats` |

## Library API

`tools.ts` exports the six query functions above as plain functions; `dataLoader.ts` exports `loadAllMatches()`, `loadFifaPlayers()`, `normalizeTeamName()`, `teamsMatch()`, `clearCache()`. Tests call these directly, bypassing the MCP layer.

## Data schema

`NormalizedMatch`: datetime, season, competition, home_team, away_team, home_goals, away_goals (unified across `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `BR-Football-Dataset.csv`, `novo_campeonato_brasileiro.csv`).
`FifaPlayer`: name, nationality, club, position, overall rating + attributes from `fifa_data.csv`.
