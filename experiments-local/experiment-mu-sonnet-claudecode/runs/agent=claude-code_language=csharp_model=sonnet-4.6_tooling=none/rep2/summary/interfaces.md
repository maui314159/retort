# Interfaces

## HTTP routes

(none — MCP server over stdio transport)

## MCP tools (13)

| Tool | Params (key ones) | Returns | Handler |
|------|-------------------|---------|---------|
| SearchMatches | team, opponent, competition, season, dateFrom, dateTo, limit | formatted match list | `MatchTools.cs:25` |
| GetHeadToHead | team1, team2, competition, limit | W/D/L + goals + recent matches | `MatchTools.cs:88` |
| GetStandings | season, competition | points table (P/W/D/L/GF/GA/GD/Pts) | `MatchTools.cs:147` |
| SearchPlayers | name, nationality, club, position, minOverall, maxAge, limit | player list with ratings | `PlayerTools.cs:17` |
| GetTopPlayers | nationality, club, position, limit | ranked players by Overall | `PlayerTools.cs:72` |
| GetBrazilianClubPlayers | nationality | players grouped by club with avg rating | `PlayerTools.cs:127` |
| GetTeamStats | team, season, competition, homeAwayBreakdown | W/D/L, GF/GA, points, win rate | `TeamTools.cs:23` |
| CompareTeams | team1, team2, season | H2H + side-by-side overall records | `TeamTools.cs:96` |
| GetTeamCompetitions | team | competitions + seasons participated | `TeamTools.cs:161` |
| GetBiggestWins | competition, season, limit | largest goal-difference matches | `StatsTools.cs:23` |
| GetCompetitionStats | competition, season | goals/match, home/away/draw rates, per-season breakdown | `StatsTools.cs:70` |
| GetTopTeams | criteria (goals/wins/undefeated/home/away), competition, season, limit | ranked team table | `StatsTools.cs:129` |
| GetDataSummary | — | dataset counts by competition, season range | `StatsTools.cs:203` |

All tools return human-readable formatted strings (StringBuilder), not JSON.

## Data schema

In-memory only (no DB). `MatchRecord`: Competition, HomeTeam/AwayTeam (+normalized), HomeGoal/AwayGoal (int?), Date (DateTime?), Season (int?), Round, Stage. `PlayerRecord`: Id, Name, Age, Nationality, Overall, Potential, Club, Position, physical + 13 skill stats.

CSV sources (all in `data/kaggle/`): Brasileirao_Matches, Brazilian_Cup_Matches, Libertadores_Matches, BR-Football-Dataset, novo_campeonato_brasileiro, fifa_data.
