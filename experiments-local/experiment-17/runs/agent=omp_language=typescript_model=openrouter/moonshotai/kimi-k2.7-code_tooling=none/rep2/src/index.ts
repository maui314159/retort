#!/usr/bin/env node
/**
 * Brazilian Soccer MCP Server
 * Entry point: loads data and starts a stdio MCP server.
 */

import { startServer } from './server.js';

startServer().catch((err) => {
  console.error('Failed to start server:', err);
  process.exit(1);
});
