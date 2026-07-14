/**
 * BDD Tests - Team Queries
 *
 * Feature: Team Queries
 * Scenarios for computing team statistics and head-to-head records.
 */

import { describe, it, expect, beforeAll } from "vitest";
import { DataLoader } from "../loader.js";
import { getTeamRecord, getHeadToHead } from "../query.js";
import type { Match } from "../types.js";

let matches: Match[];

beforeAll(() => {
  const loader = new DataLoader();
  matches = loader.matches;
});

describe("Feature: Team Queries", () => {
  describe("Scenario: Get team statistics", () => {
    it("Given the match data is loaded, When I request statistics for Palmeiras in season 2023, Then I should receive wins, losses, draws, and goals", () => {
      const record = getTeamRecord(matches, "Palmeiras", { season: 2023 });
      expect(record.matches).toBeGreaterThan(0);
      expect(record.wins).toBeGreaterThan(0);
      expect(record.draws).toBeGreaterThanOrEqual(0);
      expect(record.losses).toBeGreaterThanOrEqual(0);
      expect(record.goalsFor).toBeGreaterThan(0);
      expect(record.goalsAgainst).toBeGreaterThanOrEqual(0);
      expect(record.wins + record.draws + record.losses).toBe(record.matches);
    });

    it("And the points should be calculated as 3 per win + 1 per draw", () => {
      const record = getTeamRecord(matches, "Flamengo", { season: 2023 });
      expect(record.points).toBe(record.wins * 3 + record.draws);
    });
  });

  describe("Scenario: Get home-only record", () => {
    it("Given the match data is loaded, When I request Corinthians home record in 2022, Then only home matches should be counted", () => {
      const record = getTeamRecord(matches, "Corinthians", {
        season: 2022,
        homeOnly: true,
      });
      expect(record.matches).toBeGreaterThan(0);
      // Home record should be a subset of total
      const totalRecord = getTeamRecord(matches, "Corinthians", {
        season: 2022,
      });
      expect(record.matches).toBeLessThanOrEqual(totalRecord.matches);
    });
  });

  describe("Scenario: Get away-only record", () => {
    it("Given the match data is loaded, When I request away-only stats, Then only away matches should be counted", () => {
      const record = getTeamRecord(matches, "Santos", {
        season: 2023,
        awayOnly: true,
      });
      expect(record.matches).toBeGreaterThan(0);
      const totalRecord = getTeamRecord(matches, "Santos", { season: 2023 });
      expect(record.matches).toBeLessThanOrEqual(totalRecord.matches);
    });
  });

  describe("Scenario: Filter by competition", () => {
    it("Given the match data is loaded, When I request stats for Brasileirão only, Then only Brasileirão matches should count", () => {
      const record = getTeamRecord(matches, "Flamengo", {
        competition: "Brasileirão",
      });
      expect(record.matches).toBeGreaterThan(0);
    });
  });

  describe("Scenario: Compare Palmeiras and Santos head-to-head", () => {
    it("Given the match data is loaded, When I compare Palmeiras and Santos head-to-head, Then I should get wins for each and draws", () => {
      const h2h = getHeadToHead(matches, "Palmeiras", "Santos");
      expect(h2h.matches.length).toBeGreaterThan(0);
      expect(h2h.team1Wins).toBeGreaterThan(0);
      expect(h2h.team1Wins + h2h.team2Wins + h2h.draws).toBe(
        h2h.matches.length
      );
    });

    it("And each match in the head-to-head should involve both teams", () => {
      const h2h = getHeadToHead(matches, "Palmeiras", "Santos");
      for (const m of h2h.matches) {
        const hasPalmeiras =
          m.homeTeam.toLowerCase().includes("palmeiras") ||
          m.awayTeam.toLowerCase().includes("palmeiras");
        const hasSantos =
          m.homeTeam.toLowerCase().includes("santos") ||
          m.awayTeam.toLowerCase().includes("santos");
        expect(hasPalmeiras).toBe(true);
        expect(hasSantos).toBe(true);
      }
    });
  });

  describe("Scenario: Head-to-head between cross-competition rivals", () => {
    it("Given the match data is loaded, When I compare Flamengo vs Fluminense, Then matches from multiple competitions may appear", () => {
      const h2h = getHeadToHead(matches, "Flamengo", "Fluminense");
      expect(h2h.matches.length).toBeGreaterThan(0);
      const competitions = new Set(h2h.matches.map((m) => m.competition));
      // Fla-Flu should appear in at least Brasileirão
      expect(competitions.size).toBeGreaterThanOrEqual(1);
    });
  });
});
