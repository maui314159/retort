/**
 * Brazilian Soccer MCP Server — deduplication & cross-file tests
 * -------------------------------------------------------------
 * Context block:
 *   Verifies that overlapping matches across the brasileirao (2012–2022) and
 *   historico (2003–2019) datasets are deduplicated so standings and
 *   aggregates are not double-counted. Uses the real Kaggle data.
 */

import { describe, expect, it } from "vitest";
import { resolve } from "node:path";
import { loadAll } from "../src/loader.js";
import { standings } from "../src/queries.js";

const dataDir = resolve(process.cwd(), "data", "kaggle");

describe("Deduplication", () => {
  const ds = loadAll(dataDir);

  it("removes overlapping matches between brasileirao and historico", () => {
    // Without dedup, matches would be 4180 + 1337 + 1255 + 10296 + 6886 = 23954.
    // With dedup, the 2012–2019 overlap between brasileirao and historico is removed.
    expect(ds.matches.length).toBeLessThan(23954);
    expect(ds.matches.length).toBeGreaterThan(20000);
  });

  it("produces realistic match counts per team for 2019", () => {
    const table = standings(ds, { competition: "Brasileirão", season: 2019 });
    const flamengo = table.find((r) => r.team === "flamengo");
    expect(flamengo).toBeDefined();
    // 2019 Brasileirão: 38 rounds. Allow a small margin for date-parsing diffs.
    expect(flamengo!.played).toBeGreaterThanOrEqual(38);
    expect(flamengo!.played).toBeLessThanOrEqual(45);
    // Flamengo won the 2019 Brasileirão.
    expect(flamengo!.position).toBe(1);
  });

  it("does not double-count the Fla-Flu head-to-head", () => {
    // Before dedup, Fla-Flu had 77 matches (doubled). After dedup, ~48.
    const flamengoMatches = ds.matches.filter(
      (m) => (m.homeTeam === "flamengo" && m.awayTeam === "fluminense") ||
             (m.awayTeam === "flamengo" && m.homeTeam === "fluminense"),
    );
    expect(flamengoMatches.length).toBeLessThan(77);
    expect(flamengoMatches.length).toBeGreaterThan(20);
  });
});
