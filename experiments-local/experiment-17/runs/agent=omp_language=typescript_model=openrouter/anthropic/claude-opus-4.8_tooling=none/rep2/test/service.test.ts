/**
 * Context
 * -------
 * BDD coverage for the query layer against the REAL bundled datasets. The graph
 * is loaded once and shared. Assertions anchor on the fully-present 2019
 * Brasileirão season (Flamengo's record-setting 90-point title) and on stable
 * structural invariants, never on arbitrary defaults.
 */

import { beforeAll, describe, expect, it } from "vitest";

import { SoccerGraph } from "../src/service.js";

let graph: SoccerGraph;

beforeAll(() => {
  graph = SoccerGraph.load();
});

describe("Feature: Dataset loading", () => {
  it("Scenario: all six sources contribute matches and players", () => {
    // Given the bundled CSV files
    // Then matches and players load with every competition represented
    expect(graph.matches.length).toBeGreaterThan(15_000);
    expect(graph.players.length).toBe(18_207);

    const comps = new Set(graph.matches.map((m) => m.competition));
    expect(comps).toContain("Brasileirão Série A");
    expect(comps).toContain("Brasileirão Série B");
    expect(comps).toContain("Brasileirão Série C");
    expect(comps).toContain("Copa do Brasil");
    expect(comps).toContain("Copa Libertadores");
  });

  it("Scenario: a complete league season is not double-counted across sources", () => {
    // Given Série A 2019 appears in three source files
    // When the canonical match list is built
    const sa2019 = graph.matches.filter((m) => m.competition === "Brasileirão Série A" && m.season === 2019);
    // Then exactly one round-robin of 20 teams (380 games) survives
    expect(sa2019).toHaveLength(380);
  });
});

describe("Feature: Match Queries", () => {
  it("Scenario: find matches between two teams", () => {
    // Given the match data is loaded
    // When I search for matches between Flamengo and Fluminense
    const matches = graph.findMatches({ team: "Flamengo", opponent: "Fluminense" });
    // Then I receive matches, each with date, scores, and competition
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) {
      expect(m.date?.iso).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(typeof m.homeGoals).toBe("number");
      expect(m.competition).toBeTruthy();
      const involvesBoth =
        (m.home.baseKey === "flamengo" && m.away.baseKey === "fluminense") ||
        (m.home.baseKey === "fluminense" && m.away.baseKey === "flamengo");
      expect(involvesBoth).toBe(true);
    }
  });

  it("Scenario: filter matches by season and competition", () => {
    const matches = graph.findMatches({ team: "Palmeiras", competition: "Brasileirão Série A", season: 2019 });
    expect(matches.length).toBe(38); // 19 home + 19 away in a 20-team season
    for (const m of matches) expect(m.season).toBe(2019);
  });

  it("Scenario: results are ordered newest-first", () => {
    const matches = graph.findMatches({ team: "Santos", competition: "Brasileirão Série A", season: 2019 });
    for (let i = 1; i < matches.length; i++) {
      expect(matches[i - 1]!.date!.epoch).toBeGreaterThanOrEqual(matches[i]!.date!.epoch);
    }
  });

  it("Scenario: a date range is respected", () => {
    const matches = graph.findMatches({
      competition: "Brasileirão Série A",
      season: 2019,
      from: "2019-12-01",
      to: "2019-12-08",
    });
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) {
      expect(m.date!.iso >= "2019-12-01").toBe(true);
      expect(m.date!.iso <= "2019-12-08").toBe(true);
    }
  });
});

describe("Feature: Team Queries", () => {
  it("Scenario: get team statistics for a season", () => {
    // Given the match data is loaded
    // When I request Flamengo's 2019 Série A record
    const r = graph.teamRecord("Flamengo", { competition: "Brasileirão Série A", season: 2019 });
    // Then I receive wins/draws/losses and goals consistent with the title run
    expect(r.matches).toBe(38);
    expect(r.wins + r.draws + r.losses).toBe(38);
    // Champions 2019: 28W 6D 4L, 86 GF.
    expect(r.wins).toBe(28);
    expect(r.draws).toBe(6);
    expect(r.losses).toBe(4);
    expect(r.goalsFor).toBe(86);
  });

  it("Scenario: home/away split sums to the full record", () => {
    const all = graph.teamRecord("Palmeiras", { competition: "Brasileirão Série A", season: 2019 });
    const home = graph.teamRecord("Palmeiras", { competition: "Brasileirão Série A", season: 2019, venue: "home" });
    const away = graph.teamRecord("Palmeiras", { competition: "Brasileirão Série A", season: 2019, venue: "away" });
    expect(home.matches + away.matches).toBe(all.matches);
    expect(home.wins + away.wins).toBe(all.wins);
    expect(home.goalsFor + away.goalsFor).toBe(all.goalsFor);
  });

  it("Scenario: head-to-head totals are internally consistent", () => {
    const h2h = graph.headToHead("Flamengo", "Fluminense");
    expect(h2h.aWins + h2h.bWins + h2h.draws).toBe(h2h.matches.length);
    // Symmetry: swapping teams swaps the win columns.
    const swapped = graph.headToHead("Fluminense", "Flamengo");
    expect(swapped.aWins).toBe(h2h.bWins);
    expect(swapped.bWins).toBe(h2h.aWins);
    expect(swapped.draws).toBe(h2h.draws);
  });
});

