# Codebase summary: brazilian_soccer_mcp (kimi-k3 · opencode · rep1)

Python MCP server (FastMCP, stdio) over the six bundled Kaggle CSVs. ~1,900
lines of Python across 17 files; clean layered architecture.

## Modules

| Module | Role |
|--------|------|
| `brazilian_soccer_mcp/data.py` | Loads all 6 CSVs into two frames (`matches` unified across the 5 match files with cross-file dedup, `players` from FIFA data); `KnowledgeBase` dataclass, `get_kb()` lru-cached singleton, `BRAZILIAN_SOCCER_DATA` env override for the data dir. |
| `brazilian_soccer_mcp/normalization.py` | Team-name canonicalization (`team_key`, `clean_team_name`, accent-insensitive `text_key`) and multi-format `parse_date` (ISO, DD/MM/YYYY, with-time). |
| `brazilian_soccer_mcp/queries.py` | Pure query functions returning JSON-serializable dicts: `find_matches`, `head_to_head`, `team_stats`, `standings` (3/1/0 points, Brazilian tie-break), `search_players`, `club_summary`, `biggest_wins`, `competition_stats`, `list_competitions`, `list_teams`, `dataset_summary`, plus `resolve_team` with did-you-mean suggestions (`TeamNotFoundError`). |
| `brazilian_soccer_mcp/formatting.py` | Renders query dicts to the human-readable answer formats shown in the spec. |
| `brazilian_soccer_mcp/server.py` | FastMCP app registering 11 tools that wrap query+format; `_guard` converts lookup errors to friendly text; `main()` warms the cache and runs stdio. Console script `brazilian-soccer-mcp` in `pyproject.toml`. |

## Flow

CSV files → `data.load_*` (per-file schema mapping + normalization) → unified
`matches` / `players` frames → `queries.*` (pandas filtering/aggregation) →
`formatting.*` → MCP tool text response.

## Tests (117 passing)

- Unit: `tests/test_data.py` (loading/dedup), `test_normalization.py` (names,
  dates, accents), `test_queries.py` (each query function), `test_server.py`
  (tool registration and end-to-end tool calls).
- BDD: 5 Gherkin features (`tests/features/*.feature` — matches, teams,
  players, competitions, statistics) bound via `pytest_bdd.scenarios()` in
  `tests/step_defs/`, matching the spec's suggested BDD testing approach.
