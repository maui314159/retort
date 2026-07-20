# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/index.ts | Entry point: run the Brazilian Soccer MCP server over stdio | `main()` (script) |
| src/context.ts | Shared application context: loads the dataset once and wires the knowledge graph + query engine | `getContext()`, `AppContext` |
| src/server.ts | MCP server exposing the Brazilian soccer knowledge graph as tools | `createServer(ctx)` |
| src/loader.ts | CSV loading layer: reads the six Kaggle datasets and produces a unified, deduplicated match list plus FIFA players | `loadDataset()`, `findDataDir()`, `Dataset` |
| src/normalize.ts | Team-name/date/competition normalization (diacritics, state suffixes, aliases) | `loose()`, `parseTeamName()`, `canonicalTeamKey()`, `teamDisplayName()`, `isBrazilianTeamKey()`, `teamRef()`, `resolveTeamQuery()`, `teamNameMatches()`, `parseDate()`, `resolveCompetition()`, `competitionFromTournament()`, `stripDiacritics()` |
| src/graph.ts | In-memory knowledge graph over the unified dataset (typed nodes/edges + pre-built indexes) | `KnowledgeGraph`, `buildGraph()`, `BuiltGraph`, `GraphIndexes` |
| src/queries.ts | Query engine over the built graph (matches, records, standings, players, stats) | `SoccerQueries`, `createQueries()` |
| src/types.ts | Shared domain types for the knowledge graph | `COMPETITIONS`, `Match`, `Player`, `TeamRef`, `MatchStats`, `TeamRecord`, `StandingRow` |
| tests/helpers.ts | Shared test fixture: loads the dataset once per test process | `givenDataLoaded()`, `givenQueries()` |
| tests/normalize.test.ts | Team-name/date/competition normalization scenarios | 17 tests |
| tests/matches.test.ts | Match queries + head-to-head scenarios | 10 tests |
| tests/teams.test.ts | Team record/competition scenarios | 6 tests |
| tests/players.test.ts | FIFA player query scenarios | 10 tests |
| tests/competitions.test.ts | Standings/champion/relegation/Libertadores scenarios | 8 tests |
| tests/stats.test.ts | Aggregate statistics scenarios | 13 tests |
| tests/server.test.ts | MCP server tool listing and invocation via SDK client | 11 tests |
