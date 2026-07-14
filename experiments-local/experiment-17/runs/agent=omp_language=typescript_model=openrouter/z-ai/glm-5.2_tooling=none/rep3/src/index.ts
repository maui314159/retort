#!/usr/bin/env node
/**
 * brazilian-soccer-mcp / src/index.ts
 *
 * Process entrypoint.
 *
 * Context block:
 * Boots the MCP server over the stdio transport. The server (built in
 * server.ts) is transport-agnostic; this file is the only place that binds it
 * to stdio, keeping the server construction testable. Datasets load lazily on
 * the first tool call, so startup is fast.
 */

import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { createServer } from './server.js';

async function main(): Promise<void> {
  const server = createServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err: unknown) => {
  console.error('Failed to start brazilian-soccer-mcp:', err);
  process.exit(1);
});
