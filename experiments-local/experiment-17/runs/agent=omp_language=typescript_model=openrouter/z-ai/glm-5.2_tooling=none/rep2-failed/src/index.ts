#!/usr/bin/env node
/**
 * brazilian-soccer-mcp / src/index.ts
 *
 * Entrypoint: loads the datasets and starts the MCP server over stdio.
 *
 * Context block:
 * Resolves the data directory (default `./data/kaggle`, overridable via the
 * `BR_SOCCER_DATA_DIR` environment variable), loads all six CSVs into an
 * in-memory store, registers the MCP tools, and connects the server to a
 * stdio transport. Loading is synchronous and runs once at startup; the
 * server then answers tool calls from the connected MCP client.
 */

import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { loadData } from "./loader.js";
import { SoccerStore } from "./store.js";
import { createServer } from "./server.js";

async function main(): Promise<void> {
  const data = loadData();
  const store = new SoccerStore(data);
  const server = createServer(store);
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error(
    `[brazilian-soccer-mcp] running on stdio ` +
      `(${data.matches.length} matches, ${data.players.length} players)`,
  );
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
