/**
 * Context
 * -------
 * BDD (Given/When/Then) scenarios for the Match, Team and Statistical-Analysis
 * capability areas of the spec, run against the real loaded datasets. These
 * verify the behaviours the spec's "Success Criteria" enumerate: searching
 * matches by team/season/competition, head-to-head records, team W/D/L+goals
 * aggregation (with home/away split), biggest wins, and goals-per-match.
 */

import { describe, it, expect, beforeAll } from "vitest";
import {
  findMatches,
  headToHead,
  teamStats,
  goalsSummary,
  biggestWins,
  teamKeyMatches,
} from "../src/queries.js";
import { normalizeTeam } from "../src/normalize.js";
import type { DataStore } from "../src/store.js";
import { getStore } from "./fixture.js";

let store: DataStore;
beforeAll(async () => {
  store = await getStore();
});

describe("Feature: Match Queries", () => {
  it("Scenario: data loads from all provided CSV files", () => {
    // Given the data is loaded
    // Then all five competitions are represented and players exist
    const comps = store.competitions();
    expect(comps).toContain("Brasileirão");
    expect(comps).toContain("Copa do Brasil");
    expect(comps).toContain("Libertadores");
    expect(store.matches.length).toBeGreaterThan(10000);
    expect(store.players.length).toBeGreaterThan(18000);
  });

  it("Scenario: find matches between two teams (Fla-Flu)", () => {
    // When I search for matches between Flamengo and Fluminense
    const matches = findMatches(store, {
      team: "Flamengo",
      opponent: "Fluminense",
    });
    // Then I receive matches, each involving both teams with a date and score
    expect(matches.length).toBeGreaterThan(0);
    const flaKey = normalizeTeam("Flamengo");
    const fluKey = normalizeTeam("Fluminense");
    for (const m of matches) {
      const hasFla =
        teamKeyMatches(m.homeKey, flaKey) || teamKeyMatches(m.awayKey, flaKey);
      const hasFlu =
        teamKeyMatches(m.homeKey, fluKey) || teamKeyMatches(m.awayKey, fluKey);
      expect(hasFla && hasFlu).toBe(true);
    }
    // And results are sorted most-recent first
    const dates = matches.map((m) => m.date ?? "").filter(Boolean);
    const sorted = [...dates].sort((a, b) => b.localeCompare(a));
    expect(dates).toEqual(sorted);
  });

  it("Scenario: find matches for a team in a season", () => {
    // When I ask what matches Palmeiras played in 2023
    const matches = findMatches(store, { team: "Palmeiras", season: 2023 });
    // Then every result is from 2023 and involves Palmeiras
    expect(matches.length).toBeGreaterThan(0);
    const palKey = normalizeTeam("Palmeiras");
    for (const m of matches) {
      expect(m.season).toBe(2023);
      const inMatch =
        teamKeyMatches(m.homeKey, palKey) || teamKeyMatches(m.awayKey, palKey);
      expect(inMatch).toBe(true);
    }
  });

  it("Scenario: filter matches by competition", () => {
    // When I restrict to Copa do Brasil
    const matches = findMatches(store, {
      team: "Flamengo",
      competition: "Copa do Brasil",
    });
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) expect(m.competition).toBe("Copa do Brasil");
  });

  it("Scenario: home/away side restriction is honoured", () => {
    const home = findMatches(store, { team: "Santos", side: "home", season: 2019 });
    const santosKey = normalizeTeam("Santos");
    for (const m of home) {
      expect(teamKeyMatches(m.homeKey, santosKey)).toBe(true);
    }
  });
});

describe("Feature: Team Queries", () => {
  it("Scenario: get a team's record for a season (Corinthians 2022)", () => {
    // When I request statistics for Corinthians in 2022 Brasileirão
    const stats = teamStats(store, "Corinthians", {
      season: 2022,
      competition: "Brasileirão",
    });
    // Then I receive consistent wins/draws/losses and goals
    const r = stats.overall;
    expect(r.matches).toBe(r.wins + r.draws + r.losses);
    expect(r.matches).toBeGreaterThan(0);
    // And the home + away splits sum to the overall record
    expect(stats.home.matches + stats.away.matches).toBe(r.matches);
    expect(stats.home.wins + stats.away.wins).toBe(r.wins);
    expect(stats.home.goalsFor + stats.away.goalsFor).toBe(r.goalsFor);
  });

  it("Scenario: head-to-head record is internally consistent", () => {
    // When I compare Palmeiras and Santos head-to-head
    const h = headToHead(store, "Palmeiras", "Santos");
    // Then wins + draws account for every scored match
    expect(h.matches.length).toBeGreaterThan(0);
    expect(h.aWins + h.bWins + h.draws).toBeLessThanOrEqual(h.matches.length);
    // And it is symmetric when teams are swapped
    const swapped = headToHead(store, "Santos", "Palmeiras");
    expect(swapped.aWins).toBe(h.bWins);
    expect(swapped.bWins).toBe(h.aWins);
    expect(swapped.draws).toBe(h.draws);
  });
});

describe("Feature: Statistical Analysis", () => {
  it("Scenario: average goals per match in the Brasileirão is realistic", () => {
    // When I aggregate goals across the Brasileirão
    const s = goalsSummary(store, { competition: "Brasileirão" });
    // Then the average lands in a sane football range
    expect(s.goalsPerMatch).toBeGreaterThan(2);
    expect(s.goalsPerMatch).toBeLessThan(4);
    // And home/away/draw counts partition the scored matches
    expect(s.homeWins + s.awayWins + s.draws).toBe(s.matchesWithScore);
    // And home advantage exists (home win rate above draw-implied baseline)
    expect(s.homeWinRate).toBeGreaterThan(0.4);
  });

  it("Scenario: biggest wins are sorted by margin", () => {
    // When I ask for the biggest wins in the Brasileirão
    const top = biggestWins(store, { competition: "Brasileirão" }, 5);
    expect(top.length).toBe(5);
    // Then margins are non-increasing
    const margins = top.map((m) => Math.abs(m.homeGoal! - m.awayGoal!));
    for (let i = 1; i < margins.length; i++) {
      expect(margins[i]).toBeLessThanOrEqual(margins[i - 1]);
    }
    // And the largest margin is a blowout (>= 6 goals in this dataset)
    expect(margins[0]).toBeGreaterThanOrEqual(6);
  });
});
