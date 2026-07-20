#!/usr/bin/env node
/**
 * Entry point: run the Brazilian Soccer MCP server over stdio.
 */

import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { getContext } from "./context.js";
import { createServer } from "./server.js";

async function main(): Promise<void> {
  const ctx = getContext();
  const server = createServer(ctx);
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error(
    `brazilian-soccer-mcp ready: ${ctx.dataset.matches.length} matches, ` +
      `${ctx.dataset.players.length} players, ` +
      `${ctx.built.indexes.teams.size} teams`,
  );
}

main().catch((e) => {
  console.error("Fatal error starting brazilian-soccer-mcp:", e);
  process.exit(1);
});
