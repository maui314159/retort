# Modules

The task surface (`TASK.md`) is an **MCP server** exposing a knowledge-graph-style query
interface over six bundled Kaggle CSVs (Brasileirão Série A, Copa do Brasil, Copa
Libertadores, an extended match-stats file, a 2003–2019 historical Brasileirão file, and a
FIFA player database), answering natural-language questions across five categories: match
queries, team queries, player queries, competition queries, and statistical analysis.

**Archive state:** this run contains only the data and query layers. There is **no
`server.py`** (the MCP tool layer) and **no `tests/` directory** on disk, though both are
referenced by files that are present (`pyproject.toml` declares the console script
`brazilian-soccer-mcp = "brazilian_soccer.server:main"` and sets `testpaths = ["tests"]`;
`models.py`, `loader.py`, and `queries.py` all name `server.py` in their header comments).
There is also no `brazilian_soccer/__init__.py`. The run aborted before those files were
written.

| Path | Purpose | Entry points |
|------|---------|--------------|
| `brazilian_soccer/models.py` | JSON-serializable dataclasses + canonical competition/position tables | `Match`, `TeamRecord`, `Standing`, `Player`, `COMPETITIONS`, `POSITION_GROUPS` |
| `brazilian_soccer/normalize.py` | Team-name normalization (state suffixes, parentheticals, accents) + derby table | `normalize_team()`, `team_key()`, `derby_name()`, `STATE_CODES`, `DERBIES`, `DERBY_KEYS` |
| `brazilian_soccer/loader.py` | Reads the six CSVs into one deduplicated match DataFrame + a player DataFrame | `DATA_DIR`, `load_matches()`, `load_players()`, `get_data_summary()`, `clear_cache()` |
| `brazilian_soccer/queries.py` | Query engine over the loaded frames; all five TASK.md query categories | `find_matches()`, `head_to_head()`, `team_statistics()`, `team_competitions()`, `search_players()`, `top_players_at_club()`, `competition_standings()`, `competition_champion()`, `relegated_teams()`, `average_goals()`, `biggest_wins()`, `best_team_record()`, `derbies()`, `data_summary()`, `team_display()` |
| `pyproject.toml` | setuptools packaging; deps `pandas`, `mcp`, `fastmcp`; test extra `pytest`, `pytest-bdd`, `pytest-asyncio` | console script → `brazilian_soccer.server:main` (target absent) |
| `README.md` | Project documentation | — |
| `data/kaggle/*.csv` | The six bundled input datasets | — |

Not listed: `.ruff_cache/`, `brazilian_soccer_mcp.egg-info/`, `.coverage`, and harness
artifacts (`_meta.json`, `stack.json`, `scores.json`, `prompts.txt`, `_agent_*.log`).

**Line counts:** `queries.py` 539, `loader.py` 357, `models.py` 147, `normalize.py` 135
(1,178 total including comments; ~832 lines of code).
