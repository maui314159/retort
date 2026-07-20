#!/usr/bin/env node
/**
 * Entry point: loads the datasets, builds the knowledge graph and serves
 * the MCP server over stdio.
 *
 * Usage:
 *   npm start                 # after `npm run build`
 *   DATA_DIR=/path node dist/index.js
 */
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { loadDataset } from "./lib/dataset.js";
import { KnowledgeGraph } from "./lib/graph.js";
import { createServer } from "./server.js";

async function main(): Promise<void> {
  const started = Date.now();
  const dataset = loadDataset();
  const graph = KnowledgeGraph.fromDataset(dataset);
  console.error(
    `[brazilian-soccer-mcp] loaded ${dataset.matches.length} matches, ` +
      `${dataset.players.length} players, ${dataset.teams.size} teams ` +
      `(${graph.nodes.size} graph nodes) in ${Date.now() - started}ms`,
  );

  const server = createServer(dataset, graph);
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  console.error("Fatal error starting brazilian-soccer-mcp:", err);
  process.exit(1);
});
