#!/usr/bin/env node
/**
 * Context
 * -------
 * Executable entrypoint for the Brazilian Soccer MCP server. Loads the bundled
 * datasets once at startup, builds the `SoccerGraph` + MCP server, and serves
 * over stdio (the transport MCP hosts such as Claude Desktop use).
 *
 * Startup status is written to stderr so it never corrupts the stdout JSON-RPC
 * stream. An optional `BRAZILIAN_SOCCER_DATA_DIR` env var overrides the data
 * directory (useful for tests / alternate datasets).
 */

import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

import { createServer } from "./server.js";
import { SoccerGraph } from "./service.js";

async function main(): Promise<void> {
  const dir = process.env["BRAZILIAN_SOCCER_DATA_DIR"];
  const started = Date.now();
  const graph = SoccerGraph.load(dir);
  process.stderr.write(
    `[brazilian-soccer-mcp] loaded ${graph.matches.length} matches, ${graph.players.length} players in ${
      Date.now() - started
    }ms\n`,
  );

  const server = createServer(graph);
  const transport = new StdioServerTransport();
  await server.connect(transport);
  process.stderr.write("[brazilian-soccer-mcp] listening on stdio\n");
}

main().catch((err) => {
  process.stderr.write(`[brazilian-soccer-mcp] fatal: ${err instanceof Error ? err.stack : String(err)}\n`);
  process.exit(1);
});
