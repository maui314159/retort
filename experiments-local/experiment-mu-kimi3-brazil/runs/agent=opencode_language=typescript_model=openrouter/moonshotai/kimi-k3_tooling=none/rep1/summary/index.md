# Summary: agent=opencode · language=typescript · model=openrouter/moonshotai/kimi-k3 · tooling=none · rep 1

- **Shape:** TypeScript MCP server (stdio, `@modelcontextprotocol/sdk` + zod) over an in-memory knowledge graph built from six Kaggle CSVs of Brazilian soccer data.
- **Structure:** 10 source modules (entry point, tool layer, 8 lib modules), 8 test files (67 tests) + shared fixture, tested with vitest.
- **Interfaces:** 10 MCP tools (dataset_summary, find_matches, head_to_head, team_stats, standings, search_players, brazilian_players_by_club, biggest_wins, competition_stats, graph_neighbors); no HTTP routes or CLI subcommands.
- **Notable:** layered architecture with a transport-agnostic `createServer` factory (tests drive it over an in-memory transport); a dedicated `TeamRegistry` canonicalizes team-name variants (accents, state suffixes, alias spellings) across datasets; cross-file match deduplication at load time; an explicit typed knowledge graph (4 node types, 8 edge types) exposed via a `graph_neighbors` tool.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
