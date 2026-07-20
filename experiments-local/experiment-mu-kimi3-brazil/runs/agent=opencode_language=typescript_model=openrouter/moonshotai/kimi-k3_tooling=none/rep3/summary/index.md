# Summary: agent=opencode · language=typescript · model=openrouter/moonshotai/kimi-k3 · tooling=none · rep 3

- **Shape:** TypeScript MCP server (`@modelcontextprotocol/sdk`, stdio transport) over an in-memory knowledge graph built from six Kaggle CSVs; zod tool schemas, vitest tests.
- **Structure:** 8 src modules (~2,340 lines) in a layered pipeline — types → normalize → loader → graph → queries → server → context → index — plus 7 test files + a shared fixture (75 tests).
- **Interfaces:** 15 MCP tools + 1 MCP resource (`soccer://overview`); no HTTP routes; single stdio binary `brazilian-soccer-mcp`.
- **Notable:** explicit graph model (typed nodes/edges with out/in adjacency indexes) rather than plain lookup maps; multi-pass dedup in the loader (exact key merge, ±2-day date-drift reconciliation, league-season integrity drop); extensive team-name canonicalization (state suffixes, diacritics, historical spellings); tests are BDD-styled (`Feature:`/`Scenario:` naming) and exercise the real dataset, with `server.test.ts` driving the MCP server through the SDK client.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
