/**
 * Brazilian Soccer MCP Server - Entry Point
 * -----------------------------------------
 * Context: CLI entry point. Starts the MCP server on stdio. This file is
 * referenced by `npm start` and `package.json`'s "bin" if added.
 */

import { runStdio } from "./server.js";

runStdio().catch((err) => {
  console.error("Fatal error starting brazilian-soccer-mcp:", err);
  process.exit(1);
});
