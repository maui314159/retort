#!/usr/bin/env node
/**
 * brazilian-soccer-mcp — stdio entrypoint.
 *
 * Context: This is the executable launched by an MCP client (or `npm start`).
 * It resolves the dataset directory (defaulting to `./data/kaggle` relative to
 * the package root) and starts the MCP server over stdio.
 */

import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { dirname } from "node:path";
import { runServer } from "./server.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

async function main(): Promise<void> {
  const dataDir = resolve(process.env.DATA_DIR ?? `${__dirname}/../data/kaggle`);
  await runServer(dataDir);
}

main().catch((error) => {
  console.error("Fatal:", error);
  process.exit(1);
});
