# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| server.py | MCP server (FastMCP, stdio) exposing the query engine as 13 tools | `mcp`, `main()`, 13 `@mcp.tool()` wrappers |
| query_engine.py | All query logic over the in-memory store; JSON-serialisable returns | `find_matches`, `head_to_head`, `team_statistics`, `list_teams`, `search_players`, `top_players`, `player_profile`, `competition_standings`, `top_scoring_teams`, `list_competitions`, `biggest_wins`, `best_team_records`, `competition_overview` |
| soccer_data.py | Data layer: loads 6 Kaggle CSVs, normalises team names/dates, dedupes cross-source fixtures | `get_store()`, `SoccerStore`, `normalize_team`, `normalize_text`, `parse_date` |
| tests/conftest.py | Shared pytest-bdd fixtures/steps (session-scoped store) | `store`, `context` fixtures |
| tests/test_match_queries.py | Step definitions for match_queries.feature (8 scenarios) | `scenarios(...)` binding |
| tests/test_team_queries.py | Step definitions for team_queries.feature (4 scenarios) | `scenarios(...)` binding |
| tests/test_player_queries.py | Step definitions for player_queries.feature (7 scenarios) | `scenarios(...)` binding |
| tests/test_competition_queries.py | Step definitions for competition_queries.feature (4 scenarios) | `scenarios(...)` binding |
| tests/test_statistics.py | Step definitions for statistics.feature (6 scenarios) | `scenarios(...)` binding |
| tests/test_normalization.py | Step definitions for normalization.feature (5 scenarios) | `scenarios(...)` binding |
| tests/features/*.feature | 6 Gherkin feature files, 34 scenarios total | — |
