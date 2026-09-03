# Architecture summary

`brazilian_soccer_mcp/` — a Model Context Protocol server over the six bundled
Kaggle CSVs.

| Module | Role |
|--------|------|
| `models.py` | `Match` / `Player` dataclasses. |
| `normalize.py` | Canonicalises messy team names (alias table, accent/suffix stripping, same-named-club disambiguation by state), competition-name matching, multi-format date parsing (ISO, ISO+time, Brazilian `DD/MM/YYYY`). |
| `data_loader.py` | Reads all 6 CSVs into in-memory `Match`/`Player` records, de-dupes fixtures across overlapping sources on `(season, home, away, home_goal, away_goal)`, builds lazy indexes (by team, competition, club, name). `load_all()` is `lru_cache`d. |
| `queries.py` | The five capability categories: match (`find_matches`, `head_to_head`), team (`team_stats`, `compare_teams`, `competitions_for_team`), player (`search_players`, `top_brazilian_players`, `players_for_club`, `top_clubs_by_nationality`), competition (`standings`, `champions`, `relegated_teams`), statistics (`average_goals`, `biggest_wins`, `home_away_balance`, `derbies`). |
| `server.py` | `MCPServer` (mcp 2.x SDK) exposing 16 tools, each delegating to `queries`. `main()` runs stdio/sse/streamable-http transports. |

Flow: `server` tool call → `queries.<fn>` → `data_loader.load_all()` (cached) →
normalised in-memory records → JSON-serialisable dict/list returned verbatim.

Tests (`tests/`, 57 functions, 0 skips) exercise each layer directly plus the
MCP surface via `server.list_tools()` / `server.call_tool()`, asserting concrete
ground-truth (2019 Brasileirão champion = Flamengo 90 pts; top Brazilian player
= Neymar Jr).
