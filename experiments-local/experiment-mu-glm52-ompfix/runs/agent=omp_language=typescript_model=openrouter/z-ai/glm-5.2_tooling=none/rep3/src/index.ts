/**
 * Brazilian Soccer MCP Server — Entrypoint
 * -----------------------------------------------------------------------------
 * Context block:
 *   Wires the dataset (loaded once at startup) into the MCP server over the
 *   stdio transport. Run with `npm start` (compiled) or `npm run dev` (tsx).
 *   The server speaks the Model Context Protocol so any MCP-capable LLM client
 *   can connect and call the tools in `tools.ts`.
 *
 *   Loading is synchronous and happens before `connect()` so the first tool
 *   call never pays the parse cost. Memory footprint is the parsed model held
 *   in-process (~25k matches + ~18k players).
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { loadDataset } from "./data/loader.js";
import { registerTools } from "./tools.js";

async function main(): Promise<void> {
  const ds = loadDataset();
  const server = new McpServer({
    name: "brazilian-soccer-mcp",
    version: "2.0.0",
  });
  registerTools(server, ds);
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
