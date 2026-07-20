/**
 * Feature: Team Queries
 *   Match history and statistics, win/loss/draw records,
 *   goals scored/conceded, performance by competition.
 */
import { describe, it, expect } from "vitest";
import type { Dataset } from "../src/types.js";
import { givenDatasetLoaded } from "./helpers.js";
import {
  mostGoalsScored,
  teamCompetitions,
  teamStats,
} from "../src/services/teams.js";

let ds: Dataset;
givenDatasetLoaded((d) => (ds = d));

describe("Feature: Team Queries", () => {
  it("Scenario: Get team statistics", () => {
    // Given the match data is loaded
    // When I request statistics for "Palmeiras" in season "2023"
    const s = teamStats(ds, "Palmeiras", { season: 2023 });
    // Then I should receive wins, losses, draws, and goals
    expect(s.matches).toBeGreaterThan(0);
    expect(s.wins + s.draws + s.losses).toBe(s.matches);
    expect(s.goalsFor).toBeGreaterThan(0);
    expect(s.goalsAgainst).toBeGreaterThanOrEqual(0);
  });

  it("Scenario: Home record is split from away record", () => {
    // When I request Corinthians' record in 2022 Brasileirão
    const s = teamStats(ds, "Corinthians", {
      season: 2022,
      competition: "Brasileirão",
    });
    // Then home + away totals equal the overall record
    expect(s.home.matches + s.away.matches).toBe(s.matches);
    expect(s.home.wins + s.away.wins).toBe(s.wins);
    // And the split is non-trivial (team actually played both ways)
    expect(s.home.matches).toBeGreaterThan(0);
    expect(s.away.matches).toBeGreaterThan(0);
  });

  it("Scenario: Performance breakdown by competition", () => {
    // When I request Flamengo's stats across all seasons
    const s = teamStats(ds, "Flamengo");
    // Then multiple competitions are present in the breakdown
    expect(s.byCompetition.size).toBeGreaterThan(1);
    const compNames = [...s.byCompetition.keys()];
    expect(compNames).toContain("Brasileirão Série A");
  });

  it("Scenario: List the competitions a team played", () => {
    // When I ask what competitions Palmeiras has played in
    const comps = teamCompetitions(ds, "Palmeiras");
    // Then national and continental competitions appear
    expect(comps.get("Brasileirão Série A")).toBeGreaterThan(0);
    expect(comps.get("Copa Libertadores")).toBeGreaterThan(0);
    expect(comps.get("Copa do Brasil")).toBeGreaterThan(0);
  });

  it("Scenario: Top scoring teams of a season", () => {
    // When I ask which team scored the most goals in Série A 2023
    const top = mostGoalsScored(ds, {
      competition: "Serie A",
      season: 2023,
      limit: 10,
    });
    // Then I receive a non-empty ranking sorted by goals
    expect(top.length).toBeGreaterThan(0);
    for (let i = 1; i < top.length; i++) {
      expect(top[i - 1].goalsFor).toBeGreaterThanOrEqual(top[i].goalsFor);
    }
    expect(top[0].goalsFor).toBeGreaterThan(20);
  });

  it("Scenario: Unknown team returns empty stats, not an error", () => {
    const s = teamStats(ds, "Nonexistent FC");
    expect(s.matches).toBe(0);
    expect(s.wins).toBe(0);
  });
});
