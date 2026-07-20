#!/usr/bin/env node
/**
 * Entry point: loads the dataset and serves MCP over stdio.
 *
 * Usage:
 *   node dist/index.js [path-to-data/kaggle]
 *   SOCCER_DATA_DIR=/path/to/data/kaggle node dist/index.js
 */
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { loadDataset } from './dataset.js';
import { createServer } from './server.js';

async function main(): Promise<void> {
  const dataDir = process.argv[2] ?? process.env.SOCCER_DATA_DIR;
  const store = loadDataset(dataDir);
  console.error(
    `[brazilian-soccer-mcp] loaded ${store.dedupedMatches.length} matches, ` +
      `${store.teams.size} teams, ${store.players.length} players`,
  );
  const server = createServer(store);
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('[brazilian-soccer-mcp] serving MCP on stdio');
}

main().catch((error) => {
  console.error('Fatal error starting brazilian-soccer-mcp:', error);
  process.exit(1);
});
