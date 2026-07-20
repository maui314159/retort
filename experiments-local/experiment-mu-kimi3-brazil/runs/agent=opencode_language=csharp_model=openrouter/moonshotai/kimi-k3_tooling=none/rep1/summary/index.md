# Summary: agent=opencode_language=csharp_model=openrouter/moonshotai/kimi-k3_tooling=none · rep 1

- **Shape:** dependency-free C# (.NET 10) MCP server — hand-rolled JSON-RPC 2.0 over stdio + hand-rolled CSV parser, LINQ query engine over in-memory records
- **Structure:** 10 source modules, 6 test files (102 test cases)
- **Interfaces:** 11 MCP tools over 4 JSON-RPC methods; 1 CLI flag (`--data-dir`)
- **Notable:** zero NuGet dependencies in the server (no MCP SDK, no CsvHelper); cross-file fixture deduplication (±2-day date window); team-name canonicalization with ambiguity errors; 16 hardcoded derby rivalries; real-CSV integration tests mirror the spec's sample questions

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
