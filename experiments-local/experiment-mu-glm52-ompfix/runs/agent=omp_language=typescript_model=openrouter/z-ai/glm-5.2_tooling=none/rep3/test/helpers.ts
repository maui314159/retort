/**
 * Brazilian Soccer MCP Server — Test dataset helper
 * -----------------------------------------------------------------------------
 * Loads the real Kaggle dataset once and shares it across all BDD test files,
 * so the ~33MB of CSV parsing happens a single time per test run.
 */

import { loadDataset } from "../src/data/loader.js";
import type { Dataset } from "../src/data/types.js";

let cached: Dataset | null = null;

/** The real dataset, parsed once and memoized for the whole test run. */
export function dataset(): Dataset {
  if (!cached) cached = loadDataset();
  return cached;
}
