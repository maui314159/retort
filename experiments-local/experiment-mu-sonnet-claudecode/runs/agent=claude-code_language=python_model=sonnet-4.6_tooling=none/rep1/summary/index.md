# Codebase Summary: brazilian-soccer-mcp-server (sonnet-4.6 / claude-code / python / tooling=none, rep1)

## Layout

| File | Role |
|------|------|
| `server.py` (420 loc) | MCP server — `FastMCP("Brazilian Soccer")`, 9 `@mcp.tool()` tools, `mcp.run()` entrypoint |
| `data_loader.py` (147 loc) | Loads the 6 CSVs in `data/kaggle/`, normalizes team names, concatenates match frames, shared query helper |
| `tests/test_server.py` (266 loc) | 34 BDD-style pytest tests across 8 test classes |

## Modules & flow

- **`data_loader.py`** — one `_load_*` function per dataset (Brasileirão, Copa do Brasil, Libertadores, BR-Football, histórico, FIFA players). Each adds a `competition` label, normalized team-name columns (`_normalize_team_name` strips `-SP`/`-RJ` state suffixes), and a parsed `date`. `get_matches()` lazily concatenates all five match frames into one module-level DataFrame with numeric goals and `Int64` season; `get_fifa()` lazily loads the player CSV. `find_team_matches()` is the shared filter (team/opponent substring match on normalized names, season, competition, home/away-only flags).
- **`server.py`** — thin MCP tool layer over `data_loader`. Tools: `find_matches`, `team_statistics` (W/D/L + GF/GA), `head_to_head`, `season_standings` (3-1-0 points computed from results), `find_players` (name/nationality/club/position/min-rating over FIFA data), `top_scorers_analysis`, `biggest_wins`, `match_averages`, `best_home_record`. All return formatted strings.
- **`tests/`** — import the tool functions directly (no MCP transport) and assert on the formatted output: data loading, match queries, team stats, head-to-head, standings, player queries, aggregate stats, cross-file queries.

## Notable design points

- Data is loaded lazily and cached in module globals; no external APIs — only the supplied CSVs (per spec).
- Team matching is case-insensitive substring `contains` on state-suffix-stripped names; convenient for queries, but merges distinct clubs that differ only by state suffix (e.g. Atlético-MG / Atlético-GO) — see findings.
- The two Serie A datasets overlap for seasons 2012–2019 and are not deduplicated, so aggregates over those seasons count fixtures twice — see findings.
