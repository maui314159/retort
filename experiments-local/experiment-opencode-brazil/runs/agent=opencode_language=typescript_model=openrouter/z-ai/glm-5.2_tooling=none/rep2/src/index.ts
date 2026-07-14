#!/usr/bin/env node
/**
 * Entry point: start the Brazilian Soccer MCP server over stdio.
 * Honors BR_SOCCER_DATA_DIR for the dataset location.
 */

import { runServer } from './server.js';

runServer().catch((err) => {
  console.error('Failed to start brazilian-soccer-mcp:', err);
  process.exit(1);
});
