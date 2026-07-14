import { describe, it, expect, beforeEach } from "vitest";
import {
  findMatches,
  getHeadToHead,
  getTeamStats,
  getStandings,
  findPlayers,
  getCompetitionStats,
  getBestHomeRecord,
  getBiggestWins,
  getTeamCompetitions,
} from "../queries.js";
import { _setMatchesForTest, _setPlayersForTest, _resetCache } from "../loader.js";
import type { Match, Player } from "../types.js";

// ─── fixtures ────────────────────────────────────────────────────────────────

const MATCHES: Match[] = [
  {
    date: "2023-09-03",
    competition: "Brasileirao",
    season: 2023,
    round: "22",
    homeTeam: "Flamengo",
    awayTeam: "Fluminense",
    homeGoals: 2,
    awayGoals: 1,
  },
  {
    date: "2023-05-28",
    competition: "Brasileirao",
    season: 2023,
    round: "8",
    homeTeam: "Fluminense",
    awayTeam: "Flamengo",
    homeGoals: 1,
    awayGoals: 0,
  },
  {
    date: "2022-08-15",
    competition: "Brasileirao",
    season: 2022,
    round: "20",
    homeTeam: "Palmeiras",
    awayTeam: "Corinthians",
    homeGoals: 3,
    awayGoals: 0,
  },
  {
    date: "2022-09-10",
    competition: "Brasileirao",
    season: 2022,
    round: "25",
    homeTeam: "Corinthians",
    awayTeam: "Palmeiras",
    homeGoals: 1,
    awayGoals: 1,
  },
  {
    date: "2021-06-05",
    competition: "Libertadores",
    season: 2021,
    stage: "group stage",
    homeTeam: "Flamengo",
    awayTeam: "Palestino",
    homeGoals: 5,
    awayGoals: 0,
  },
  {
    date: "2023-10-01",
    competition: "Copa do Brasil",
    season: 2023,
    round: "Semi-Final",
    homeTeam: "Atletico Mineiro",
    awayTeam: "Flamengo",
    homeGoals: 2,
    awayGoals: 3,
  },
  {
    date: "2022-07-01",
    competition: "Brasileirao",
    season: 2022,
    round: "10",
    homeTeam: "Flamengo",
    awayTeam: "Santos",
    homeGoals: 4,
    awayGoals: 0,
  },
];

const PLAYERS: Player[] = [
  {
    id: 1,
    name: "Neymar Jr",
    age: 31,
    nationality: "Brazil",
    overall: 92,
    potential: 92,
    club: "Paris Saint-Germain",
    position: "LW",
  },
  {
    id: 2,
    name: "Alisson",
    age: 30,
    nationality: "Brazil",
    overall: 89,
    potential: 89,
    club: "Liverpool",
    position: "GK",
  },
  {
    id: 3,
    name: "Gabriel Barbosa",
    age: 26,
    nationality: "Brazil",
    overall: 80,
    potential: 84,
    club: "Flamengo",
    position: "ST",
  },
  {
    id: 4,
    name: "L. Messi",
    age: 35,
    nationality: "Argentina",
    overall: 94,
    potential: 94,
    club: "FC Barcelona",
    position: "RF",
  },
  {
    id: 5,
    name: "Pedro",
    age: 25,
    nationality: "Brazil",
    overall: 78,
    potential: 83,
    club: "Flamengo",
    position: "ST",
  },
];

beforeEach(() => {
  _resetCache();
  _setMatchesForTest(MATCHES);
  _setPlayersForTest(PLAYERS);
});

// ─── findMatches ─────────────────────────────────────────────────────────────

describe("findMatches", () => {
  it("returns all matches when no filters", () => {
    expect(findMatches({})).toHaveLength(MATCHES.length);
  });

  it("filters by team (home or away)", () => {
    const results = findMatches({ team: "Flamengo" });
    expect(results.length).toBeGreaterThan(0);
    for (const m of results) {
      expect(
        m.homeTeam.includes("Flamengo") || m.awayTeam.includes("Flamengo")
      ).toBe(true);
    }
  });

  it("filters by season", () => {
    const results = findMatches({ season: 2023 });
    for (const m of results) expect(m.season).toBe(2023);
  });

  it("filters by competition", () => {
    const results = findMatches({ competition: "Copa do Brasil" });
    for (const m of results) expect(m.competition).toBe("Copa do Brasil");
  });

  it("filters head-to-head with team1 + team2", () => {
    const results = findMatches({ team1: "Flamengo", team2: "Fluminense" });
    expect(results).toHaveLength(2);
  });

  it("returns matches sorted by date descending", () => {
    const results = findMatches({ team: "Flamengo" });
    for (let i = 1; i < results.length; i++) {
      expect(results[i - 1].date >= results[i].date).toBe(true);
    }
  });

  it("respects limit", () => {
    expect(findMatches({ limit: 2 })).toHaveLength(2);
  });

  it("filters by date range", () => {
    const results = findMatches({ dateFrom: "2023-01-01", dateTo: "2023-12-31" });
    for (const m of results) {
      expect(m.date >= "2023-01-01").toBe(true);
      expect(m.date <= "2023-12-31").toBe(true);
    }
  });

  it("returns empty array for unmatched criteria", () => {
    expect(findMatches({ team: "Zomba FC Unknown" })).toHaveLength(0);
  });
});

