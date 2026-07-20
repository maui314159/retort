# Interfaces

## HTTP routes

(none)

## MCP tools (stdio transport, FastMCP)

| Tool | Description | Handler |
|------|-------------|---------|
| find_matches | Matches by team/opponent/competition/season/date-range/venue/stage | `query_engine.py:find_matches` |
| head_to_head | All matches between two teams + W/D/L balance | `query_engine.py:head_to_head` |
| team_statistics | W/D/L, goals for/against, win rate; per-competition breakdown | `query_engine.py:team_statistics` |
| list_teams | Team names, optionally by competition/season | `query_engine.py:list_teams` |
| search_players | FIFA players by name/nationality/club/position/min_overall | `query_engine.py:search_players` |
| top_players | Highest-rated players with filters | `query_engine.py:top_players` |
| player_profile | Best-match single player profile + skill ratings | `query_engine.py:player_profile` |
| competition_standings | League table computed from results (3/1/0, tie-breaks) | `query_engine.py:competition_standings` |
| top_scoring_teams | Teams ranked by goals scored | `query_engine.py:top_scoring_teams` |
| list_competitions | Competitions with season coverage + match counts | `query_engine.py:list_competitions` |
| biggest_wins | Largest goal-margin matches | `query_engine.py:biggest_wins` |
| best_team_records | Teams by points-per-game (home/away filter) | `query_engine.py:best_team_records` |
| competition_overview | Matches, avg goals/match, home/draw/away win rates | `query_engine.py:competition_overview` |

## CLI commands

`python server.py` — runs the MCP server on stdio (no subcommands).

## Data schema

In-memory pandas tables built from `data/kaggle/`:
- `matches`: date, season, competition, home_team, away_team, home_goals, away_goals, round, stage, venue, source, home_key, away_key (5 CSV sources unified; `played_matches` is the deduped played subset).
- `players`: FIFA CSV columns plus derived `name_key`, `club_key`, `club_team_key`, `nationality_key`.
