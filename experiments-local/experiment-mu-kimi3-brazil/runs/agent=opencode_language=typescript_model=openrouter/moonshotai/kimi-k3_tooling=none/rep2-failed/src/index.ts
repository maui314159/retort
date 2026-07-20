#!/usr/bin/env node
/**
 * Entry point: start the Brazilian Soccer MCP server on stdio.
 */
import { main } from "./server.js";

main().catch((err) => {
  console.error("Fatal error starting brazilian-soccer-mcp:", err);
  process.exit(1);
});