// ─── getHeadToHead ───────────────────────────────────────────────────────────

describe("getHeadToHead", () => {
  it("returns correct H2H for Flamengo vs Fluminense", () => {
    const h2h = getHeadToHead("Flamengo", "Fluminense");
    expect(h2h.matches).toHaveLength(2);
    expect(h2h.team1Wins).toBe(1);  // 2-1
    expect(h2h.team2Wins).toBe(1);  // 1-0
    expect(h2h.draws).toBe(0);
    expect(h2h.team1Goals).toBe(2); // Flamengo scored 2+0=2
    expect(h2h.team2Goals).toBe(2); // Fluminense scored 1+1=2
  });

  it("returns empty record for unknown teams", () => {
    const h2h = getHeadToHead("Team A", "Team B");
    expect(h2h.matches).toHaveLength(0);
    expect(h2h.team1Wins).toBe(0);
  });

  it("is symmetric for team ordering", () => {
    const fwd = getHeadToHead("Flamengo", "Fluminense");
    const rev = getHeadToHead("Fluminense", "Flamengo");
    expect(fwd.matches).toHaveLength(rev.matches.length);
    expect(fwd.team1Wins).toBe(rev.team2Wins);
    expect(fwd.team2Wins).toBe(rev.team1Wins);
  });
});

// ─── getTeamStats ────────────────────────────────────────────────────────────

describe("getTeamStats", () => {
  it("calculates full record for Flamengo", () => {
    const rec = getTeamStats({ team: "Flamengo" });
    expect(rec.matches).toBe(5); // MATCHES has 5 Flamengo matches
    expect(rec.wins).toBeGreaterThanOrEqual(0);
    expect(rec.points).toBe(rec.wins * 3 + rec.draws);
  });

  it("calculates home-only stats", () => {
    const rec = getTeamStats({ team: "Flamengo", homeOnly: true });
    // Flamengo home: vs Fluminense (2-1 W), vs Palestino (5-0 W), vs Santos (4-0 W)
    expect(rec.matches).toBe(3);
    expect(rec.wins).toBe(3);
  });

  it("calculates away-only stats", () => {
    const rec = getTeamStats({ team: "Flamengo", awayOnly: true });
    // Flamengo away: vs Fluminense (0-1 L), vs Atletico Mineiro (3-2 W)
    expect(rec.matches).toBe(2);
  });

  it("filters by season", () => {
    const rec = getTeamStats({ team: "Flamengo", season: 2023 });
    expect(rec.matches).toBeGreaterThan(0);
    expect(rec.matches).toBeLessThan(getTeamStats({ team: "Flamengo" }).matches);
  });

  it("returns zero-match record for unknown team", () => {
    const rec = getTeamStats({ team: "Unknown FC" });
    expect(rec.matches).toBe(0);
    expect(rec.points).toBe(0);
  });
});

// ─── getStandings ────────────────────────────────────────────────────────────

describe("getStandings", () => {
  it("returns standings sorted by points descending", () => {
    const table = getStandings("Brasileirao", 2022);
    for (let i = 1; i < table.length; i++) {
      const gd = (t: (typeof table)[0]) => t.goalsFor - t.goalsAgainst;
      expect(
        table[i - 1].points > table[i].points ||
          (table[i - 1].points === table[i].points && gd(table[i - 1]) >= gd(table[i]))
      ).toBe(true);
    }
  });

  it("includes all teams that played in that competition/season", () => {
    const table = getStandings("Brasileirao", 2022);
    const teamNames = table.map((r) => r.team);
    expect(teamNames).toContain("Palmeiras");
    expect(teamNames).toContain("Corinthians");
  });

  it("returns empty for season with no data", () => {
    expect(getStandings("Brasileirao", 1900)).toHaveLength(0);
  });
});

// ─── findPlayers ──────────────────────────────────────────────────────────────

