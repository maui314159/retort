/**
 * Shared test fixture: loads the dataset once per test process and exposes
 * the query engine. Mirrors the BDD "Given the data is loaded" step.
 */

import { getContext, type AppContext } from "../src/context.js";
import type { SoccerQueries } from "../src/queries.js";

let ctx: AppContext | null = null;

/** Given the match and player data is loaded */
export function givenDataLoaded(): AppContext {
  if (!ctx) ctx = getContext();
  return ctx;
}

export function givenQueries(): SoccerQueries {
  return givenDataLoaded().queries;
}
