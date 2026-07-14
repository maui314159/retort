/**
 * Entry point for the Brazilian Soccer MCP server.
 *
 * Loads the datasets and starts a stdio-backed MCP server. Intended to be
 * invoked as an MCP subprocess from a compatible host.
 */

import { runServer } from "./server.js";

await runServer();
