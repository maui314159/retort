# Interfaces

MCP server over stdio (`ModelContextProtocol` 0.3.0-preview.2, `WithStdioServerTransport` + `WithToolsFromAssembly`, Program.cs:28-31). All tools return formatted text.

| MCP tool | Parameters | Description |
|----------|-----------|-------------|
| `search_matches` | team, season, competition, fromDate, toDate, homeTeam, awayTeam, limit | Match search across all 5 match CSVs (capped at 50 rows) |
| `get_head_to_head` | team1, team2, season?, competition? | W/L/D + goals + recent matches between two teams |
| `get_team_stats` | team, season?, competition?, homeOnly? | W/D/L, points, goals for/against, win rate, per-match averages |
| `get_standings` | season, competition="Brasileirão" | League table computed from match results (pts, GD, GF tiebreaks) |
| `search_players` | name, nationality, club, position, minRating, limit | FIFA dataset search, sorted by Overall desc |
| `get_biggest_wins` | competition?, season?, team?, limit | Largest goal-margin victories |
| `get_competition_summary` | competition?, season? | Match/goal totals, home-win %, top scoring teams |
| `get_team_competitions` | team | Competitions + season ranges a team appears in |
| `get_season_list` | — | Inventory of competitions/seasons/match+player counts |
| `get_top_teams` | season?, competition?, limit | Teams ranked by points then goal difference (≥3 matches) |

## Data schemas

- `Match`: date, home/away team + goals, season, competition, round, stage, states, arena
- `Player`: FIFA attributes (Overall, Potential, Club, Position, skill ratings, GK ratings)
- `TeamStats`: aggregate with computed `Points = 3W + D`, `WinRate`, `GoalDiff`
