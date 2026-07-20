# Run Summary — csharp / sonnet-4.6 / claude-code / tooling=none · rep3

**Surface:** An MCP server (stdio) answering natural-language-style queries over the six bundled Brazilian soccer CSVs — match search, head-to-head, team stats, computed standings, FIFA player search, and aggregate statistics.

**Flow:** `Program.cs` walks up from the binary to find `data/kaggle`, eagerly loads all six CSVs into an in-memory `SoccerDatabase` (lists of records), then hosts `SoccerTools` — 10 attribute-registered MCP tools — over stdio via the official `ModelContextProtocol` C# SDK. Queries are LINQ over the in-memory lists; team-name variation is handled by `DataLoader.NormalizeTeam` (strips `-SP`/`-RJ` state suffixes) + substring `TeamMatches`.

- [modules.md](modules.md) — file-by-file map
- [interfaces.md](interfaces.md) — the 10 MCP tools and data schemas

Notable: clean layered design (loader → database → tools); tests run against the real CSVs (integration-style), 44 test cases, no mocks, no skips.
