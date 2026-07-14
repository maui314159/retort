/**
 * Shared test fixtures: loads the real dataset once for all spec files.
 */

import { loadDataset, resolveDataDir } from '../src/loader.js';
import type { Dataset } from '../src/types.js';

let cached: Dataset | null = null;

/** Load (and cache) the real Kaggle dataset for tests. */
export function getTestDataset(): Dataset {
  if (!cached) {
    cached = loadDataset(resolveDataDir());
  }
  return cached;
}
