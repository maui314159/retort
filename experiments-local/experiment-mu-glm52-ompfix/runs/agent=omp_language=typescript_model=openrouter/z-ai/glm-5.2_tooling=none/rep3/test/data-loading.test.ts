/**
 * BDD Feature: Data Loading
 * -----------------------------------------------------------------------------
 * Verifies all six provided Kaggle CSV files load into the normalized model
 * with sane counts and provenance, satisfying the success criterion
 * "All 6 CSV files are loadable and queryable".
 */

import { describe, it, expect } from "vitest";
import { dataset } from "./helpers.js";

describe("Feature: Data Loading", () => {
  const ds = dataset();

  describe("Scenario: All six datasets are loaded", () => {
    // Given the six Kaggle CSV files in data/kaggle/
    // When the dataset is loaded
    // Then match and player counts reflect every file
    it("loads matches from all five match files plus players from fifa_data", () => {
      expect(ds.matches.length).toBeGreaterThan(23000);
      expect(ds.players.length).toBe(18207);
    });

    it("exposes a competition catalog with all sources", () => {
      const sources = new Set(ds.competitions.map((c) => c.source));
      expect(sources).toContain("Brasileirao_Matches");
      expect(sources).toContain("Brazilian_Cup_Matches");
      expect(sources).toContain("Libertadores_Matches");
      expect(sources).toContain("novo_campeonato_brasileiro");
      expect(sources).toContain("BR-Football-Dataset");
    });

    it("each competition lists its seasons", () => {
      const br = ds.competitions.find((c) => c.source === "Brasileirao_Matches");
      expect(br).toBeDefined();
      expect(br!.seasons).toContain(2012);
      expect(br!.seasons).toContain(2022);
    });
  });

  describe("Scenario: Every match carries provenance and a competition", () => {
    // Given the loaded matches
    // Then each has a non-empty source, competition, and normalized team names
    it("every match has source, competition, and normalized teams", () => {
      for (const m of ds.matches) {
        expect(m.source.length).toBeGreaterThan(0);
        expect(m.competition.length).toBeGreaterThan(0);
        expect(m.homeTeam.length).toBeGreaterThan(0);
        expect(m.awayTeam.length).toBeGreaterThan(0);
      }
    });

    it("the Libertadores NA-row (unscored final) is handled, not crashing", () => {
      const na = ds.matches.find((m) => m.source === "Libertadores_Matches" && m.season == null);
      expect(na).toBeDefined();
      expect(na!.homeGoals).toBeNull();
      expect(na!.awayGoals).toBeNull();
    });
  });
});
