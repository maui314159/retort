/**
 * Context
 * -------
 * Shared, lazily-built DataStore for the integration/BDD tests. Loading the six
 * CSVs takes a moment, so we memoize a single store instance across all test
 * files via a module-level promise. Tests treat this as the "Given the data is
 * loaded" precondition.
 */

import { loadStore, type DataStore } from "../src/store.js";

let storePromise: Promise<DataStore> | null = null;

export function getStore(): Promise<DataStore> {
  if (!storePromise) storePromise = loadStore();
  return storePromise;
}
