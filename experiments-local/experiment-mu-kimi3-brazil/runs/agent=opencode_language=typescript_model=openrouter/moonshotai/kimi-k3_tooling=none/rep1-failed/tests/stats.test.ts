/**
 * Feature: Statistical Analysis
 *   Goals-per-match averages, home vs away performance,
 *   biggest victories, season comparisons.
 */
import { describe, it, expect } from "vitest";
import type { Dataset } from "../src/types.js";
import { givenDatasetLoaded } from "./helpers.js";
import {
  aggregateStats,
  bestVenueRecords,
  biggestWins,
} from "../src/services/stats.js";

let ds: Dataset;
givenDatasetLoaded((d) => (ds = d));

describe("Feature: Statistical Analysis", () => {
  it("Scenario: Average goals per match is realistic", () => {
    // When I ask for the average goals per match in the Brasileirão
    const s = aggregateStats(ds, { competition: "Brasileirão" });
    // Then the average is in the typical 2.0–3.0 range
    expect(s.matches).toBeGreaterThan(1000);
    expect(s.avgGoalsPerMatch).toBeGreaterThan(2.0);
    expect(s.avgGoalsPerMatch).toBeLessThan(3.0);
  });

  it("Scenario: Home advantage is visible", () => {
    // When I compute win rates
    const s = aggregateStats(ds, { competition: "Brasileirão Série A" });
    // Then home win rate beats away win rate
    expect(s.homeWinRate).toBeGreaterThan(s.awayWinRate);
    expect(s.homeWinRate).toBeGreaterThan(0.35);
  });

  it("Scenario: Result shares add up to 100%", () => {
    const s = aggregateStats(ds, {});
    expect(s.homeWins + s.draws + s.awayWins).toBe(s.matches);
    expect(s.homeWinRate + s.drawRate + s.awayWinRate).toBeCloseTo(1, 10);
  });

  it("Scenario: Biggest wins are sorted by margin", () => {
    // When I ask for the biggest victories in the dataset
    const wins = biggestWins(ds, { limit: 10 });
    expect(wins.length).toBe(10);
    // Then margins are descending and include the famous 8-0
    const margins = wins.map((m) => Math.abs(m.homeGoals - m.awayGoals));
    expect(margins[0]).toBeGreaterThanOrEqual(8);
    for (let i = 1; i < margins.length; i++) {
      expect(margins[i - 1]).toBeGreaterThanOrEqual(margins[i]);
    }
  });

  it("Scenario: Biggest wins can be scoped to a competition", () => {
    const wins = biggestWins(ds, { competition: "Libertadores", limit: 5 });
    for (const m of wins) expect(m.competition).toBe("Copa Libertadores");
  });

  it("Scenario: Best home records by win rate", () => {
    // When I ask which team has the best home record
    const rows = bestVenueRecords(ds, "home", { minMatches: 50, limit: 10 });
    // Then the ranking is sorted by win rate and stats are consistent
    expect(rows.length).toBeGreaterThan(0);
    for (let i = 1; i < rows.length; i++) {
      expect(rows[i - 1].winRate).toBeGreaterThanOrEqual(rows[i].winRate);
    }
    for (const r of rows) {
      expect(r.wins + r.draws + r.losses).toBe(r.played);
    }
  });

  it("Scenario: Best away records by win rate", () => {
    const rows = bestVenueRecords(ds, "away", { minMatches: 50, limit: 10 });
    expect(rows.length).toBeGreaterThan(0);
    expect(rows[0].winRate).toBeGreaterThan(0.3);
  });

  it("Scenario: Compare two seasons side by side", () => {
    // When I compare the 2018 and 2019 Brasileirão seasons
    const s18 = aggregateStats(ds, { competition: "Brasileirão", season: 2018 });
    const s19 = aggregateStats(ds, { competition: "Brasileirão", season: 2019 });
    // Then both seasons have full-ish data and comparable magnitudes
    expect(s18.matches).toBeGreaterThan(300);
    expect(s19.matches).toBeGreaterThan(300);
    expect(Math.abs(s18.avgGoalsPerMatch - s19.avgGoalsPerMatch)).toBeLessThan(1);
  });
});
