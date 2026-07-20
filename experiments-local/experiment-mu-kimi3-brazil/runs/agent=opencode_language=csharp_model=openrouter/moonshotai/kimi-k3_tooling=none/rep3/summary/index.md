# Summary: agent=opencode_language=csharp_model=openrouter/moonshotai/kimi-k3_tooling=none · rep 3

- **Shape:** C# (.NET 10) stdio MCP server — hand-rolled JSON-RPC 2.0 loop (no MCP SDK), in-memory knowledge graph over five Brazilian-soccer CSV datasets.
- **Structure:** 12 source files across `Program` / `Mcp` / `Tools` / `Graph` / `Data` / `Services` layers (~1,900 lines), 13 test files (68 xUnit Fact/Theory tests).
- **Interfaces:** 13 MCP tools (matches, head-to-head, team stats, standings, competition stats, biggest wins, player search/club/top/summary, list teams/competitions, graph stats); 7 JSON-RPC methods; single CLI entry with env-var/upward data-dir resolution.
- **Notable:** No external MCP or CSV dependency — protocol and RFC-4180-ish parsing are hand-written; cross-file joins via a shared `TeamNameNormalizer` canonical key; fuzzy team/competition resolution emits "note" strings in tool output; all tool results are human-readable text rather than structured JSON.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
