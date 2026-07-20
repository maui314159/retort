/**
 * Shared application context: loads the dataset once and wires the
 * knowledge graph + query engine. Used by both the MCP server and tests.
 */

import { loadDataset, type Dataset } from "./loader.js";
import { buildGraph, type BuiltGraph } from "./graph.js";
import { createQueries, type SoccerQueries } from "./queries.js";

export interface AppContext {
  dataset: Dataset;
  built: BuiltGraph;
  queries: SoccerQueries;
}

let cached: AppContext | null = null;

export function getContext(dataDir?: string): AppContext {
  if (cached && !dataDir) return cached;
  const dataset = loadDataset(dataDir);
  const built = buildGraph(dataset.matches, dataset.players);
  const queries = createQueries(built, dataset.matches, dataset.players);
  const ctx: AppContext = { dataset, built, queries };
  if (!dataDir) cached = ctx;
  return ctx;
}
