/**
 * Feature: Statistical Analysis
 *
 * Aggregated statistics: goals per match, home vs away performance,
 * head-to-head records and the biggest wins in the dataset.
 */
import { describe, it, expect } from "vitest";
import { getDataset } from "./helpers.js";
import { biggestWins, competitionStats } from "../src/lib/queries.js";
import { Competition } from "../src/lib/types.js";

describe("Feature: Statistical Analysis", () => {
  it("Scenario: Average goals per match in the Brasileirão", () => {
    // Given the match data is loaded
    const { dataset } = getDataset();
    // When aggregated statistics are calculated for Série A
    const stats = competitionStats(dataset, Competition.BrasileiraoSerieA, null);
    // Then the average is in the historically expected range (2.4-2.7)
    expect(stats.avgGoalsPerMatch).toBeGreaterThan(2.3);
    expect(stats.avgGoalsPerMatch).toBeLessThan(2.8);
    // And home advantage is visible but not absolute
    expect(stats.homeWinRate).toBeGreaterThan(40);
    expect(stats.homeWinRate).toBeLessThan(60);
    expect(stats.homeWinRate + stats.drawRate + stats.awayWinRate).toBeCloseTo(100, 0);
    expect(stats.topScoringTeam).not.toBeNull();
  });

  it("Scenario: Season-filtered statistics", () => {
    const { dataset } = getDataset();
    const stats2019 = competitionStats(dataset, Competition.BrasileiraoSerieA, 2019);
    expect(stats2019.matches).toBe(380);
    const statsCup = competitionStats(dataset, Competition.CopaDoBrasil, null);
    expect(statsCup.matches).toBeGreaterThan(1000);
    expect(statsCup.avgGoalsPerMatch).toBeGreaterThan(1.5);
  });

  it("Scenario: Biggest wins in the dataset", () => {
    const { dataset } = getDataset();
    const wins = biggestWins(dataset, null, null, 10);
    expect(wins).toHaveLength(10);
    // Sorted by margin, then total goals.
    for (let i = 1; i < wins.length; i++) {
      expect(wins[i - 1].margin).toBeGreaterThanOrEqual(wins[i].margin);
    }
    // The largest margin on record: São Paulo 9-1 4 de Julho (2021 Copa do Brasil).
    expect(wins[0].margin).toBe(8);
    expect(wins[0].match.homeTeam.name).toBe("São Paulo");
    expect(wins[0].match.homeGoals).toBe(9);
    expect(wins[0].match.awayGoals).toBe(1);
    expect(wins[0].match.awayTeam.name).toBe("4 de Julho");
  });

  it("Scenario: Biggest wins filtered by competition", () => {
    const { dataset } = getDataset();
    const libWins = biggestWins(dataset, Competition.Libertadores, null, 5);
    expect(libWins.every((w) => w.match.competition === Competition.Libertadores)).toBe(true);
    expect(libWins[0].margin).toBeGreaterThanOrEqual(6);
    const serieAWins = biggestWins(dataset, Competition.BrasileiraoSerieA, null, 5);
    expect(serieAWins.every((w) => w.match.competition === Competition.BrasileiraoSerieA)).toBe(true);
  });

  it("Scenario: Home vs away performance comparison", () => {
    const { dataset } = getDataset();
    const stats = competitionStats(dataset, null, null);
    // Across the whole dataset home teams win more often than away teams.
    expect(stats.homeWinRate).toBeGreaterThan(stats.awayWinRate);
  });

  it("Scenario: Query performance stays within the success-criteria bounds", () => {
    const { dataset } = getDataset();
    // Simple lookups must answer in < 2s; aggregates in < 5s (spec §Success Criteria).
    const t0 = performance.now();
    competitionStats(dataset, null, null);
    biggestWins(dataset, null, null, 50);
    const elapsed = performance.now() - t0;
    expect(elapsed).toBeLessThan(2000);
  });
});
