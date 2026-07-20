/**
 * Feature: Team Queries
 *
 * Match history, win/loss/draw records, goals and performance splits.
 */

import { beforeAll, describe, expect, it } from "vitest";
import { givenDataLoaded } from "./helpers.js";
import type { SoccerQueries } from "../src/queries.js";

let q: SoccerQueries;

beforeAll(() => {
  q = givenDataLoaded().queries;
});

describe("Feature: Team Queries", () => {
  it("Scenario: Get team statistics for a season", () => {
    // Given the match data is loaded
    // When I request statistics for "Palmeiras" in season "2023"
    const rec = q.teamRecord("Palmeiras", { season: 2023, competition: "Serie A" });
    // Then I should receive wins, losses, draws, and goals
    expect(rec.matches).toBeGreaterThan(30);
    expect(rec.wins + rec.draws + rec.losses).toBe(rec.matches);
    expect(rec.goalsFor).toBeGreaterThan(0);
    expect(rec.goalsAgainst).toBeGreaterThan(0);
    expect(rec.goalDifference).toBe(rec.goalsFor - rec.goalsAgainst);
    expect(rec.winRate).toBeCloseTo(rec.wins / rec.matches, 10);
  });

  it("Scenario: Corinthians home record in 2022", () => {
    // When I request Corinthians' home record in the 2022 Brasileirão
    const rec = q.teamRecord("Corinthians", {
      season: 2022,
      competition: "Brasileirão",
      venue: "home",
    });
    // Then there are exactly 19 home matches (20-team league)
    expect(rec.matches).toBe(19);
    expect(rec.wins + rec.draws + rec.losses).toBe(19);
    // And home + away must equal the full season record
    const away = q.teamRecord("Corinthians", { season: 2022, competition: "Brasileirão", venue: "away" });
    const all = q.teamRecord("Corinthians", { season: 2022, competition: "Brasileirão" });
    expect(away.matches).toBe(19);
    expect(all.matches).toBe(38);
    expect(rec.wins + away.wins).toBe(all.wins);
    expect(rec.goalsFor + away.goalsFor).toBe(all.goalsFor);
  });

  it("Scenario: Which team scored the most goals in Serie A 2023", () => {
    // When I ask for the top-scoring teams of 2023
    const top = q.topScoringTeams({ season: 2023, competition: "Serie A", limit: 5 });
    // Then the leader is a real 2023 Serie A attack with consistent numbers
    expect(top.length).toBe(5);
    expect(top[0].goalsFor).toBeGreaterThanOrEqual(top[1].goalsFor);
    expect(top[0].goalsFor).toBeGreaterThan(50);
    // And every listed team played 2023 Serie A football
    for (const r of top) expect(r.matches).toBeGreaterThan(30);
  });

  it("Scenario: Best home record in a season", () => {
    // When I ask for the best home records of 2023 Serie A
    const best = q.bestHomeRecords({ season: 2023, competition: "Serie A", limit: 5, minMatches: 15 });
    // Then win rates are sorted descending
    for (let i = 1; i < best.length; i++) {
      expect(best[i - 1].winRate).toBeGreaterThanOrEqual(best[i].winRate);
    }
    // And every team listed has the minimum number of home matches
    for (const r of best) expect(r.matches).toBeGreaterThanOrEqual(15);
  });

  it("Scenario: Team competitions overview", () => {
    // When I ask what competitions Palmeiras has played in
    const tc = q.teamCompetitions("Palmeiras");
    const comps = tc.competitions.map((c) => c.competition);
    // Then the three main competitions show up
    expect(comps).toContain("Brasileirão Série A");
    expect(comps).toContain("Copa do Brasil");
    expect(comps).toContain("Copa Libertadores");
    // And each entry carries seasons and match counts
    for (const c of tc.competitions) {
      expect(c.matches).toBeGreaterThan(0);
      expect(c.seasons.length).toBeGreaterThan(0);
    }
  });

  it("Scenario: Unknown team yields an empty record, not a crash", () => {
    const rec = q.teamRecord("Wolverhampton Wanderers");
    expect(rec.matches).toBe(0);
    expect(rec.winRate).toBe(0);
  });
});
