#!/usr/bin/env node
/**
 * Brazilian Soccer MCP Server — Entry point.
 *
 * Context block
 * -------------
 * Boots an MCP server over stdio that exposes the Brazilian soccer knowledge
 * graph (matches, teams, players, competitions) to any MCP-compatible LLM
 * client (Claude Desktop, etc.). On startup it loads all six Kaggle CSVs from
 * `data/kaggle/` into memory once, then registers the query tools. The data
 * directory can be overridden with the BRAZILIAN_SOCCER_DATA_DIR env var.
 *
 * Run:
 *   npm run build && node dist/index.js
 *   # or, for development:
 *   bun run src/index.ts
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { DEFAULT_DATA_DIR, loadDataset } from "./data/loader.js";
import { registerTools } from "./tools.js";

async function main(): Promise<void> {
  const dataDir = process.env.BRAZILIAN_SOCCER_DATA_DIR ?? DEFAULT_DATA_DIR;
  const dataset = loadDataset(dataDir);

  const server = new McpServer(
    {
      name: "brazilian-soccer-mcp",
      version: "1.0.0",
    },
    {
      instructions:
        "Brazilian soccer knowledge graph. Query matches, teams, players, and competitions across " +
        `${dataset.matches.length} matches and ${dataset.players.length} FIFA players. ` +
        "Team names accept variants (e.g. 'Palmeiras-SP' == 'Palmeiras'). Use list_teams to resolve names first.",
    },
  );

  registerTools(server, dataset);

  const transport = new StdioServerTransport();
  await server.connect(transport);
  // Keep process alive; transport handles stdin.
  process.stderr.write(
    `[brazilian-soccer-mcp] ready: ${dataset.matches.length} matches, ${dataset.players.length} players loaded from ${dataDir}\n`,
  );
}

main().catch((err) => {
  process.stderr.write(`Fatal: ${err instanceof Error ? err.stack ?? err.message : String(err)}\n`);
  process.exit(1);
});
