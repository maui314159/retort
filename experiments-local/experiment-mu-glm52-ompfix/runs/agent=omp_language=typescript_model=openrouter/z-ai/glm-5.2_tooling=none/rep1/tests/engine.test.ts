/**
 * brazilian-soccer-mcp — BDD tests for loaders + query engine
 *
 * Context block
 * ============
 * See src/types.ts for the top-level project context block.
 *
 * Loads the real Kaggle datasets from `data/kaggle` and exercises every
 * query-engine capability named in TASK.md's Required Capabilities and
 * Success Criteria (match, team, player, competition, and statistical
 * queries; cross-file matching; head-to-head; standings).
 */

import { describe, it, expect, beforeAll } from "vitest";
import { join } from "node:path";
import { SoccerDatabase } from "../src/engine.js";
import { loadAllMatches, loadFifaPlayers } from "../src/loaders.js";

const dataDir = join(process.cwd(), "data", "kaggle");
let db: SoccerDatabase;

beforeAll(async () => {
  const [matches, players] = await Promise.all([
    loadAllMatches(dataDir),
    loadFifaPlayers(dataDir),
  ]);
  db = new SoccerDatabase(matches, players);
});

describe("Feature: Data coverage", () => {
  it("Scenario: all six CSV files load into the database", () => {
    // Given the datasets in data/kaggle
    // When loaded
    // Then matches and players are populated
    expect(db.matches.length).toBeGreaterThan(20000);
    expect(db.players.length).toBeGreaterThan(18000);
  });

  it("Scenario: matches come from multiple competitions", () => {
    const comps = new Set(db.matches.map((m) => m.competition));
    expect(comps.size).toBeGreaterThanOrEqual(4);
    expect([...comps].some((c) => c.toLowerCase().includes("brasileir"))).toBe(true);
    expect([...comps].some((c) => c.toLowerCase().includes("copa do brasil"))).toBe(true);
    expect([...comps].some((c) => c.toLowerCase().includes("libertadores"))).toBe(true);
  });
});

describe("Feature: Match Queries", () => {
  it("Scenario: find matches between two teams", () => {
    // Given the match data is loaded
    // When I search for matches between "Flamengo" and "Fluminense"
    // Then I should receive a list of matches
    // And each match should have date, scores, and competition
    const rows = db.findMatches({ team: "Flamengo", opponent: "Fluminense", limit: 50 });
    expect(rows.length).toBeGreaterThan(0);
    for (const m of rows) {
      expect(m.date === null || typeof m.date === "string").toBe(true);
      expect(typeof m.competition).toBe("string");
      expect(m.homeTeam).toBeTruthy();
      expect(m.awayTeam).toBeTruthy();
      // One side is Flamengo, the other Fluminense (tolerant).
      const isFlaFlu =
        (m.homeTeam.toLowerCase().includes("flamengo") ||
          m.awayTeam.toLowerCase().includes("flamengo")) &&
        (m.homeTeam.toLowerCase().includes("fluminense") ||
          m.awayTeam.toLowerCase().includes("fluminense"));
      expect(isFlaFlu).toBe(true);
    }
  });

  it("Scenario: filter matches by season and competition", () => {
    const rows = db.findMatches({ team: "Palmeiras", season: 2022, competition: "Brasileirão" });
    expect(rows.length).toBeGreaterThan(0);
    for (const m of rows) expect(m.season).toBe(2022);
  });

  it("Scenario: last match between two teams is the most recent", () => {
    const rows = db.findMatches({ team: "Flamengo", opponent: "Corinthians", limit: 5 });
    const last = db.lastMatchBetween("Flamengo", "Corinthians");
    expect(last).not.toBeNull();
    expect(rows.length).toBeGreaterThan(0);
    // The most recent is at index 0 (sorted desc by date).
    expect((last!.date ?? "") >= (rows[rows.length - 1].date ?? "")).toBe(true);
  });
});

describe("Feature: Team Queries", () => {
  it("Scenario: get team statistics for a season", () => {
    // Given the match data is loaded
    // When I request statistics for "Palmeiras" in season 2023
    // Then I should receive wins, losses, draws, and goals
    const s = db.teamStats("Palmeiras", 2023);
    expect(s.team).toBe("Palmeiras");
    expect(s.matches).toBeGreaterThan(0);
    expect(s.wins + s.draws + s.losses).toBe(s.matches);
    expect(s.goalsFor).toBeGreaterThanOrEqual(0);
    expect(s.goalsAgainst).toBeGreaterThanOrEqual(0);
  });

  it("Scenario: home/away split sums to total", () => {
    const s = db.teamStats("Corinthians", 2022);
    expect(s.home.matches + s.away.matches).toBe(s.matches);
    expect(s.home.wins + s.away.wins).toBe(s.wins);
  });

  it("Scenario: competitions a team appears in span datasets", () => {
    const comps = db.competitionsFor("Palmeiras");
    expect(comps.length).toBeGreaterThanOrEqual(2);
    expect(comps.some((c) => c.toLowerCase().includes("brasileir"))).toBe(true);
  });
});

