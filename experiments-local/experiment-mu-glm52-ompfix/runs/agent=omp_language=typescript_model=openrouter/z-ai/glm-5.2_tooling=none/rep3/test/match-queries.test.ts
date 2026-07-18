/**
 * BDD Feature: Match Queries
 * -----------------------------------------------------------------------------
 * Covers the spec's "Match Queries" category: find matches by team, opponent,
 * date range, competition, season, and stage. Mirrors the Gherkin scenarios:
 *   Given the match data is loaded
 *   When I search for matches between "Flamengo" and "Fluminense"
 *   Then I should receive a list of matches with date, scores, and competition
 */

import { describe, it, expect } from "vitest";
import { dataset } from "./helpers.js";
import { findMatches, headToHead, lastMatch } from "../src/data/query.js";

describe("Feature: Match Queries", () => {
  const ds = dataset();

  describe('Scenario: Find matches between two teams', () => {
    // Given the match data is loaded
    // When I search for matches between "Flamengo" and "Fluminense"
    // Then I should receive a list of matches with date, scores, and competition
    it("returns matches where both teams appear (either venue)", () => {
      const matches = findMatches(ds, { team: "Flamengo", opponent: "Fluminense", competition: "brasileirao" });
      expect(matches.length).toBeGreaterThan(0);
      for (const m of matches) {
        const hasFla = m.homeTeam.includes("Flamengo") || m.awayTeam.includes("Flamengo");
        const hasFlu = m.homeTeam.includes("Fluminense") || m.awayTeam.includes("Fluminense");
        expect(hasFla && hasFlu).toBe(true);
        expect(m.date).toBeTruthy();
        expect(m.competition).toBe("brasileirao");
      }
    });

    it("tolerates team-name variations (suffix, accents)", () => {
      // "Flamengo" must match the stored "Flamengo-RJ".
      const matches = findMatches(ds, { team: "Flamengo", competition: "brasileirao", season: 2019 });
      expect(matches.length).toBeGreaterThan(0);
      for (const m of matches) {
        expect(m.homeTeam.includes("Flamengo") || m.awayTeam.includes("Flamengo")).toBe(true);
      }
    });
  });

  describe("Scenario: Filter by competition and season", () => {
    it("returns only Copa do Brasil 2018 matches", () => {
      const matches = findMatches(ds, { competition: "copa-do-brasil", season: 2018 });
      expect(matches.length).toBeGreaterThan(0);
      for (const m of matches) {
        expect(m.competition).toBe("copa-do-brasil");
        expect(m.season).toBe(2018);
      }
    });

    it("returns Libertadores finals (stage = final)", () => {
      const finals = findMatches(ds, { competition: "libertadores", stage: "final" });
      expect(finals.length).toBeGreaterThan(0);
      for (const m of finals) expect(m.stage).toBe("final");
    });
  });

  describe("Scenario: Filter by date range", () => {
    it("returns matches within an ISO date range", () => {
      const matches = findMatches(ds, {
        competition: "brasileirao", season: 2019,
        from: "2019-06-01", to: "2019-06-30",
      });
      expect(matches.length).toBeGreaterThan(0);
      for (const m of matches) {
        expect(m.date! >= "2019-06-01").toBe(true);
        expect(m.date! <= "2019-06-30").toBe(true);
      }
    });
  });

  describe("Scenario: Head-to-head summary", () => {
    it("computes wins/draws/goals for two teams", () => {
      const h2h = headToHead(ds, "Flamengo", "Fluminense", { competition: "brasileirao" });
      expect(h2h.played).toBeGreaterThan(0);
      expect(h2h.team1Wins + h2h.team2Wins + h2h.draws).toBe(h2h.played);
      expect(h2h.team1Goals).toBeGreaterThanOrEqual(0);
      expect(h2h.team2Goals).toBeGreaterThanOrEqual(0);
    });

    it("is symmetric regardless of argument order", () => {
      const a = headToHead(ds, "Palmeiras", "Santos", { competition: "brasileirao" });
      const b = headToHead(ds, "Santos", "Palmeiras", { competition: "brasileirao" });
      expect(a.played).toBe(b.played);
      expect(a.team1Wins).toBe(b.team2Wins);
      expect(a.team2Wins).toBe(b.team1Wins);
    });
  });

  describe('Scenario: When did Flamengo last play Corinthians?', () => {
    it("returns the most recent match between the two teams", () => {
      const m = lastMatch(ds, "Flamengo", { opponent: "Corinthians" });
      expect(m).not.toBeNull();
      const hasFla = m!.homeTeam.includes("Flamengo") || m!.awayTeam.includes("Flamengo");
      const hasCor = m!.homeTeam.includes("Corinthians") || m!.awayTeam.includes("Corinthians");
      expect(hasFla && hasCor).toBe(true);
    });
  });
});
