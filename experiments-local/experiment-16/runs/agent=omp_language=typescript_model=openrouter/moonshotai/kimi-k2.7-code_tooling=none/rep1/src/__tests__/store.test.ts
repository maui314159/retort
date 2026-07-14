/**
 * BDD-style tests for the Brazilian Soccer MCP data store.
 *
 * Scenarios mirror the Gherkin examples in TASK.md and the sample questions
 * from the specification.
 */

import { describe, it, expect, beforeAll } from "vitest";
import { loadAllData } from "../loaders.js";
import { SoccerStore } from "../store.js";

describe("Data loading", () => {
  let store: SoccerStore;

  beforeAll(async () => {
    const data = await loadAllData("data/kaggle");
    store = new SoccerStore(data);
  });

  it("loads all six CSV files into memory", () => {
    expect(store.matches.length).toBeGreaterThan(17_000);
    expect(store.players.length).toBeGreaterThan(15_000);
  });
});

describe("Feature: Match Queries", () => {
  let store: SoccerStore;

  beforeAll(async () => {
    const data = await loadAllData("data/kaggle");
    store = new SoccerStore(data);
  });

  it("Scenario: Find matches between two teams", () => {
    const matches = store.searchMatches({ team: "Flamengo", opponent: "Fluminense" });
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) {
      expect(m.homeGoals).not.toBeNull();
      expect(m.awayGoals).not.toBeNull();
      expect(m.date).not.toBeNull();
      expect([m.homeKey, m.awayKey]).toContain("flamengo");
      expect([m.homeKey, m.awayKey]).toContain("fluminense");
    }
  });

  it("Scenario: Find matches for a team in a season", () => {
    const matches = store.searchMatches({ team: "Palmeiras", season: 2023 });
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) {
      expect(m.season).toBe(2023);
      expect([m.homeKey, m.awayKey]).toContain("palmeiras");
    }
  });

  it("normalizes team name variations (state suffixes)", () => {
    const withSuffix = store.searchMatches({ team: "Palmeiras-SP", season: 2012 });
    const withoutSuffix = store.searchMatches({ team: "Palmeiras", season: 2012 });
    expect(withoutSuffix.length).toBeGreaterThan(0);
    expect(withSuffix.length).toEqual(withoutSuffix.length);
  });

  it("filters matches by competition", () => {
    const libertadores = store.searchMatches({ competition: "Copa Libertadores" });
    expect(libertadores.length).toBeGreaterThan(0);
    for (const m of libertadores) {
      expect(m.competition.toLowerCase()).toContain("libertadores");
    }
  });
});

describe("Feature: Team Queries", () => {
  let store: SoccerStore;

  beforeAll(async () => {
    const data = await loadAllData("data/kaggle");
    store = new SoccerStore(data);
  });

  it("Scenario: Get team statistics", () => {
    const stats = store.teamStatistics("Corinthians", {
      season: 2022,
      competition: "Brasileirão",
      venue: "home",
    });
    expect(stats.matches).toBeGreaterThan(0);
    expect(stats.wins + stats.draws + stats.losses).toBe(stats.matches);
    expect(stats.goalsFor).toBeGreaterThanOrEqual(0);
    expect(stats.goalsAgainst).toBeGreaterThanOrEqual(0);
  });

  it("compares two teams head-to-head", () => {
    const h2h = store.headToHead("Palmeiras", "Santos");
    expect(h2h.matches.length).toBeGreaterThan(0);
    expect(h2h.winsA + h2h.winsB + h2h.draws).toBe(h2h.matches.length);
  });
});

describe("Feature: Player Queries", () => {
  let store: SoccerStore;

  beforeAll(async () => {
    const data = await loadAllData("data/kaggle");
    store = new SoccerStore(data);
  });

  it("finds players by name", () => {
    const players = store.searchPlayers({ name: "Neymar Jr" });
    expect(players.length).toBeGreaterThan(0);
    expect(players[0].name.toLowerCase()).toContain("neymar");
  });

  it("filters Brazilian players", () => {
    const players = store.searchPlayers({ nationality: "Brazil", limit: 50 });
    expect(players.length).toBeGreaterThan(0);
    for (const p of players) {
      expect(p.nationality?.toLowerCase()).toBe("brazil");
    }
  });

  it("finds players at a Brazilian club", () => {
    const players = store.searchPlayers({ club: "Santos", limit: 20 });
    expect(players.length).toBeGreaterThan(0);
    for (const p of players) {
      expect(p.club?.toLowerCase()).toContain("santos");
    }
  });
});

describe("Feature: Competition Queries", () => {
  let store: SoccerStore;

  beforeAll(async () => {
    const data = await loadAllData("data/kaggle");
    store = new SoccerStore(data);
  });

  it("calculates 2019 Brasileirão standings with Flamengo as champion", () => {
    const standings = store.competitionStandings("Brasileirão", 2019);
    expect(standings.length).toBeGreaterThan(0);
    expect(standings[0].team).toBe("Flamengo");
    expect(standings[0].points).toBeGreaterThan(0);
  });

  it("lists Copa do Brasil matches", () => {
    const matches = store.searchMatches({ competition: "Copa do Brasil" });
    expect(matches.length).toBeGreaterThan(0);
  });
});

describe("Feature: Statistical Analysis", () => {
  let store: SoccerStore;

  beforeAll(async () => {
    const data = await loadAllData("data/kaggle");
    store = new SoccerStore(data);
  });

  it("computes average goals per match", () => {
    const avg = store.averageGoalsPerMatch({ competition: "Brasileirão" });
    expect(avg).toBeGreaterThan(0);
    expect(avg).toBeLessThan(10);
  });

  it("finds biggest wins", () => {
    const wins = store.biggestWins({ competition: "Brasileirão", limit: 10 });
    expect(wins.length).toBe(10);
    for (let i = 1; i < wins.length; i++) {
      const prev = Math.abs((wins[i - 1].homeGoals ?? 0) - (wins[i - 1].awayGoals ?? 0));
      const curr = Math.abs((wins[i].homeGoals ?? 0) - (wins[i].awayGoals ?? 0));
      expect(curr).toBeLessThanOrEqual(prev);
    }
  });
});
