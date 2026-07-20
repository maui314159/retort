/**
 * Feature: Match Queries
 *   Find matches by criteria: team, date range, competition, season.
 */
import { describe, it, expect } from "vitest";
import type { Dataset } from "../src/types.js";
import { givenDatasetLoaded } from "./helpers.js";
import {
  competitionMatches,
  findMatches,
  headToHead,
  lastMeeting,
} from "../src/services/matches.js";

let ds: Dataset;
givenDatasetLoaded((d) => (ds = d));

describe("Feature: Match Queries", () => {
  it("Scenario: Find matches between two teams", () => {
    // Given the match data is loaded
    // When I search for matches between "Flamengo" and "Fluminense"
    const matches = findMatches(ds, {
      team: "Flamengo",
      opponent: "Fluminense",
      limit: 100,
    });
    // Then I should receive a list of matches
    expect(matches.length).toBeGreaterThan(10);
    // And each match should have date, scores, and competition
    for (const m of matches) {
      expect(m.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(typeof m.homeGoals).toBe("number");
      expect(typeof m.awayGoals).toBe("number");
      expect(m.competition.length).toBeGreaterThan(0);
    }
  });

  it("Scenario: matches cross source files for the same pairing", () => {
    // Given the Fla-Flu derby appears in several files
    const matches = findMatches(ds, { team: "Flamengo", opponent: "Fluminense", limit: 200 });
    const sources = new Set(matches.map((m) => m.source));
    // Then more than one source file contributes results
    expect(sources.size).toBeGreaterThan(1);
  });

  it("Scenario: Filter matches by team and season", () => {
    // When I search for Palmeiras matches in 2023
    const matches = findMatches(ds, { team: "Palmeiras", season: 2023, limit: 200 });
    // Then all results involve Palmeiras and belong to 2023
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) {
      expect(m.season).toBe(2023);
    }
  });

  it("Scenario: Filter matches by competition", () => {
    // When I search Libertadores matches involving Grêmio
    const matches = findMatches(ds, {
      team: "Grêmio",
      competition: "Libertadores",
      limit: 50,
    });
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) expect(m.competition).toBe("Copa Libertadores");
  });

  it("Scenario: Filter matches by date range", () => {
    // When I search matches between 2023-01-01 and 2023-12-31
    const matches = findMatches(ds, {
      fromDate: "2023-01-01",
      toDate: "2023-12-31",
      limit: 200,
    });
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) {
      expect(m.date! >= "2023-01-01").toBe(true);
      expect(m.date! <= "2023-12-31").toBe(true);
    }
  });

  it("Scenario: Find cup finals via the stage filter", () => {
    // When I search for Copa do Brasil finals
    const finals = findMatches(ds, {
      competition: "Copa do Brasil",
      stage: "final",
      limit: 50,
    });
    // Then I receive final-round matches
    expect(finals.length).toBeGreaterThan(5);
    for (const m of finals) expect(m.stage).toBe("final");
  });

  it("Scenario: results are chronological", () => {
    const matches = findMatches(ds, { team: "Santos", limit: 100 });
    const dates = matches.map((m) => m.date!);
    const sorted = [...dates].sort();
    expect(dates).toEqual(sorted);
  });

  it("Scenario: Last meeting between two teams", () => {
    // When I ask when Flamengo last played Corinthians
    const m = lastMeeting(ds, "Flamengo", "Corinthians");
    // Then I get the most recent match with a score
    expect(m).not.toBeNull();
    expect(m!.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(m!.homeGoals).toBeGreaterThanOrEqual(0);
    expect(m!.awayGoals).toBeGreaterThanOrEqual(0);
  });

  it("Scenario: Head-to-head summary is internally consistent", () => {
    // When I compare Palmeiras and Santos
    const h = headToHead(ds, "Palmeiras", "Santos");
    // Then totals add up
    expect(h.matches).toBeGreaterThan(10);
    expect(h.winsA + h.winsB + h.draws).toBe(h.matches);
    expect(h.recent.length).toBeLessThanOrEqual(10);
  });

  it("Scenario: competition name aliases resolve", () => {
    expect(competitionMatches("Brasileirão Série A", "brasileirao")).toBe(true);
    expect(competitionMatches("Brasileirão Série A", "Serie A")).toBe(true);
    expect(competitionMatches("Copa do Brasil", "brazilian cup")).toBe(true);
    expect(competitionMatches("Copa Libertadores", "libertadores")).toBe(true);
    expect(competitionMatches("Copa do Brasil", "libertadores")).toBe(false);
  });
});
