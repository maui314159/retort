# Flow

```mermaid
sequenceDiagram
    participant Client as MCP client (LLM)
    participant index as index.ts
    participant loader as data-loader.ts
    participant engine as query-engine.ts
    Note over index,loader: startup: 6 CSVs → Database (in memory)
    Client->>index: CallTool search_matches {team:"Flamengo", opponent:"Fluminense"}
    index->>engine: searchMatches(db, opts)
    engine->>loader: normalizeTeam()/teamMatches() per row
    engine-->>index: NormalizedMatch[] (date-desc, limited)
    index-->>Client: {content:[{type:"text", text: formatted list}]}
```

At startup `index.ts` synchronously loads all six CSVs via `data-loader.ts` and concatenates the four match sources into one `NormalizedMatch[]`. Each MCP `CallTool` request is routed by a switch in `index.ts` to a pure function in `query-engine.ts` that filters/aggregates the in-memory arrays and returns formatted plain text. Errors are caught per-call and returned as text. Notable deviations: no dedup between the overlapping Brasileirão datasets; `searchMatches` sorts a possibly shared array in place; no input validation beyond TypeScript casts.
