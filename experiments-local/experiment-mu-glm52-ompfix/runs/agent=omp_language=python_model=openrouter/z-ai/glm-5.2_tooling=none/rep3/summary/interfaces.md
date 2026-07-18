# Interfaces

## HTTP routes

(none — MCP stdio/SSE transport, no REST surface)

## CLI commands

| Command | Flags | Description |
|---------|-------|-------------|
| `python mcp_server.py` | `--transport {stdio,sse}` (default `stdio`), `--port INT` (default 8000) | Runs the MCP server; eagerly loads the store at startup (`mcp_server.py:278`) |

## MCP tools

| Tool | Args | Returns | Handler |
|------|------|---------|---------|
| `search_matches` | team, opponent, competition, season, start, end, limit | JSON match list | `mcp_server.py:70` |
| `last_match` | team, opponent | JSON match \| `{}` | `mcp_server.py:102` |
| `head_to_head` | team_a, team_b | JSON W/D/L + matches | `mcp_server.py:113` |
| `team_stats` | team, competition, season, venue | JSON W/D/L + goals | `mcp_server.py:128` |
| `team_competitions` | team | JSON comp + counts | `mcp_server.py:144` |
| `standings` | competition, season | JSON ranked table | `mcp_server.py:156` |
| `biggest_wins` | competition, season, limit | JSON win list | `mcp_server.py:167` |
| `average_goals` | competition, season | JSON avg + home-win rate | `mcp_server.py:178` |
| `best_record` | venue, competition, season, limit | JSON ranked teams | `mcp_server.py:188` |
| `derbies` | season, limit | JSON labelled matches | `mcp_server.py:200` |
| `player_search` | name, nationality, club, position, min_overall, limit, sort_by, desc | JSON player list | `mcp_server.py:213` |
| `top_players` | nationality, club, position, limit | JSON player list | `mcp_server.py:236` |
| `brazilians_at_brazilian_clubs` | limit | JSON player list | `mcp_server.py:248` |
| `list_competitions` | — | JSON string list | `mcp_server.py:260` |
| `list_seasons` | competition | JSON int list | `mcp_server.py:267` |

## Data schema

Unified in-memory `matches` DataFrame (`soccer_data.py:_to_unified`, one row per match across 5 match CSVs):
`date` (Timestamp), `home`/`away` (display str), `home_key`/`away_key` (normalized str), `home_goal`/`away_goal` (int|None), `competition` (str), `season` (int|None), `stage` (str), `goal_diff` (int, precomputed).

`players` DataFrame: `fifa_data.csv` verbatim minus unnamed index columns; projected to
`id, name, age, nationality, overall, potential, club, position, jersey_number, height, weight` by `_player_row`.

Team-name registry: `CANONICAL_ALIASES` (variant → canonical key) + `TEAM_DISPLAY` (canonical key → display name), populated by `_register()` at import.