describe("Feature: Head-to-Head", () => {
  it("Scenario: compare two teams head-to-head", () => {
    const h2h = db.headToHead("Palmeiras", "Santos");
    expect(h2h.matches).toBeGreaterThan(0);
    expect(h2h.teamAWins + h2h.teamBWins + h2h.draws).toBeLessThanOrEqual(h2h.matches);
    expect(h2h.teamAGoals).toBeGreaterThanOrEqual(0);
  });
});

describe("Feature: Player Queries", () => {
  it("Scenario: search Brazilian players sorted by rating", () => {
    const players = db.playerSearch({ nationality: "Brazil", limit: 20 });
    expect(players.length).toBeGreaterThan(0);
    for (const p of players) {
      expect(p.nationality.toLowerCase()).toContain("brazil");
    }
    // Sorted by overall descending.
    for (let i = 1; i < players.length; i++) {
      expect((players[i - 1].overall ?? 0)).toBeGreaterThanOrEqual(
        players[i].overall ?? 0,
      );
    }
  });

  it("Scenario: search players by club", () => {
    const players = db.playerSearch({ club: "Santos", limit: 20 });
    expect(players.length).toBeGreaterThan(0);
    for (const p of players) expect(p.club.toLowerCase()).toContain("santos");
  });

  it("Scenario: search a named player", () => {
    const players = db.playerSearch({ name: "Neymar", limit: 5 });
    expect(players.length).toBeGreaterThan(0);
    expect(players[0].name.toLowerCase()).toContain("neymar");
  });

  it("Scenario: Brazilian players grouped by club", () => {
    const rows = db.brazilianPlayersByClub();
    expect(rows.length).toBeGreaterThan(0);
    // Descending by count.
    for (let i = 1; i < rows.length; i++) {
      expect(rows[i - 1].count).toBeGreaterThanOrEqual(rows[i].count);
    }
  });
});

describe("Feature: Competition Queries", () => {
  it("Scenario: standings for a Brasileirão season", () => {
    const rows = db.standings("Brasileirão", 2019);
    expect(rows.length).toBeGreaterThanOrEqual(10);
    // Standings are sorted by points descending.
    for (let i = 1; i < rows.length; i++) {
      expect(rows[i - 1].points).toBeGreaterThanOrEqual(rows[i].points);
    }
    // Champion is position 1.
    expect(rows[0].position).toBe(1);
    expect(rows[0].points).toBeGreaterThanOrEqual(rows[rows.length - 1].points);
  });

  it("Scenario: standings have consistent W/D/L vs played", () => {
    const rows = db.standings("Brasileirão", 2019);
    for (const r of rows) {
      expect(r.wins + r.draws + r.losses).toBe(r.played);
    }
  });
});

describe("Feature: Statistical Analysis", () => {
  it("Scenario: average goals per match in the Brasileirão", () => {
    const r = db.averageGoals("Brasileirão");
    expect(r.matches).toBeGreaterThan(0);
    expect(r.avgGoals).toBeGreaterThan(0);
    expect(r.avgGoals).toBeLessThan(10);
    expect(r.homeWinRate + r.awayWinRate + r.drawRate).toBeCloseTo(1, 5);
  });

  it("Scenario: biggest wins are sorted by goal difference", () => {
    const rows = db.biggestWins(10, "Brasileirão");
    expect(rows.length).toBeGreaterThan(0);
    for (let i = 1; i < rows.length; i++) {
      const prev = Math.abs((rows[i - 1].homeGoal ?? 0) - (rows[i - 1].awayGoal ?? 0));
      const cur = Math.abs((rows[i].homeGoal ?? 0) - (rows[i].awayGoal ?? 0));
      expect(prev).toBeGreaterThanOrEqual(cur);
    }
  });

  it("Scenario: best home record returns a team with home matches", () => {
    const s = db.bestRecordAtVenue("home");
    expect(s).not.toBeNull();
    expect(s!.home.matches).toBeGreaterThan(0);
  });
});

describe("Feature: Cross-file queries", () => {
  it("Scenario: a team appears across multiple source datasets", () => {
    const sources = new Set(
      db.matchesForTeam("Flamengo").map((m) => m.source),
    );
    expect(sources.size).toBeGreaterThanOrEqual(2);
  });

  it("Scenario: player + match data can be queried together via the same db", () => {
    const players = db.playerSearch({ club: "Santos", limit: 5 });
    const matches = db.findMatches({ team: "Flamengo", limit: 5 });
    expect(players.length).toBeGreaterThan(0);
    expect(matches.length).toBeGreaterThan(0);
  });
});
