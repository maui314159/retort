/*
 * Brazilian Soccer MCP Server - main entrypoint
 *
 * Loads the provided Kaggle CSV datasets and exposes a Model Context Protocol
 * (MCP) server via stdio.
 */

import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { loadDataset } from './loader.js';
import { QueryEngine } from './engine.js';
import { createServer } from './server.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const DATA_DIR = process.env.BRAZILIAN_SOCCER_DATA_DIR ?? resolve(__dirname, '..', 'data', 'kaggle');

async function main() {
  const store = await loadDataset(DATA_DIR);
  const engine = new QueryEngine(store);
  const server = createServer(engine);
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((error) => {
  console.error('Fatal error starting Brazilian Soccer MCP server:', error);
  process.exit(1);
});
