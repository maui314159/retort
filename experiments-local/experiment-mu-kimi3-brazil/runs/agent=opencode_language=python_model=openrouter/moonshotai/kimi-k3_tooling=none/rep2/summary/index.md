# Codebase summary — kimi-k3 · brazil-bench · rep2

*(Generated inline by evaluate-run; the `run-summary` skill was not available as an invocable skill in this session.)*

## Layout

```
brazilian_soccer_mcp/     # package (1,181 LOC)
├── server.py             # FastMCP entrypoint — 10 @mcp.tool functions, stdio/HTTP transports
├── queries.py            # QueryEngine — all query logic, organized by the 5 spec categories
├── data.py               # DataStore — loads the 6 CSVs from data/kaggle/ into a canonical match frame + players frame
├── normalization.py      # team/competition name normalization, date parsing (ISO + DD/MM/YYYY)
└── graph.py              # lightweight knowledge graph (team↔competition edges) — beyond spec
tests/                    # pytest-bdd suite (703 LOC)
├── features/*.feature    # 6 feature files, 28 scenarios total
├── test_*.py             # step definitions per feature, via scenarios()
└── conftest.py           # session-scoped DataStore/QueryEngine fixtures + shared Given steps
```

## Flow

`server.py` lazily builds one `DataStore` (reads all six Kaggle CSVs, normalizes team
keys, dedups to a canonical per-season match frame) and wraps it in a `QueryEngine`.
Each MCP tool is a thin delegation to an engine method. Engine methods share a common
`_filter()` (team/opponent/competition/season/date-range) and `_played()` helper, then
aggregate with pandas.

## Interfaces (MCP tools)

`dataset_overview`, `search_matches`, `head_to_head`, `team_statistics`,
`competition_standings`, `team_competitions`, `search_players`, `top_rated_players`,
`biggest_wins`, `competition_stats`.

## Notable design points

- Team-name normalization ("Palmeiras-SP" ≡ "Palmeiras") with substring fallback in `QueryEngine._resolve_team`.
- Standings computed from results with 3/1/0 points, full tie-break chain, champion/relegation tags (`queries.py:standings`).
- Tests are BDD (pytest-bdd) with human-readable Gherkin feature files — an idiomatic, above-baseline test structure.
