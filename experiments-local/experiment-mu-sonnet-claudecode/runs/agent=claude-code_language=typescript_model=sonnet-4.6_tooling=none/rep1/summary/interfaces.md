# Interfaces

## HTTP routes

(none — stdio MCP server)

## MCP tools

| Tool | Inputs | Returns | Handler |
|------|--------|---------|---------|
| search_matches | team, home_team, away_team, opponent, season, competition, date_from, date_to, limit | formatted match list | `index.ts` case "search_matches" → `query-engine.ts:searchMatches` |
| get_team_stats | team (req), season, competition, home_only, away_only | W/D/L, goals, points, win rate | `getTeamStats` |
| head_to_head | team1, team2 (req), season, competition, limit | H2H record + recent matches | `headToHead` |
| get_standings | season (req), competition (default Brasileirao) | computed league table | `getStandings` |
| search_players | name, nationality, club, position, min_overall, max_age, limit | player list sorted by Overall | `searchPlayers` |
| get_global_stats | competition | totals, avg goals/match, home win rate | `getGlobalStats` |
| get_biggest_wins | limit, competition | matches sorted by goal margin | `getBiggestWins` |
| get_extended_match_stats | team (req), limit | shots/corners rows from BR-Football dataset | `getExtendedStats` |

## Data schema

In-memory `Database` = `{ matches: NormalizedMatch[], extended: ExtendedMatch[], players: FifaPlayer[] }`.
`NormalizedMatch`: date (ISO string), home_team, away_team, home_goal, away_goal, season, competition, round?, stage?, extra?. Built by concatenating Brasileirão + Copa do Brasil + Libertadores + historical CSVs (no dedup across sources).

## CLI commands

(none)
