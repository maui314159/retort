# Summary: agent=opencode_language=python_model=openrouter/moonshotai/kimi-k3_tooling=none · rep 3

- **Shape:** FastMCP (stdio) server over an in-memory pandas store; 3-layer split (server → query engine → data layer)
- **Structure:** 3 source modules, 7 test files (pytest-bdd) + 6 Gherkin feature files
- **Interfaces:** 13 MCP tools / 1 CLI entry (`python server.py`) / 13 public query functions
- **Notable:** unusually thorough team-name normalisation (~100-entry alias table, state/country suffix stripping, letter-spaced acronym handling) and cross-source fixture de-duplication with source priority — most runs of this task skip both. BDD-style tests (pytest-bdd + Gherkin) rather than plain pytest.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
