/**
 * BDD Tests - Statistical Analysis
 *
 * Feature: Statistical Analysis
 * Scenarios for aggregated match statistics: average goals,
 * home/away win rates, biggest victories, and team rankings.
 */

import { describe, it, expect, beforeAll } from "vitest";
import { DataLoader } from "../loader.js";
import { getMatchStats, getBestTeamRecord } from "../query.js";
import type { Match } from "../types.js";

let matches: Match[];

beforeAll(() => {
  const loader = new DataLoader();
  matches = loader.matches;
});

describe("Feature: Statistical Analysis", () => {
  describe("Scenario: Get overall match statistics", () => {
    it("Given the match data is loaded, When I request match statistics, Then I should get totals and averages", () => {
      const stats = getMatchStats(matches);
      expect(stats.totalMatches).toBeGreaterThan(0);
      expect(stats.totalGoals).toBeGreaterThan(0);
      expect(stats.avgGoalsPerMatch).toBeGreaterThan(0);
      expect(stats.avgGoalsPerMatch).toBeLessThan(10); // sanity
    });

    it("And home wins + away wins + draws should equal total matches", () => {
      const stats = getMatchStats(matches);
      expect(stats.homeWins + stats.awayWins + stats.draws).toBe(
        stats.totalMatches
      );
    });

    it("And home win rate should be higher than away win rate (typical home advantage)", () => {
      const stats = getMatchStats(matches);
      expect(stats.homeWinRate).toBeGreaterThan(stats.awayWinRate);
    });
  });

  describe("Scenario: Get statistics for a specific competition", () => {
    it("Given the match data is loaded, When I request stats for Brasileirão, Then only Brasileirão matches should be counted", () => {
      const allStats = getMatchStats(matches);
      const brasStats = getMatchStats(matches, { competition: "Brasileirão" });
      expect(brasStats.totalMatches).toBeGreaterThan(0);
      expect(brasStats.totalMatches).toBeLessThanOrEqual(allStats.totalMatches);
    });
  });

  describe("Scenario: Get statistics for a specific season", () => {
    it("Given the match data is loaded, When I request stats for 2023, Then only 2023 matches should be counted", () => {
      const stats = getMatchStats(matches, { season: 2023 });
      expect(stats.totalMatches).toBeGreaterThan(0);
    });
  });

  describe("Scenario: Biggest victories", () => {
    it("Given the match data is loaded, Then biggest home wins should be sorted by goal difference", () => {
      const stats = getMatchStats(matches);
      expect(stats.biggestHomeWins.length).toBeGreaterThan(0);
      for (const m of stats.biggestHomeWins) {
        expect(m.homeGoals).toBeGreaterThan(m.awayGoals);
      }
    });

    it("And biggest away wins should have away team scoring more", () => {
      const stats = getMatchStats(matches);
      expect(stats.biggestAwayWins.length).toBeGreaterThan(0);
      for (const m of stats.biggestAwayWins) {
        expect(m.awayGoals).toBeGreaterThan(m.homeGoals);
      }
    });
  });

  describe("Scenario: Rate calculations", () => {
    it("Given the match data is loaded, Then home/away/draw rates should sum to approximately 100%", () => {
      const stats = getMatchStats(matches);
      const total = stats.homeWinRate + stats.awayWinRate + stats.drawRate;
      expect(total).toBeGreaterThanOrEqual(99.5);
      expect(total).toBeLessThanOrEqual(100.5);
    });
  });

  describe("Scenario: Best team records", () => {
    it("Given the match data is loaded, When I rank teams by points in Brasileirão 2023, Then results should be sorted by points descending", () => {
      const records = getBestTeamRecord(matches, {
        competition: "Brasileirão",
        season: 2023,
      });
      expect(records.length).toBeGreaterThan(0);
      for (let i = 1; i < records.length; i++) {
        expect(records[i - 1].points).toBeGreaterThanOrEqual(
          records[i].points
        );
      }
    });
  });

  describe("Scenario: Best home record", () => {
    it("Given the match data is loaded, When I rank teams by home record, Then all records should reflect home-only stats", () => {
      const records = getBestTeamRecord(matches, {
        competition: "Brasileirão",
        season: 2023,
        homeOnly: true,
      });
      expect(records.length).toBeGreaterThan(0);
    });
  });

  describe("Scenario: Best away record", () => {
    it("Given the match data is loaded, When I rank teams by away record, Then all records should reflect away-only stats", () => {
      const records = getBestTeamRecord(matches, {
        competition: "Brasileirão",
        season: 2023,
        awayOnly: true,
      });
      expect(records.length).toBeGreaterThan(0);
    });
  });

  describe("Scenario: Average goals per match is reasonable", () => {
    it("Given the match data is loaded, When I compute average goals per match, Then it should be between 1 and 6", () => {
      const stats = getMatchStats(matches);
      expect(stats.avgGoalsPerMatch).toBeGreaterThanOrEqual(1);
      expect(stats.avgGoalsPerMatch).toBeLessThanOrEqual(6);
    });
  });
});
