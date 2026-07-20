# Summary: agent=claude-code_language=typescript_model=sonnet-4.6_tooling=none · rep 1

- **Shape:** TypeScript stdio MCP server (@modelcontextprotocol/sdk) over an in-memory CSV-backed dataset; vitest test suite.
- **Structure:** 4 source modules, 2 test files (34 tests).
- **Interfaces:** 8 MCP tools (match search, team stats, head-to-head, standings, player search, global stats, biggest wins, extended stats).
- **Notable:** All four match CSVs are concatenated into one normalized list with no cross-dataset dedup — the Brasileirão and historical CSVs overlap for seasons 2012–2019, so aggregate tools double-count those seasons. Team-name matching uses accent-stripped bidirectional substring matching.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
