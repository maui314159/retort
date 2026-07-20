# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/index.ts | Entry point: loads the datasets, builds the knowledge graph and serves the MCP server over stdio | `main()` |
| src/server.ts | MCP server exposing the Brazilian soccer knowledge graph as tools; transport-agnostic factory | `createServer(dataset, graph)` |
| src/lib/dataset.ts | Dataset loader: reads the six Kaggle CSV files, normalizes rows into canonical Match/Player records, merges cross-file duplicate matches | `loadDataset()`, `resolveDataDir()`, `Dataset`, `DATA_FILES` |
| src/lib/types.ts | Core domain types for the Brazilian soccer knowledge graph | `Competition`, `Team`, `Match`, `MatchStats`, `Player`, `MatchResult`, `matchResult()` |
| src/lib/teams.ts | Canonical team registry: canonicalizes raw spellings via three mapping layers (full raw name, suffix-less base, base+UF) and resolves free-text queries | `TeamRegistry`, `TeamResolution` |
| src/lib/text.ts | Text normalization utilities: Brazilian Portuguese accents, cedillas, casing, whitespace | `normalizeText()`, `splitTeamSuffix()` |
| src/lib/dates.ts | Date parsing for the multiple formats used across the datasets (ISO, ISO+time, DD/MM/YYYY) | `parseDateTime()`, `parseYear()`, `ParsedDateTime` |
| src/lib/queries.ts | Query engine: all retrieval operations over the unified dataset, pure functions with no MCP plumbing | `findMatches()`, `headToHead()`, `teamRecord()`, `computeStandings()`, `searchPlayers()`, `brazilianPlayersByClub()`, `competitionStats()`, `biggestWins()`, `resolveCompetition()`, `resolveTeamOrError()` |
| src/lib/graph.ts | In-memory knowledge graph over the unified dataset (team/player/match/competition nodes, typed edges) | `KnowledgeGraph` (`fromDataset()`, `neighbors()`, node-id statics), `GraphNode`, `GraphEdge` |
| src/lib/format.ts | Response formatters — render query results in the answer styles shown in the specification examples | `formatMatchLine()`, `formatMatchList()`, `formatTeamRecord()`, `formatHeadToHead()`, `formatStandings()`, `formatPlayer()`, `formatCompetitionStats()`, `formatBigWins()`, `teamLabel()` |
| test/helpers.ts | Shared test fixture: loads the real dataset once per test worker | `getDataset()` |
| test/dataset.test.ts | Dataset loading tests | 6 test functions |
| test/normalization.test.ts | Text, date and team-name normalization tests | 16 test functions |
| test/matches.test.ts | Match query tests | 8 test functions |
| test/teams.test.ts | Team query tests | 6 test functions |
| test/players.test.ts | Player query tests | 7 test functions |
| test/competitions.test.ts | Competition query tests | 7 test functions |
| test/stats.test.ts | Statistical analysis tests | 6 test functions |
| test/mcp.test.ts | MCP protocol end-to-end tests (in-memory transport) | 11 test functions |
| vitest.config.ts | Vitest configuration | — |
