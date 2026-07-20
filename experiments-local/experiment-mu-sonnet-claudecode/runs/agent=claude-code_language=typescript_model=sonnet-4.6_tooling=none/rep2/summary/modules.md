# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/index.ts | Process entrypoint — creates the server and connects a stdio transport | `main()` |
| src/server.ts | MCP server construction; registers the six tools with zod input schemas | `createServer()` |
| src/tools.ts | Pure query functions over the loaded data (filter, aggregate, rank) | `searchMatches`, `getTeamStats`, `headToHead`, `searchPlayers`, `getStandings`, `getTopStats` |
| src/dataLoader.ts | CSV loading (all 6 files under `data/kaggle/`), normalization into `NormalizedMatch`/`FifaPlayer`, in-memory caching, team-name normalization | `loadAllMatches`, `loadFifaPlayers`, `normalizeTeamName`, `teamsMatch`, `clearCache` |
| src/types.ts | Interfaces for each raw CSV row shape plus the normalized/result types | `NormalizedMatch`, `FifaPlayer`, `TeamStats`, `HeadToHeadResult`, … |
| src/__tests__/dataLoader.test.ts | Loader + name-normalization tests | 14 test cases |
| src/__tests__/tools.test.ts | BDD-style (Given/When/Then) tests over all six query capabilities | 24 test cases |
