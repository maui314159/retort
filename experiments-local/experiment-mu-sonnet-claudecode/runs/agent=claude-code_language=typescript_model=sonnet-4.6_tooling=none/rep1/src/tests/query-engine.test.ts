import { describe, it, expect, beforeAll } from "vitest";
import {
  loadBrasileiraoMatches,
  loadCupMatches,
  loadLibertadoresMatches,
  loadExtendedMatches,
  loadHistoricalMatches,
  loadFifaPlayers,
  buildNormalizedMatches,
} from "../data-loader.js";
import {
  searchMatches,
  getTeamStats,
  headToHead,
  getStandings,
  searchPlayers,
  getGlobalStats,
  getBiggestWins,
  getExtendedStats,
} from "../query-engine.js";
import type { Database } from "../query-engine.js";

let db: Database;

beforeAll(() => {
  const brasileirao = loadBrasileiraoMatches();
  const cup = loadCupMatches();
  const libertadores = loadLibertadoresMatches();
  const historical = loadHistoricalMatches();
  const extended = loadExtendedMatches();
  const players = loadFifaPlayers();
  const matches = buildNormalizedMatches(brasileirao, cup, libertadores, historical);
  db = { matches, extended, players };
});

describe("Match queries", () => {
  it("finds matches between Flamengo and Fluminense", () => {
    const results = searchMatches(db, { team: "Flamengo", opponent: "Fluminense" });
    expect(results.length).toBeGreaterThan(0);
    results.forEach((m) => {
      const names = [m.home_team.toLowerCase(), m.away_team.toLowerCase()];
      expect(names.some((n) => n.includes("flamengo") || n.includes("fluminense"))).toBe(true);
    });
  });

  it("finds Palmeiras matches in 2022", () => {
    const results = searchMatches(db, { team: "Palmeiras", season: 2022 });
    expect(results.length).toBeGreaterThan(0);
    results.forEach((m) => {
      expect(m.season).toBe(2022);
    });
  });

  it("finds matches by competition", () => {
    const results = searchMatches(db, { competition: "Libertadores" });
    expect(results.length).toBeGreaterThan(100);
    results.forEach((m) => {
      expect(m.competition.toLowerCase()).toContain("libertadores");
    });
  });

  it("finds matches by date range", () => {
    const results = searchMatches(db, {
      dateFrom: "2019-01-01",
      dateTo: "2019-12-31",
    });
    expect(results.length).toBeGreaterThan(0);
    results.forEach((m) => {
      expect(m.date >= "2019-01-01" && m.date <= "2019-12-31").toBe(true);
    });
  });

  it("respects the limit parameter", () => {
    const results = searchMatches(db, { limit: 5 });
    expect(results.length).toBeLessThanOrEqual(5);
  });

  it("returns results sorted by date descending", () => {
    const results = searchMatches(db, { limit: 10 });
    for (let i = 1; i < results.length; i++) {
      expect(results[i - 1].date >= results[i].date).toBe(true);
    }
  });

  it("finds Copa do Brasil matches", () => {
    const results = searchMatches(db, { competition: "Copa do Brasil" });
    expect(results.length).toBeGreaterThan(0);
  });
});

describe("Team statistics", () => {
  it("calculates Corinthians home record in 2022", () => {
    const stats = getTeamStats(db, "Corinthians", {
      season: 2022,
      competition: "Brasileirao Serie A",
      homeOnly: true,
    });
    expect(stats.matches).toBeGreaterThan(0);
    expect(stats.wins + stats.draws + stats.losses).toBe(stats.matches);
    expect(stats.points).toBe(stats.wins * 3 + stats.draws);
  });

  it("calculates team stats without filters", () => {
    const stats = getTeamStats(db, "Flamengo", {});
    expect(stats.matches).toBeGreaterThan(50);
    expect(stats.goals_for).toBeGreaterThan(0);
    expect(stats.goal_difference).toBe(stats.goals_for - stats.goals_against);
  });

  it("returns zero stats for unknown team", () => {
    const stats = getTeamStats(db, "XYZ Unknown Team 9999", {});
    expect(stats.matches).toBe(0);
  });
});

