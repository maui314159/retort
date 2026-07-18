# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `soccer_data.py` | Loads, normalizes and queries the six Kaggle CSVs; unified match table + FIFA players | `SoccerStore`, `get_store()`, `normalize_team()`, `normalize_comp()`, `parse_date()`, `display_team()`, `team_display()` |
| `mcp_server.py` | Exposes the query layer as 15 FastMCP tools; stdio/SSE entrypoint | `mcp` (FastMCP), `main()`, 15 `@mcp.tool()` functions |
| `test_brazilian_soccer.py` | BDD-style Given/When/Then pytest suite over the store and the tool layer | 25 test functions in 8 classes (36 tests after parametrization) |
| `requirements.txt` | Runtime + test dependencies | pandas>=2.0, mcp>=1.0, pytest>=8.0, pytest-asyncio>=0.23 |
| `README.md` | Usage / design notes | — |

Data files under `data/kaggle/` are task-supplied inputs, not generated code.
