# Flow

```mermaid
sequenceDiagram
    participant Client as MCP Client
    participant index as index.ts
    participant server as server.ts
    participant teams as teams.ts (TeamRegistry)
    participant queries as queries.ts
    participant format as format.ts

    Note over index: startup
    index->>index: loadDataset() — parse 6 CSVs, dedupe matches
    index->>index: KnowledgeGraph.fromDataset(dataset)
    index->>server: createServer(dataset, graph)
    index->>Client: connect(StdioServerTransport)

    Client->>server: call_tool find_matches {team:"Flamengo", opponent:"Fluminense"}
    server->>teams: resolveTeamOrError(dataset, "Flamengo")
    teams-->>server: Team node (canonical, accent/suffix-insensitive)
    server->>teams: resolveTeamOrError(dataset, "Fluminense")
    teams-->>server: Team node
    server->>queries: findMatches(dataset, {team, opponent, ...})
    queries-->>server: Match[]
    server->>server: sortByDateDesc(matches)
    server->>format: formatMatchList(ordered, limit)
    format-->>server: lines + hiddenCount
    server-->>Client: text result (header, match lines, "... N more")
```

At startup, `index.ts` loads all six Kaggle CSVs into a unified, deduplicated `Dataset`, builds the in-memory `KnowledgeGraph`, and connects the MCP server over stdio. On a `find_matches` call, `server.ts` first resolves each free-text team name through the `TeamRegistry` (normalizing accents, state suffixes and alias spellings) — unresolvable names return an `isError` text result rather than a thrown error. It then delegates to the pure query function `findMatches` in `queries.ts`, sorts results most-recent-first, and renders them via `format.ts` with a truncation note when results exceed the limit (default 20).

Deviations from common patterns: all data is held in memory and queries are synchronous inside async handlers (fine at this dataset size, no streaming/pagination beyond a `limit` cap); date-range inputs are compared as raw strings rather than validated as dates; tool errors are conveyed via `isError` text results, so malformed filter values (e.g. an invalid `dateFrom`) silently narrow results instead of erroring.
