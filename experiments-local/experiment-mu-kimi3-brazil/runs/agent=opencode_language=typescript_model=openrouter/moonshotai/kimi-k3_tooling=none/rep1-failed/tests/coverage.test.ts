/**
 * Feature: Data coverage
 *   All 6 CSV files are loadable and queryable; cross-file queries work.
 */
import { describe, it, expect } from "vitest";
import type { Dataset } from "../src/types.js";
import { givenDatasetLoaded } from "./helpers.js";

let ds: Dataset;
givenDatasetLoaded((d) => (ds = d));

describe("Feature: Data coverage", () => {
  it("Scenario: All 6 CSV files are loaded", () => {
    // Given the loader ran against data/kaggle
    // Then every expected file appears in the manifest
    const files = ds.loadedFiles.map((f) => f.file).sort();
    expect(files).toEqual([
      "BR-Football-Dataset.csv",
      "Brasileirao_Matches.csv",
      "Brazilian_Cup_Matches.csv",
      "Libertadores_Matches.csv",
      "fifa_data.csv",
      "novo_campeonato_brasileiro.csv",
    ]);
  });

  it("Scenario: Row counts match the documented sizes", () => {
    const byFile = new Map(ds.loadedFiles.map((f) => [f.file, f.rows]));
    expect(byFile.get("Brasileirao_Matches.csv")).toBe(4180);
    expect(byFile.get("Brazilian_Cup_Matches.csv")).toBe(1337);
    expect(byFile.get("Libertadores_Matches.csv")).toBe(1255);
    expect(byFile.get("BR-Football-Dataset.csv")).toBe(10296);
    expect(byFile.get("novo_campeonato_brasileiro.csv")).toBe(6886);
    expect(byFile.get("fifa_data.csv")).toBe(18207);
  });

  it("Scenario: Matches and players are materialized", () => {
    // Cross-file duplicates are merged, so the unique-match count is
    // lower than the raw row sum but still large.
    expect(ds.matches.length).toBeGreaterThan(10000);
    expect(ds.players.length).toBe(18207);
    expect(ds.teamIndex.size).toBeGreaterThan(100);
  });

  it("Scenario: Cross-file duplicates are merged into one node", () => {
    // The 2019 Brasileirão season exists in three source files;
    // after dedupe it must contain exactly the 380 real fixtures.
    const n = ds.matches.filter(
      (m) => m.competition === "Brasileirão Série A" && m.season === 2019,
    ).length;
    expect(n).toBe(380);
  });

  it("Scenario: Every match has a provenance tag", () => {
    for (const m of ds.matches) {
      expect(m.source).toBeTruthy();
      expect(m.id).toContain("#");
    }
  });

  it("Scenario: Cross-file team query aggregates all sources", () => {
    // When I look up Flamengo in the team index
    const keys = [...ds.teamIndex.keys()].filter((k) => k.includes("flamengo"));
    expect(keys.length).toBeGreaterThan(0);
    const idx = keys.flatMap((k) => ds.teamIndex.get(k)!);
    const sources = new Set(idx.map((i) => ds.matches[i].source));
    // Then matches come from multiple source files
    expect(sources.size).toBeGreaterThanOrEqual(3);
  });
});
