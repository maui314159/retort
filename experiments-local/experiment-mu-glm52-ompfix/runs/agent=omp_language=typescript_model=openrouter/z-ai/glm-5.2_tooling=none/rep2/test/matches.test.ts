/**
 * Brazilian Soccer MCP Server — BDD match & team query tests
 * ----------------------------------------------------------
 * Context block:
 *   BDD (Given/When/Then) scenarios covering the Match Queries and Team
 *   Queries requirements from the spec. Each test exercises the query engine
 *   against the deterministic fixture dataset in fixtures.ts.
 */

import { describe, expect, it } from "vitest";
import { buildDataset } from "./fixtures.js";
import {
  queryMatches,
  teamStats,
  headToHead,
  bestRecord,
  topScoringTeams,
} from "../src/queries.js";

describe("Feature: Match Queries", () => {
  const ds = buildDataset();

  describe("Scenario: Find matches between two teams", () => {
    it("Given the match data is loaded, When I search for matches between Flamengo and Fluminense, Then I receive a list with date, scores and competition", () => {
      const results = queryMatches(ds, { team: "Flamengo", opponent: "Fluminense" });
      expect(results.length).toBe(2);
      for (const m of results) {
        expect(m.date).toBeTruthy();
        expect(typeof m.homeGoal).toBe("number");
        expect(typeof m.awayGoal).toBe("number");
        expect(m.competition).toBe("Brasileirão");
      }
      // Sorted newest first.
      expect(results[0].date).toBe("2023-09-03");
      expect(results[1].date).toBe("2023-05-28");
    });

    it("matches a team spelled with a state suffix", () => {
      // "Flamengo-RJ" must normalise to the same key as "Flamengo".
      const results = queryMatches(ds, { team: "Flamengo-RJ" });
      expect(results.length).toBeGreaterThanOrEqual(5);
    });
  });

  describe("Scenario: Find matches by season", () => {
    it("returns only 2023 matches for Palmeiras", () => {
      const results = queryMatches(ds, { team: "Palmeiras", season: 2023 });
      expect(results.length).toBe(3);
      expect(results.every((m) => m.season === 2023)).toBe(true);
    });
  });

  describe("Scenario: Find Copa do Brasil matches", () => {
    it("filters by competition label", () => {
      const results = queryMatches(ds, { competition: "Copa do Brasil" });
      expect(results.length).toBe(1);
      expect(results[0].competition).toBe("Copa do Brasil");
    });
  });

  describe("Scenario: Find Libertadores final", () => {
    it("filters by stage", () => {
      const results = queryMatches(ds, { competition: "Libertadores", stage: "final" });
      expect(results.length).toBe(1);
      expect(results[0].stage).toBe("final");
    });
  });
});

describe("Feature: Team Queries", () => {
  const ds = buildDataset();

  describe("Scenario: Get team statistics for a season", () => {
    it("Given match data, When I request statistics for Palmeiras in season 2023, Then I receive wins, losses, draws and goals", () => {
      const stats = teamStats(ds, { team: "Palmeiras", season: 2023 });
      // Palmeiras 2023: 3-0 vs São Paulo (W), 1-1 vs Corinthians (D), 0-5 vs Flamengo (L)
      expect(stats.matches).toBe(3);
      expect(stats.wins).toBe(1);
      expect(stats.draws).toBe(1);
      expect(stats.losses).toBe(1);
      expect(stats.goalsFor).toBe(4);
      expect(stats.goalsAgainst).toBe(6);
      expect(stats.points).toBe(4);
    });
  });

  describe("Scenario: Corinthians home record in 2022", () => {
    it("returns home-only statistics", () => {
      // No 2022 data for Corinthians in fixture → 0 matches, but shape correct.
      const stats = teamStats(ds, { team: "Corinthians", season: 2022, homeAway: "home" });
      expect(stats.matches).toBe(0);
      expect(stats.homeAway).toBe("home");
    });
  });

  describe("Scenario: Corinthians 2023 home record", () => {
    it("counts only home matches", () => {
      const stats = teamStats(ds, { team: "Corinthians", season: 2023, homeAway: "home" });
      expect(stats.matches).toBe(1);
      expect(stats.goalsFor).toBe(1);
      expect(stats.goalsAgainst).toBe(1);
    });
  });
});

describe("Feature: Head-to-Head", () => {
  const ds = buildDataset();

  describe("Scenario: Compare Palmeiras and Flamengo", () => {
    it("Given match data, When I compare Palmeiras and Flamengo head-to-head, Then I get wins/draws/goals", () => {
      // 2023 only: Flamengo 5-0 Palmeiras.
      const h2h = headToHead(ds, "Palmeiras", "Flamengo", 2023);
      expect(h2h.matches).toBe(1);
      expect(h2h.teamBWins).toBe(1); // Flamengo (teamB) won
      expect(h2h.teamAWins).toBe(0);
      expect(h2h.teamBGoals).toBe(5);
      expect(h2h.teamAGoals).toBe(0);
    });
  });

  describe("Scenario: Flamengo vs Fluminense head-to-head", () => {
    it("aggregates across both fixtures", () => {
      const h2h = headToHead(ds, "Flamengo", "Fluminense");
      expect(h2h.matches).toBe(2);
      expect(h2h.teamAWins).toBe(1); // Flamengo won 2-1
      expect(h2h.teamBWins).toBe(1); // Fluminense won 1-0
      expect(h2h.draws).toBe(0);
    });
  });
});

describe("Feature: Statistical Analysis", () => {
  const ds = buildDataset();

  describe("Scenario: Best home record in 2023", () => {
    it("returns teams sorted by home record", () => {
      const top = bestRecord(ds, { season: 2023, homeAway: "home" });
      expect(top.length).toBeGreaterThan(0);
      // Flamengo home: beat Fluminense 2-1, beat Palmeiras 5-0 → 6 pts.
      const flamengo = top.find((t) => t.team === "flamengo");
      expect(flamengo).toBeDefined();
      expect(flamengo!.points).toBe(6);
    });
  });

  describe("Scenario: Top scoring teams in 2023", () => {
    it("ranks teams by goals scored", () => {
      const top = topScoringTeams(ds, { season: 2023, limit: 3 });
      expect(top.length).toBeGreaterThan(0);
      // Flamengo scored 7 (2+5) in 2023.
      expect(top[0].team).toBe("flamengo");
      expect(top[0].goalsFor).toBe(7);
    });
  });
});
