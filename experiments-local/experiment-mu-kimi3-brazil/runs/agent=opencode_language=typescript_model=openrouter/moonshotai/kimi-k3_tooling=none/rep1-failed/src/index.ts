#!/usr/bin/env node
/**
 * Entry point: loads the datasets and serves the MCP server over stdio.
 *
 * Usage:
 *   npm run build && npm start
 *   npx tsx src/index.ts            # dev mode
 *
 * Environment:
 *   DATA_DIR — override the data/kaggle directory location.
 */
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { loadDataset, DEFAULT_DATA_DIR } from "./loader.js";
import { createServer } from "./server.js";

async function main(): Promise<void> {
  const dataDir = process.env.DATA_DIR ?? DEFAULT_DATA_DIR;
  console.error(`[brazilian-soccer-mcp] loading data from ${dataDir} ...`);
  const t0 = Date.now();
  const dataset = await loadDataset(dataDir);
  console.error(
    `[brazilian-soccer-mcp] loaded ${dataset.matches.length} matches and ` +
      `${dataset.players.length} players from ${dataset.loadedFiles.length} files ` +
      `in ${Date.now() - t0}ms`,
  );

  const server = createServer(dataset);
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("[brazilian-soccer-mcp] server running on stdio");
}

main().catch((err) => {
  console.error("[brazilian-soccer-mcp] fatal:", err);
  process.exit(1);
});
