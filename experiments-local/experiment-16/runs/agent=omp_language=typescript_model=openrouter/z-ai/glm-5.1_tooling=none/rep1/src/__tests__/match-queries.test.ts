/**
 * BDD Tests - Match Queries
 *
 * Feature: Match Queries
 * Scenarios for searching matches by team, opponent, competition, season,
 * and date range using the searchMatches function.
 */

import { describe, it, expect, beforeAll } from "vitest";
import { DataLoader, normalizeTeamName, parseDate } from "../loader.js";
import { searchMatches } from "../query.js";
import type { Match } from "../types.js";

let matches: Match[];

beforeAll(() => {
  const loader = new DataLoader();
  matches = loader.matches;
});

describe("Feature: Match Queries", () => {
  describe("Scenario: Find matches between two teams", () => {
    it("Given the match data is loaded, When I search for matches between Flamengo and Fluminense, Then I should receive a list of matches", () => {
      const result = searchMatches(matches, {
        team: "Flamengo",
        opponent: "Fluminense",
      });
      expect(result.length).toBeGreaterThan(0);
    });

    it("And each match should have one team matching Flamengo and the other Fluminense", () => {
      const result = searchMatches(matches, {
        team: "Flamengo",
        opponent: "Fluminense",
      });
      for (const m of result) {
        const hasFlamengo =
          m.homeTeam.toLowerCase().includes("flamengo") ||
          m.awayTeam.toLowerCase().includes("flamengo");
        const hasFluminense =
          m.homeTeam.toLowerCase().includes("fluminense") ||
          m.awayTeam.toLowerCase().includes("fluminense");
        expect(hasFlamengo).toBe(true);
        expect(hasFluminense).toBe(true);
      }
    });

    it("And each match should have date, scores, and competition", () => {
      const result = searchMatches(matches, {
        team: "Flamengo",
        opponent: "Fluminense",
      });
      for (const m of result) {
        expect(m.date).toBeTruthy();
        expect(typeof m.homeGoals).toBe("number");
        expect(typeof m.awayGoals).toBe("number");
        expect(m.competition).toBeTruthy();
      }
    });
  });

  describe("Scenario: Find matches by team name", () => {
    it("Given the match data is loaded, When I search for Palmeiras matches, Then I should receive matches where Palmeiras played home or away", () => {
      const result = searchMatches(matches, { team: "Palmeiras" });
      expect(result.length).toBeGreaterThan(0);
      for (const m of result) {
        const isPalmeiras =
          m.homeTeam.toLowerCase().includes("palmeiras") ||
          m.awayTeam.toLowerCase().includes("palmeiras");
        expect(isPalmeiras).toBe(true);
      }
    });
  });

  describe("Scenario: Filter matches by competition", () => {
    it("Given the match data is loaded, When I search for Copa do Brasil matches, Then all results should be from Copa do Brasil", () => {
      const result = searchMatches(matches, { competition: "Copa do Brasil" });
      expect(result.length).toBeGreaterThan(0);
      for (const m of result) {
        expect(m.competition.toLowerCase()).toContain("copa do brasil");
      }
    });

    it("When I search for Libertadores matches, Then all results should be from Copa Libertadores", () => {
      const result = searchMatches(matches, { competition: "Libertadores" });
      expect(result.length).toBeGreaterThan(0);
      for (const m of result) {
        expect(m.competition.toLowerCase()).toContain("libertadores");
      }
    });
  });

  describe("Scenario: Filter matches by season", () => {
    it("Given the match data is loaded, When I search for matches in 2023, Then all results should have season 2023", () => {
      const result = searchMatches(matches, { season: 2023 });
      expect(result.length).toBeGreaterThan(0);
      for (const m of result) {
        expect(m.season).toBe(2023);
      }
    });
  });

  describe("Scenario: Filter matches by date range", () => {
    it("Given the match data is loaded, When I search for matches in 2023-01-01 to 2023-06-30, Then all results should be within that range", () => {
      const result = searchMatches(matches, {
        dateFrom: "2023-01-01",
        dateTo: "2023-06-30",
      });
      expect(result.length).toBeGreaterThan(0);
      for (const m of result) {
        expect(m.date >= "2023-01-01").toBe(true);
        expect(m.date <= "2023-06-30").toBe(true);
      }
    });
  });

  describe("Scenario: Combine multiple filters", () => {
    it("Given the match data is loaded, When I search for Palmeiras in Brasileirão 2022, Then results should match all criteria", () => {
      const result = searchMatches(matches, {
        team: "Palmeiras",
        competition: "Brasileirão",
        season: 2022,
      });
      expect(result.length).toBeGreaterThan(0);
      for (const m of result) {
        const isPalmeiras =
          m.homeTeam.toLowerCase().includes("palmeiras") ||
          m.awayTeam.toLowerCase().includes("palmeiras");
        expect(isPalmeiras).toBe(true);
        expect(m.competition).toBe("Brasileirão");
        expect(m.season).toBe(2022);
      }
    });
  });

  describe("Scenario: Limit results", () => {
    it("Given the match data is loaded, When I search with a limit of 5, Then I should receive at most 5 results", () => {
      const result = searchMatches(matches, { team: "Flamengo", limit: 5 });
      expect(result.length).toBeLessThanOrEqual(5);
    });
  });

  describe("Scenario: Results sorted by date descending", () => {
    it("Given the match data is loaded, When I search for matches, Then results should be sorted most recent first", () => {
      const result = searchMatches(matches, { team: "Flamengo", limit: 20 });
      for (let i = 1; i < result.length; i++) {
        expect(result[i - 1].date >= result[i].date).toBe(true);
      }
    });
  });
});

describe("Feature: Team name normalization", () => {
  it("should strip state suffix from Brasileirão format", () => {
    expect(normalizeTeamName("Palmeiras-SP")).toBe("Palmeiras");
    expect(normalizeTeamName("Flamengo-RJ")).toBe("Flamengo");
  });

  it("should strip ' - XX' state suffix from Copa do Brasil format", () => {
    expect(normalizeTeamName("América - MG")).toBe("América");
  });

  it("should remove parenthetical annotations", () => {
    expect(
      normalizeTeamName("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ")
    ).toBe("Boavista Sport Club");
  });

  it("should leave clean names unchanged", () => {
    expect(normalizeTeamName("São Paulo")).toBe("São Paulo");
    expect(normalizeTeamName("Grêmio")).toBe("Grêmio");
  });
});

describe("Feature: Date parsing", () => {
  it("should parse ISO dates with time", () => {
    expect(parseDate("2012-05-19 18:30:00")).toBe("2012-05-19");
  });

  it("should parse ISO dates without time", () => {
    expect(parseDate("2023-09-24")).toBe("2023-09-24");
  });

  it("should parse Brazilian date format", () => {
    expect(parseDate("29/03/2003")).toBe("2003-03-29");
  });
});
