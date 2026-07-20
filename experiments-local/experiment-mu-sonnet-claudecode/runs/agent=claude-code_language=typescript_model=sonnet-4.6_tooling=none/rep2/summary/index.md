# Summary: agent=claude-code_language=typescript_model=sonnet-4.6_tooling=none · rep 2

- **Shape:** TypeScript MCP server (`@modelcontextprotocol/sdk`, stdio transport) over five Kaggle match CSVs + the FIFA player CSV, parsed with `csv-parse` into an in-memory cache.
- **Structure:** 5 source modules, 2 test files (vitest, 38 tests).
- **Interfaces:** 6 MCP tools (`search_matches`, `get_team_stats`, `head_to_head`, `search_players`, `get_standings`, `get_top_stats`); the pure query functions are also exported from `tools.ts` and tested directly.
- **Notable:** query logic is fully separated from MCP plumbing (`tools.ts` vs `server.ts`), and the loader normalizes team names (strips state suffixes/parentheticals, folds accents) so filters match across the differently-formatted datasets.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
