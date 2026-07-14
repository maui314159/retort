/**
 * Entry point for the Brazilian Soccer MCP server.
 *
 * Loads all CSV datasets into memory, builds the query store, and connects
 * the MCP server over stdio.
 */

import { resolve } from "node:path";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { loadAllData } from "./loaders.js";
import { SoccerStore } from "./store.js";
import { createSoccerServer } from "./server.js";

async function main(): Promise<void> {
  const dataDir = resolve(process.env.DATA_DIR ?? "data/kaggle");
  const data = await loadAllData(dataDir);
  const store = new SoccerStore(data);

  // eslint-disable-next-line no-console
  console.error(
    `Loaded ${store.matches.length} matches and ${store.players.length} players from ${dataDir}`
  );

  const server = createSoccerServer(store);
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  // eslint-disable-next-line no-console
  console.error("Fatal error starting Brazilian Soccer MCP server:", err);
  process.exit(1);
});
