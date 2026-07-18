/**
 * BDD Feature: Statistical Analysis
 * -----------------------------------------------------------------------------
 * Covers the spec's "Statistical Analysis" category: goals-per-match averages,
 * home vs away win rates, and biggest victories. Assertions are grounded in the
 * computed 2019 Brasileirão totals.
 */

import { describe, it, expect } from "vitest";
import { dataset } from "./helpers.js";
import { matchStatistics, biggestWins } from "../src/data/query.js";

describe("Feature: Statistical Analysis", () => {
  const ds = dataset();

  describe("Scenario: Average goals per match in the Brasileirão", () => {
    it("computes aggregate statistics for a season", () => {
      const stats = matchStatistics(ds, { competition: "brasileirao", season: 2019 });
      expect(stats.scoredMatches).toBe(380);
      expect(stats.matches).toBe(380);
      expect(stats.totalGoals).toBe(876);
      expect(stats.averageGoals).toBeCloseTo(2.31, 2);
      expect(stats.homeWins + stats.awayWins + stats.draws).toBe(stats.scoredMatches);
    });

    it("home win rate exceeds away win rate (typical home advantage)", () => {
      const stats = matchStatistics(ds, { competition: "brasileirao" });
      expect(stats.homeWinRate).toBeGreaterThan(stats.awayWinRate);
    });
  });

  describe("Scenario: Biggest wins in the dataset", () => {
    it("returns matches sorted by descending goal margin", () => {
      const wins = biggestWins(ds, { competition: "brasileirao" }, 5);
      expect(wins.length).toBe(5);
      for (const m of wins) {
        expect(m.homeGoals != null && m.awayGoals != null).toBe(true);
      }
      // Largest margin first; all Brasileirão max margins are 6 goals.
      const margins = wins.map((m) => Math.abs((m.homeGoals ?? 0) - (m.awayGoals ?? 0)));
      for (let i = 1; i < margins.length; i++) {
        expect(margins[i - 1]).toBeGreaterThanOrEqual(margins[i]);
      }
    });

    it("the largest Brasileirão victory margin is 6 goals", () => {
      const wins = biggestWins(ds, { competition: "brasileirao" }, 1);
      const margin = Math.abs((wins[0].homeGoals ?? 0) - (wins[0].awayGoals ?? 0));
      expect(margin).toBe(6);
    });
  });

  describe("Scenario: Scoped statistics by team", () => {
    it("computes statistics restricted to a single team's matches", () => {
      const stats = matchStatistics(ds, { competition: "brasileirao", season: 2019, team: "Flamengo" });
      expect(stats.matches).toBe(38);
      // Flamengo scored 86 and conceded 37 in 2019.
      // homeWins+awayWins+draws should equal 38.
      expect(stats.homeWins + stats.awayWins + stats.draws).toBe(stats.scoredMatches);
    });
  });
});
