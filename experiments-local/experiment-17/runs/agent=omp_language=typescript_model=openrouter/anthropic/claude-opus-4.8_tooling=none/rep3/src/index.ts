#!/usr/bin/env node
/**
 * Context
 * -------
 * Executable entry point for the Brazilian Soccer MCP server. Loads the Kaggle
 * datasets into memory (loader.ts), builds the MCP server with all tools
 * registered (server.ts), and connects it over stdio so MCP clients (e.g. an
 * LLM host such as Claude Desktop) can call the tools.
 *
 * The dataset directory may be overridden with the SOCCER_DATA_DIR environment
 * variable; otherwise it defaults to `<cwd>/data/kaggle`.
 */

import { join } from "node:path";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { loadSoccerData } from "./loader.js";
import { createServer } from "./server.js";

async function main(): Promise<void> {
  const dataDir = process.env.SOCCER_DATA_DIR ?? join(process.cwd(), "data", "kaggle");
  const data = loadSoccerData(dataDir);
  // Startup diagnostics go to stderr so they never corrupt the stdio JSON-RPC
  // stream on stdout.
  console.error(
    `[brazilian-soccer-mcp] loaded ${data.matches.length} matches, ${data.players.length} players from ${dataDir}`
  );

  const server = createServer(data);
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("[brazilian-soccer-mcp] server ready on stdio");
}

main().catch((err) => {
  console.error("[brazilian-soccer-mcp] fatal:", err);
  process.exit(1);
});
