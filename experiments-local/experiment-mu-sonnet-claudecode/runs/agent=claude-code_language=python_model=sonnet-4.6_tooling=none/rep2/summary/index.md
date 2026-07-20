# Codebase Summary — brazilian-soccer MCP server (python · sonnet-4.6 · claude-code · tooling=none · rep2)

## Modules

| File | LOC | Role |
|------|-----|------|
| `server.py` | 651 | MCP server (`mcp.server.Server`, stdio transport). Declares 7 tools in `list_tools()`; single `call_tool()` dispatcher implements them all against pandas DataFrames. |
| `data_loader.py` | 166 | Loads the 6 CSVs from `data/kaggle/`, parses multi-format dates (`_parse_dates`), normalizes team names via alias map (`normalize_team`), unifies match sources in `load_all_matches()`. |
| `tests/test_server.py` | 377 | 45 BDD-style pytest tests: data loading, normalization, and one class per tool, calling `srv.call_tool` directly via an asyncio helper. |

## Tools exposed

- `search_matches` — team/team2/competition/season/date-range filters over the unified match frame
- `get_team_stats` — W/D/L, GF/GA, win rate, home/away split
- `search_players` — FIFA data by name/nationality/club/position/min_overall
- `get_head_to_head` — W/D/L record between two teams + recent matches
- `get_competition_standings` — Brasileirão points table computed from `brasileirao` + `historico` frames
- `get_biggest_wins` — largest goal margins
- `get_average_goals` — goals/match, home-win/draw/away-win rates

## Data flow

CSV files → per-source loaders (rename columns to a common schema: `home_team`, `away_team`, `home_goal`, `away_goal`, `datetime`, `competition`, `*_norm`) → `load_all_matches()` concat → lazily cached in `server._DATA` on first tool call → filtered per tool → formatted text via `_fmt_match`.

## Known structural issue

`Brasileirao_Matches.csv` (2012–2022) and `novo_campeonato_brasileiro.csv` (2003–2019) overlap for seasons 2012–2019. Both `load_all_matches()` and `get_competition_standings` include both sources; `drop_duplicates()` cannot match rows across them (different team-name spellings and column sets), so overlapping seasons are double-counted. See `../findings.jsonl`.
