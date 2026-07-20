/**
 * Shared test fixture: loads the real dataset once per test worker and
 * exposes it to the BDD scenarios (the files are the actual Kaggle CSVs
 * shipped in this repository).
 */
import { loadDataset, Dataset } from "../src/lib/dataset.js";
import { KnowledgeGraph } from "../src/lib/graph.js";

let cached: { dataset: Dataset; graph: KnowledgeGraph } | null = null;

export function getDataset(): { dataset: Dataset; graph: KnowledgeGraph } {
  if (!cached) {
    const dataset = loadDataset();
    cached = { dataset, graph: KnowledgeGraph.fromDataset(dataset) };
  }
  return cached;
}
