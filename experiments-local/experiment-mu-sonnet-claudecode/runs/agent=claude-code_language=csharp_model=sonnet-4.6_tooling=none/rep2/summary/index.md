# Summary: agent=claude-code_language=csharp_model=sonnet-4.6_tooling=none · rep 2

- **Shape:** .NET 10 MCP server (official `ModelContextProtocol` 1.4.1 SDK, stdio transport) with CsvHelper-backed in-memory data layer.
- **Structure:** 9 source modules (1,368 LoC) + 5 test files (543 LoC, 55 xUnit tests).
- **Interfaces:** 13 MCP tools across 4 tool classes (match / player / team / stats); no HTTP, no CLI.
- **Notable:** dedicated `TeamNameNormalizer` with ~80-entry alias table and state-suffix regexes; tools return formatted prose strings, not JSON; overlapping Brasileirão datasets are loaded without deduplication.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
