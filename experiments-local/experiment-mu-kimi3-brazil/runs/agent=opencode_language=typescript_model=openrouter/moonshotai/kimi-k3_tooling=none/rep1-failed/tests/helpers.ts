/**
 * Shared test fixture: loads the real Kaggle datasets once per worker.
 */
import { beforeAll } from "vitest";
import path from "node:path";
import { loadDataset } from "../src/loader.js";
import type { Dataset } from "../src/types.js";

export const DATA_DIR = path.resolve(__dirname, "..", "data", "kaggle");

let cache: Dataset | null = null;

export async function getDataset(): Promise<Dataset> {
  if (!cache) cache = await loadDataset(DATA_DIR);
  return cache;
}

/** BDD "Given the match data is loaded" — call inside describe blocks. */
export function givenDatasetLoaded(set: (ds: Dataset) => void): void {
  beforeAll(async () => {
    set(await getDataset());
  });
}
