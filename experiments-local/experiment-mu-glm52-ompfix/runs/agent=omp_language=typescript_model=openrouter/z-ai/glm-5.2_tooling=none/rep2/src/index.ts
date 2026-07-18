/**
 * Brazilian Soccer MCP Server — stdio entrypoint
 * ----------------------------------------------
 * Context block:
 *   Boots a Model Context Protocol server over stdio. Loads the Kaggle
 *   datasets once at startup, then registers the tool list (from tools.ts)
 *   and a CallToolRequest handler that delegates to the shared dispatcher.
 *   Kept thin: all tool logic lives in src/tools.ts so it is unit-testable.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

import { loadAll } from "./loader.js";
import { createDispatcher, toolDefinitions } from "./tools.js";

/** Create and run the MCP server over stdio. */
export async function main(): Promise<void> {
  const ds = loadAll();
  console.error(`[mcp] loaded ${ds.matches.length} matches, ${ds.players.length} players`, ds.counts);

  const dispatch = createDispatcher(ds);
  const server = new Server(
    { name: "brazilian-soccer-mcp", version: "1.0.0" },
    { capabilities: { tools: {} } },
  );

  server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: toolDefinitions(),
  }));

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    const result = dispatch(name, args ?? {});
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    };
  });

  const transport = new StdioServerTransport();
  await server.connect(transport);
}

// Run when invoked directly.
main().catch((err) => {
  console.error("[mcp] fatal:", err);
  process.exit(1);
});