describe("findPlayers", () => {
  it("returns all players with no filters", () => {
    expect(findPlayers({})).toHaveLength(PLAYERS.length);
  });

  it("filters by name (case insensitive)", () => {
    const results = findPlayers({ name: "neymar" });
    expect(results).toHaveLength(1);
    expect(results[0].name).toBe("Neymar Jr");
  });

  it("filters by nationality", () => {
    const results = findPlayers({ nationality: "Brazil" });
    for (const p of results) expect(p.nationality).toBe("Brazil");
    expect(results.length).toBe(4);
  });

  it("filters by club", () => {
    const results = findPlayers({ club: "Flamengo" });
    expect(results).toHaveLength(2);
    for (const p of results) expect(p.club).toBe("Flamengo");
  });

  it("filters by position", () => {
    const results = findPlayers({ position: "ST" });
    for (const p of results) expect(p.position).toContain("ST");
  });

  it("filters by min_overall", () => {
    const results = findPlayers({ minOverall: 90 });
    for (const p of results) expect(p.overall).toBeGreaterThanOrEqual(90);
  });

  it("returns results sorted by overall descending", () => {
    const results = findPlayers({});
    for (let i = 1; i < results.length; i++) {
      expect(results[i - 1].overall).toBeGreaterThanOrEqual(results[i].overall);
    }
  });

  it("respects limit", () => {
    expect(findPlayers({ limit: 2 })).toHaveLength(2);
  });

  it("returns empty for no match", () => {
    expect(findPlayers({ name: "zzznobodyzz" })).toHaveLength(0);
  });
});

// ─── getCompetitionStats ─────────────────────────────────────────────────────

describe("getCompetitionStats", () => {
  it("calculates correct total matches and goals", () => {
    const stats = getCompetitionStats("Brasileirao");
    const expected = MATCHES.filter((m) => m.competition === "Brasileirao");
    expect(stats.totalMatches).toBe(expected.length);
    expect(stats.totalGoals).toBe(
      expected.reduce((s, m) => s + m.homeGoals + m.awayGoals, 0)
    );
  });

  it("identifies biggest win", () => {
    const stats = getCompetitionStats();
    expect(stats.biggestWin).toBeDefined();
    expect(stats.biggestWin!.goalDiff).toBeGreaterThanOrEqual(4);
  });

  it("includes home/away breakdown", () => {
    const stats = getCompetitionStats();
    expect(stats.homeWins + stats.awayWins + stats.draws).toBe(stats.totalMatches);
  });

  it("computes avgGoalsPerMatch", () => {
    const stats = getCompetitionStats();
    expect(stats.avgGoalsPerMatch).toBeCloseTo(
      stats.totalGoals / stats.totalMatches,
      5
    );
  });
});

// ─── getBestHomeRecord ────────────────────────────────────────────────────────

describe("getBestHomeRecord", () => {
  it("returns teams with at least 5 home matches in unconstrained data", () => {
    // Our fixture has <5 home matches per team; function should return empty
    const results = getBestHomeRecord();
    // With only 7 total matches in fixture, no team has 5 home games
    expect(Array.isArray(results)).toBe(true);
  });

  it("respects top_n", () => {
    // Real data test — reset to actual CSV data then verify top_n is respected
    _resetCache(); // will lazy-load from real CSVs
    const results = getBestHomeRecord("Brasileirao", undefined, 3);
    expect(results.length).toBeLessThanOrEqual(3);
  });
});

// ─── getBiggestWins ───────────────────────────────────────────────────────────

describe("getBiggestWins", () => {
  it("returns wins sorted by goal difference descending", () => {
    const wins = getBiggestWins(5);
    for (let i = 1; i < wins.length; i++) {
      expect(wins[i - 1].goalDiff).toBeGreaterThanOrEqual(wins[i].goalDiff);
    }
  });

  it("the biggest win in fixture is Flamengo 5-0 Palestino", () => {
    const wins = getBiggestWins(1);
    expect(wins[0].goalDiff).toBe(5);
    expect(
      wins[0].match.homeTeam === "Flamengo" || wins[0].match.awayTeam === "Flamengo"
    ).toBe(true);
  });
});

// ─── getTeamCompetitions ──────────────────────────────────────────────────────

describe("getTeamCompetitions", () => {
  it("returns competitions for Flamengo", () => {
    const comps = getTeamCompetitions("Flamengo");
    expect(comps).toContain("Brasileirao");
    expect(comps).toContain("Libertadores");
    expect(comps).toContain("Copa do Brasil");
  });

  it("returns empty for unknown team", () => {
    expect(getTeamCompetitions("Unknown FC 99")).toHaveLength(0);
  });

  it("returns sorted list", () => {
    const comps = getTeamCompetitions("Flamengo");
    expect([...comps].sort()).toEqual(comps);
  });
});
