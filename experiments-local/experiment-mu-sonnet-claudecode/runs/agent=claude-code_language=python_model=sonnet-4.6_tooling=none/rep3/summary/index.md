# Codebase Summary — brazilian-soccer-mcp-server (rep3)

Three-module Python MCP server built on FastMCP + pandas.

## Modules

| File | LOC | Role |
|------|-----|------|
| `server.py` | 152 | MCP entrypoint. `fastmcp.FastMCP` instance exposing 7 tools: `find_matches`, `get_team_statistics`, `get_head_to_head`, `find_players`, `get_standings`, `get_biggest_wins`, `get_dataset_summary`. Each tool is a thin, limit-clamped wrapper over `data_loader`. |
| `data_loader.py` | 518 | Data + query engine. Per-CSV loaders (`load_brasileirao`, `load_copa_brasil`, `load_libertadores`, `load_br_football`, `load_historico`, `load_fifa`), each `@lru_cache`d, normalizing columns to a shared schema (`date`, `home`, `away`, `home_goals`, `away_goals`, `season`, `competition`). `load_all_matches()` concatenates the five match datasets. Query functions filter/aggregate the combined frame. |
| `test_server.py` | 322 | 50 pytest tests in 9 classes: normalization, per-file loading, match queries, team stats, head-to-head, player queries, standings, biggest wins, dataset summary, and MCP tool registration (via `mcp.list_tools()`). |

## Flow

CSV files in `data/kaggle/` → cached loaders normalize to a unified match schema → `load_all_matches()` union → query functions (filter by team/competition/season/date; aggregate W/D/L, standings, head-to-head, summary stats) → serialized as plain dict/list results by the MCP tools.

## Interfaces / conventions

- Team-name handling: `normalize_team()` strips `-SP`-style state suffixes, accents, case, and applies an alias map (`sport club corinthians paulista` → `corinthians`); matching is bidirectional substring containment.
- Dates parsed per-dataset (ISO, Brazilian `DD/MM/YYYY`, datetime-with-time all handled); seasons as nullable `Int64`.
- FIFA player data kept separate from match data (no cross-join needed by the tools).
