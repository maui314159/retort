#!/usr/bin/env node
/**
 * Context
 * -------
 * Executable entrypoint for the Brazilian Soccer MCP server. Loads the CSV
 * datasets into an in-memory DataStore, builds the MCP server, and serves it
 * over stdio (the transport MCP clients launch by default). Data directory can
 * be overridden with the SOCCER_DATA_DIR environment variable.
 */

import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { loadStore } from "./store.js";
import { buildServer } from "./server.js";

async function main(): Promise<void> {
  const dataDir = process.env.SOCCER_DATA_DIR;
  const store = await loadStore(dataDir);
  // stderr only: stdout is reserved for the MCP JSON-RPC stream.
  console.error(
    `[brazilian-soccer-mcp] loaded ${store.matches.length} matches, ` +
      `${store.players.length} players`,
  );

  const server = buildServer(store);
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("[brazilian-soccer-mcp] server connected over stdio");
}

main().catch((err) => {
  console.error("[brazilian-soccer-mcp] fatal:", err);
  process.exit(1);
});
