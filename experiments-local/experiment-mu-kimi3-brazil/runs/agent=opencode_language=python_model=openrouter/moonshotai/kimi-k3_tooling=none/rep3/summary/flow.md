# Flow

```mermaid
sequenceDiagram
    Client->>server.py: MCP tool call find_matches(team="Flamengo")
    server.py->>query_engine.py: qe.find_matches(team=...)
    query_engine.py->>soccer_data.py: get_store() (lru_cached)
    soccer_data.py-->>query_engine.py: SoccerStore (matches + players)
    query_engine.py->>query_engine.py: _resolve_team_key / _filter_matches
    query_engine.py-->>server.py: {"total", "returned", "matches": [...]}
    server.py-->>Client: JSON tool result
```

A tool call reaches the thin `@mcp.tool()` wrapper in `server.py`, which delegates to the matching `query_engine` function. The engine lazily loads the cached `SoccerStore` (all six CSVs parsed, team names normalised, cross-source duplicate fixtures collapsed), filters the `played_matches` DataFrame with pandas boolean masks, and serialises the head of the result to plain dicts. Notable: every match row serialisation calls `_team_name`, which rebuilds the full display-name map (`_display_names` does a groupby over all matches) — correct but repeated work per row; results are still returned well within the spec's latency targets per the passing tests. Input validation exists for venue and competition (explicit `ValueError`s); unknown teams degrade to empty results rather than erroring.