describe("Feature: Player Queries", () => {
  it("Scenario: search players by name", () => {
    const players = graph.findPlayers({ name: "Neymar" });
    expect(players.length).toBeGreaterThan(0);
    expect(players[0]!.name).toContain("Neymar");
  });

  it("Scenario: filter Brazilian players ranked by rating", () => {
    const players = graph.findPlayers({ nationality: "Brazil" });
    expect(players.length).toBe(827);
    expect(players.every((p) => p.nationality === "Brazil")).toBe(true);
    // Sorted by overall descending.
    for (let i = 1; i < players.length; i++) {
      expect(players[i - 1]!.overall ?? 0).toBeGreaterThanOrEqual(players[i]!.overall ?? 0);
    }
    expect(players[0]!.name).toContain("Neymar");
  });

  it("Scenario: filter by club substring", () => {
    // Fluminense is present in this FIFA snapshot; Flamengo is not.
    const players = graph.findPlayers({ club: "Fluminense" });
    expect(players.length).toBeGreaterThan(0);
    expect(players.every((p) => /fluminense/i.test(p.club))).toBe(true);
  });

  it("Scenario: minimum-rating threshold is enforced", () => {
    const players = graph.findPlayers({ nationality: "Brazil", minOverall: 85 });
    expect(players.every((p) => (p.overall ?? 0) >= 85)).toBe(true);
  });
});

describe("Feature: Competition Queries", () => {
  it("Scenario: 2019 Brasileirão standings name Flamengo champion with 90 points", () => {
    // Given match results for 2019 Série A
    // When the table is computed
    const table = graph.standings("Brasileirão Série A", 2019);
    // Then 20 teams are ranked and Flamengo top with the historical 90 points
    expect(table).toHaveLength(20);
    expect(table[0]!.team).toBe("Flamengo-RJ");
    expect(table[0]!.points).toBe(90);
    expect(table[0]!.wins).toBe(28);
    expect(table[0]!.draws).toBe(6);
    expect(table[0]!.losses).toBe(4);
    // Every team plays 38 games.
    expect(table.every((r) => r.played === 38)).toBe(true);
  });

  it("Scenario: points equal 3*wins + draws for every team", () => {
    const table = graph.standings("Brasileirão Série A", 2019);
    for (const r of table) expect(r.points).toBe(r.wins * 3 + r.draws);
  });
});

describe("Feature: Statistical Analysis", () => {
  it("Scenario: average goals per match is a plausible football figure", () => {
    const stats = graph.competitionStats("Brasileirão Série A", 2019);
    expect(stats.matches).toBe(380);
    expect(stats.goalsPerMatch).toBeGreaterThan(2);
    expect(stats.goalsPerMatch).toBeLessThan(4);
    expect(stats.homeWins + stats.awayWins + stats.draws).toBe(380);
  });

  it("Scenario: home win rate is between 0 and 1", () => {
    const stats = graph.competitionStats("Brasileirão Série A");
    expect(stats.homeWinRate).toBeGreaterThan(0);
    expect(stats.homeWinRate).toBeLessThan(1);
  });

  it("Scenario: biggest wins are sorted by goal margin", () => {
    const wins = graph.biggestWins({ limit: 10 });
    expect(wins).toHaveLength(10);
    for (let i = 1; i < wins.length; i++) {
      const prev = Math.abs(wins[i - 1]!.homeGoals - wins[i - 1]!.awayGoals);
      const cur = Math.abs(wins[i]!.homeGoals - wins[i]!.awayGoals);
      expect(prev).toBeGreaterThanOrEqual(cur);
    }
    expect(Math.abs(wins[0]!.homeGoals - wins[0]!.awayGoals)).toBeGreaterThanOrEqual(6);
  });
});