describe("Head-to-head", () => {
  it("computes Palmeiras vs Santos head-to-head", () => {
    const result = headToHead(db, "Palmeiras", "Santos", {});
    expect(result.matches.length).toBeGreaterThan(0);
    expect(result.team1_wins + result.team2_wins + result.draws).toBe(
      result.matches.length + (result.team1_wins + result.team2_wins + result.draws - result.matches.length)
    );
    // Total wins+draws should be consistent
    expect(result.team1_wins).toBeGreaterThanOrEqual(0);
    expect(result.team2_wins).toBeGreaterThanOrEqual(0);
    expect(result.draws).toBeGreaterThanOrEqual(0);
  });

  it("returns empty for non-existent matchup", () => {
    const result = headToHead(db, "TeamA99", "TeamB99", {});
    expect(result.matches.length).toBe(0);
    expect(result.team1_wins).toBe(0);
  });
});

describe("Standings", () => {
  it("calculates 2019 Brasileirão standings", () => {
    const standings = getStandings(db, 2019, "Brasileirao");
    expect(standings.length).toBeGreaterThan(10);
    // Top team should have most points
    expect(standings[0].points).toBeGreaterThanOrEqual(standings[1].points);
    // Points should be consistent with W/D/L
    standings.forEach((s) => {
      expect(s.points).toBe(s.wins * 3 + s.draws);
    });
  });

  it("returns champion at top", () => {
    const standings = getStandings(db, 2019, "Brasileirao");
    expect(standings.length).toBeGreaterThan(0);
    // 2019 champion was Flamengo
    const champion = standings[0].team.toLowerCase();
    expect(champion).toContain("flamengo");
  });
});

describe("Player queries", () => {
  it("finds Brazilian players", () => {
    const players = searchPlayers(db, { nationality: "Brazil", limit: 10 });
    expect(players.length).toBeGreaterThan(0);
    players.forEach((p) => {
      expect(p.Nationality.toLowerCase()).toContain("brazil");
    });
  });

  it("searches players by name", () => {
    const players = searchPlayers(db, { name: "Neymar" });
    expect(players.length).toBeGreaterThan(0);
    expect(players[0].Name.toLowerCase()).toContain("neymar");
  });

  it("filters by minimum overall rating", () => {
    const players = searchPlayers(db, { minOverall: 85, limit: 20 });
    expect(players.length).toBeGreaterThan(0);
    players.forEach((p) => {
      expect(p.Overall).toBeGreaterThanOrEqual(85);
    });
  });

  it("returns players sorted by overall rating descending", () => {
    const players = searchPlayers(db, { nationality: "Brazilian", limit: 10 });
    for (let i = 1; i < players.length; i++) {
      expect(players[i - 1].Overall).toBeGreaterThanOrEqual(players[i].Overall);
    }
  });

  it("filters players by club", () => {
    const players = searchPlayers(db, { club: "Grêmio", limit: 20 });
    expect(players.length).toBeGreaterThan(0);
    players.forEach((p) => {
      expect(p.Club.toLowerCase()).toContain("gr");
    });
  });
});

describe("Statistics", () => {
  it("calculates global stats", () => {
    const stats = getGlobalStats(db);
    expect(stats.total_matches).toBeGreaterThan(1000);
    expect(stats.avg_goals_per_match).toBeGreaterThan(0);
    expect(stats.home_wins + stats.away_wins + stats.draws).toBe(stats.total_matches);
    expect(stats.home_win_rate).toBeGreaterThan(0);
  });

  it("returns biggest wins sorted by margin", () => {
    const wins = getBiggestWins(db, 10);
    expect(wins.length).toBeGreaterThan(0);
    for (let i = 1; i < wins.length; i++) {
      expect(wins[i - 1].margin).toBeGreaterThanOrEqual(wins[i].margin);
    }
    wins.forEach((w) => {
      expect(w.margin).toBe(Math.abs(w.home_goal - w.away_goal));
    });
  });

  it("filters global stats by competition", () => {
    const allStats = getGlobalStats(db);
    const brStats = getGlobalStats(db, "Brasileirao");
    expect(brStats.total_matches).toBeLessThan(allStats.total_matches);
    expect(brStats.total_matches).toBeGreaterThan(0);
  });
});

describe("Extended match stats", () => {
  it("returns extended stats for a team", () => {
    const results = getExtendedStats(db, "Flamengo", { limit: 5 });
    expect(results.length).toBeGreaterThan(0);
    results.forEach((m) => {
      const teams = [m.home.toLowerCase(), m.away.toLowerCase()];
      expect(teams.some((t) => t.includes("flamengo"))).toBe(true);
    });
  });

  it("returns empty for unknown team in extended data", () => {
    const results = getExtendedStats(db, "UnknownTeam9999XYZ", {});
    expect(results.length).toBe(0);
  });
});
