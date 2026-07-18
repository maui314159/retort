# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `brazilian_soccer/__init__.py` | Package docstring + version marker; no runtime logic | `__version__` |
| `brazilian_soccer/models.py` | Serializable dataclasses that form the contract between loader, queries, and MCP tools; plus canonical competition names and position groupings | `Match`, `TeamRecord`, `Standing`, `Player`, `COMPETITIONS`, `POSITION_GROUPS` |
| `brazilian_soccer/normalize.py` | Team-name normalization: strips state suffixes (`-SP`) and parenthetical notes, folds accents to an ASCII match key; canonical derby table | `normalize_team()`, `team_key()`, `derby_name()`, `STATE_CODES`, `DERBIES`, `DERBY_KEYS` |
| `brazilian_soccer/loader.py` | Loads the 5 match CSVs + FIFA player CSV from `data/kaggle/` into unified, deduplicated pandas DataFrames; `lru_cache`d | `DATA_DIR`, `load_matches()`, `load_players()`, `get_data_summary()`, `clear_cache()` |
| `brazilian_soccer/queries.py` | Query engine over the DataFrames: match search, team records, player search, standings, aggregate stats | `find_matches()`, `head_to_head()`, `team_statistics()`, `team_competitions()`, `search_players()`, `top_players_at_club()`, `competition_standings()`, `team_display()`, `competition_champion()`, `relegated_teams()`, `average_goals()`, `biggest_wins()`, `best_team_record()`, `derbies()`, `data_summary()` |
| `brazilian_soccer/server.py` | FastMCP server; registers one `@mcp.tool` wrapper per query function and one resource; console-script entry point | `mcp`, `main()`, 14 `tool_*` functions, `summary_resource()` |
| `tests/conftest.py` | Session-scoped fixtures wrapping the cached loaders | `matches_df`, `players_df` |
| `tests/test_loader.py` | CSV loading, dedup, dtype coercion, date parsing | 10 test functions |
| `tests/test_queries.py` | Query-engine behavior across all five query categories | 35 test functions |
| `tests/test_server.py` | MCP tool registration and protocol-level tool invocation | 11 test functions |
| `tests/test_bdd.py` | pytest-bdd step definitions binding `features/match_queries.feature` | 7 scenarios (`scenarios(...)`), 0 plain test functions |
| `features/match_queries.feature` | Gherkin feature file: 7 scenarios over match/team/standings/player queries | `Feature: Match Queries` |
| `pyproject.toml` | setuptools build, deps (`pandas`, `mcp`, `fastmcp`), pytest config, console script | `brazilian-soccer-mcp` script |
| `README.md` | Usage/architecture notes (agent-authored) | — |
| `brazilian-soccer-mcp-guide.md` | Additional agent-authored guide document | — |

Total: 63 tests (10 + 35 + 11 plain functions + 7 BDD scenarios).

Not listed (generated/build artifacts, excluded per skill constraints): `build/lib/brazilian_soccer/*` (a duplicate copy of the package), `brazilian_soccer_mcp.egg-info/`, `.pytest_cache/`, `.ruff_cache/`, `.coverage`, `data/kaggle/*.csv` (provided inputs), and harness files (`TASK.md`, `FEEDBACK.md`, `REQUIREMENTS.json`, `scores.json`, `stack.json`, `prompts.txt`, `_agent_std*.log`).
