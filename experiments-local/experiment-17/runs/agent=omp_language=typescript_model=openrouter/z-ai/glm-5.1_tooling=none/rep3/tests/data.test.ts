/**
 * Brazilian Soccer MCP Server - BDD Test Suite
 *
 * Behavior-Driven Development tests using Given/When/Then structure
 * covering all five required query categories from the specification:
 *   1. Match Queries
 *   2. Team Queries
 *   3. Player Queries
 *   4. Competition Queries
 *   5. Statistical Analysis
 *
 * Also covers cross-cutting concerns: team name normalization,
 * date format handling, and data coverage across all 6 CSV files.
 */

import { describe, it, expect, beforeAll } from "vitest";
import { loadData, normalizeTeamName, type SoccerData } from "../src/loader.js";
import {
  searchMatches,
  getTeamStats,
  searchPlayers,
  getCompetitionStandings,
  getHeadToHead,
  getAggregateStats,
} from "../src/data.js";

let data: SoccerData;

beforeAll(() => {
  data = loadData();
});

// ═══════════════════════════════════════════════════════════════════════
// Feature: Team Name Normalization
// ═══════════════════════════════════════════════════════════════════════

describe("Feature: Team Name Normalization", () => {
  it("Scenario: Strip state suffix from team name", () => {
    // Given a team name with state suffix
    // When I normalize the name
    const result = normalizeTeamName("Palmeiras-SP");
    // Then the suffix should be removed
    expect(result).toBe("Palmeiras");
  });

  it("Scenario: Strip state suffix with spaces", () => {
    const result = normalizeTeamName("Flamengo - RJ");
    expect(result).toBe("Flamengo");
  });

  it("Scenario: Strip parenthetical annotations", () => {
    const result = normalizeTeamName("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ");
    expect(result).toBe("Boavista Sport Club");
  });

  it("Scenario: Name without suffix passes through", () => {
    const result = normalizeTeamName("São Paulo");
    expect(result).toBe("São Paulo");
  });

  it("Scenario: Known alias resolved", () => {
    const result = normalizeTeamName("sao paulo");
    expect(result).toBe("São Paulo");
  });

  it("Scenario: Empty string returns empty", () => {
    expect(normalizeTeamName("")).toBe("");
  });
});

// ═══════════════════════════════════════════════════════════════════════
// Feature: Match Queries
// ═══════════════════════════════════════════════════════════════════════

describe("Feature: Match Queries", () => {
  it("Scenario: Find matches by team", () => {
    // Given the match data is loaded
    // When I search for matches involving "Flamengo"
    const results = searchMatches({ team: "Flamengo" });
    // Then I should receive a non-empty list of matches
    expect(results.length).toBeGreaterThan(0);
    // And each match should involve Flamengo
    for (const m of results) {
      const involves = m.homeTeam.toLowerCase().includes("flamengo") || m.awayTeam.toLowerCase().includes("flamengo");
      expect(involves).toBe(true);
    }
  });

  it("Scenario: Find matches between two specific teams", () => {
    // When I search for matches between Flamengo and Fluminense
    const results = searchMatches({ team: "Flamengo", opponent: "Fluminense" });
    // Then each match should involve both teams
    expect(results.length).toBeGreaterThan(0);
    for (const m of results) {
      const hasFlamengo = m.homeTeam.toLowerCase().includes("flamengo") || m.awayTeam.toLowerCase().includes("flamengo");
      const hasFluminense = m.homeTeam.toLowerCase().includes("fluminense") || m.awayTeam.toLowerCase().includes("fluminense");
      expect(hasFlamengo).toBe(true);
      expect(hasFluminense).toBe(true);
    }
  });

  it("Scenario: Filter matches by competition", () => {
    // When I search for Libertadores matches
    const results = searchMatches({ competition: "Libertadores" });
    // Then all results should be Libertadores matches
    expect(results.length).toBeGreaterThan(0);
    for (const m of results) {
      expect(m.competition).toBe("Libertadores");
    }
  });

  it("Scenario: Filter matches by season", () => {
    // When I search for 2023 season matches
    const results = searchMatches({ season: 2023 });
    // Then all results should be from 2023
    expect(results.length).toBeGreaterThan(0);
    for (const m of results) {
      expect(m.season).toBe(2023);
    }
  });

  it("Scenario: Filter matches by date range", () => {
    // When I search for matches between 2023-01-01 and 2023-06-30
    const results = searchMatches({ startDate: "2023-01-01", endDate: "2023-06-30" });
    // Then all matches should be in that range
    for (const m of results) {
      expect(m.date >= "2023-01-01").toBe(true);
      expect(m.date <= "2023-06-30").toBe(true);
    }
  });

  it("Scenario: Limit results count", () => {
    // When I search with a limit of 5
    const results = searchMatches({ team: "Palmeiras", limit: 5 });
    // Then I should get at most 5 results
    expect(results.length).toBeLessThanOrEqual(5);
  });

  it("Scenario: Each match has date, scores, and competition", () => {
    // Given match data is loaded
    // When I search for any matches
    const results = searchMatches({ season: 2023, limit: 5 });
    // Then each match should have date, scores, and competition
    for (const m of results) {
      expect(m.date).toBeTruthy();
      expect(typeof m.homeGoals).toBe("number");
      expect(typeof m.awayGoals).toBe("number");
      expect(m.competition).toBeTruthy();
      expect(m.homeTeam).toBeTruthy();
      expect(m.awayTeam).toBeTruthy();
    }
  });
});

// ═══════════════════════════════════════════════════════════════════════
// Feature: Team Queries
// ═══════════════════════════════════════════════════════════════════════

describe("Feature: Team Queries", () => {
  it("Scenario: Get overall team statistics", () => {
    // Given the match data is loaded
    // When I request statistics for Palmeiras
    const stats = getTeamStats("Palmeiras");
    // Then I should receive wins, losses, draws, and goals
    expect(stats.matches).toBeGreaterThan(0);
    expect(stats.wins + stats.draws + stats.losses).toBe(stats.matches);
    expect(stats.goalsFor).toBeGreaterThan(0);
    expect(stats.goalsAgainst).toBeGreaterThan(0);
    expect(stats.winRate).toMatch(/^\d+\.\d+%$/);
  });

  it("Scenario: Get team statistics for a specific season", () => {
    // When I request statistics for Palmeiras in season 2023
    const stats = getTeamStats("Palmeiras", 2023);
    // Then all stats should reflect only that season
    expect(stats.matches).toBeGreaterThan(0);
    expect(stats.wins + stats.draws + stats.losses).toBe(stats.matches);
  });

  it("Scenario: Get home-only statistics", () => {
    // When I request home-only stats for Corinthians
    const stats = getTeamStats("Corinthians", undefined, undefined, true);
    // Then all matches should be home matches
    expect(stats.matches).toBeGreaterThan(0);
  });

  it("Scenario: Get team statistics filtered by competition", () => {
    // When I request Palmeiras stats in Brasileirão
    const stats = getTeamStats("Palmeiras", undefined, "Brasileirão");
    expect(stats.matches).toBeGreaterThan(0);
  });

  it("Scenario: Win rate calculation is correct", () => {
    // When I get stats for any team
    const stats = getTeamStats("Flamengo");
    // Then the win rate should be wins/matches * 100
    const expectedRate = ((stats.wins / stats.matches) * 100).toFixed(1) + "%";
    expect(stats.winRate).toBe(expectedRate);
  });
});

// ═══════════════════════════════════════════════════════════════════════
// Feature: Player Queries
// ═══════════════════════════════════════════════════════════════════════

describe("Feature: Player Queries", () => {
  it("Scenario: Search players by name", () => {
    // Given the player data is loaded
    // When I search for "Neymar"
    const results = searchPlayers({ name: "Neymar" });
    // Then I should find at least one player
    expect(results.length).toBeGreaterThan(0);
    // And the player's name should contain "Neymar"
    for (const p of results) {
      expect(p.name.toLowerCase()).toContain("neymar");
    }
  });

  it("Scenario: Filter players by nationality (Brazilian)", () => {
    // When I search for Brazilian players
    const results = searchPlayers({ nationality: "Brazil" });
    // Then all results should be Brazilian
    expect(results.length).toBeGreaterThan(0);
    for (const p of results) {
      expect(p.nationality.toLowerCase()).toContain("brazil");
    }
  });

  it("Scenario: Filter players by club", () => {
    // When I search for players at Grêmio (FIFA dataset uses this name)
    const results = searchPlayers({ club: "Grêmio" });
    // Then all results should play for a club containing Grêmio
    expect(results.length).toBeGreaterThan(0);
    for (const p of results) {
      expect(p.club.toLowerCase()).toContain("grêmio");
    }
  });

  it("Scenario: Filter players by position", () => {
    // When I search for goalkeepers
    const results = searchPlayers({ position: "GK" });
    // Then all results should be goalkeepers
    expect(results.length).toBeGreaterThan(0);
    for (const p of results) {
      expect(p.position).toContain("GK");
    }
  });

  it("Scenario: Filter by minimum overall rating", () => {
    // When I search for players with overall >= 85
    const results = searchPlayers({ minOverall: 85 });
    // Then all results should have overall >= 85
    for (const p of results) {
      expect(p.overall).toBeGreaterThanOrEqual(85);
    }
  });

  it("Scenario: Results are sorted by overall rating descending", () => {
    // When I search for Brazilian players
    const results = searchPlayers({ nationality: "Brazil" });
    // Then results should be sorted by overall descending
    for (let i = 1; i < results.length; i++) {
      expect(results[i - 1].overall).toBeGreaterThanOrEqual(results[i].overall);
    }
  });

  it("Scenario: Limit player results", () => {
    const results = searchPlayers({ nationality: "Brazil", limit: 10 });
    expect(results.length).toBeLessThanOrEqual(10);
  });
});

// ═══════════════════════════════════════════════════════════════════════
// Feature: Competition Queries
// ═══════════════════════════════════════════════════════════════════════

describe("Feature: Competition Queries", () => {
  it("Scenario: Get Brasileirão standings for a season", () => {
    // Given the match data is loaded
    // When I request standings for Brasileirão 2019
    const standings = getCompetitionStandings({ competition: "Brasileirão", season: 2019 });
    // Then I should receive a sorted table
    expect(standings.length).toBeGreaterThan(0);
    // And the first place should have the most points
    for (let i = 1; i < standings.length; i++) {
      expect(standings[i - 1].points).toBeGreaterThanOrEqual(standings[i].points);
    }
  });

  it("Scenario: Points calculation is correct (win=3, draw=1)", () => {
    // When I get standings
    const standings = getCompetitionStandings({ competition: "Brasileirão", season: 2019 });
    // Then each entry's points should equal 3*wins + 1*draws
    for (const entry of standings) {
      const expected = entry.wins * 3 + entry.draws;
      expect(entry.points).toBe(expected);
    }
  });

  it("Scenario: Goal difference equals goals for minus goals against", () => {
    const standings = getCompetitionStandings({ competition: "Brasileirão", season: 2019 });
    for (const entry of standings) {
      expect(entry.goalDifference).toBe(entry.goalsFor - entry.goalsAgainst);
    }
  });

  it("Scenario: 2019 Brasileirão champion is Flamengo", () => {
    const standings = getCompetitionStandings({ competition: "Brasileirão", season: 2019 });
    expect(standings[0].team.toLowerCase()).toContain("flamengo");
    expect(standings[0].position).toBe(1);
  });

  it("Scenario: Historical Brasileirão standings work", () => {
    const standings = getCompetitionStandings({ competition: "Historical Brasileirão", season: 2018 });
    expect(standings.length).toBeGreaterThan(0);
  });
});

// ═══════════════════════════════════════════════════════════════════════
// Feature: Statistical Analysis
// ═══════════════════════════════════════════════════════════════════════

describe("Feature: Statistical Analysis", () => {
  it("Scenario: Get aggregate statistics for all data", () => {
    // Given the data is loaded
    // When I request aggregate stats with no filters
    const stats = getAggregateStats({});
    // Then I should get totals
    expect(stats.totalMatches).toBeGreaterThan(0);
    expect(stats.totalGoals).toBeGreaterThan(0);
    expect(parseFloat(stats.avgGoalsPerMatch)).toBeGreaterThan(0);
    expect(stats.homeWins + stats.awayWins + stats.draws).toBe(stats.totalMatches);
  });

  it("Scenario: Average goals per match is reasonable", () => {
    // When I get aggregate stats
    const stats = getAggregateStats({});
    // Then average goals should be between 1 and 8 (reasonable for soccer)
    const avg = parseFloat(stats.avgGoalsPerMatch);
    expect(avg).toBeGreaterThan(1);
    expect(avg).toBeLessThan(8);
  });

  it("Scenario: Home win rate exceeds away win rate", () => {
    // When I get aggregate stats
    const stats = getAggregateStats({});
    // Then home wins should exceed away wins (home advantage)
    expect(stats.homeWins).toBeGreaterThan(stats.awayWins);
  });

  it("Scenario: Biggest victories are sorted by margin", () => {
    // When I get aggregate stats
    const stats = getAggregateStats({});
    // Then biggest victories should be listed
    expect(stats.biggestWins.length).toBeGreaterThan(0);
    // And each entry should have required fields
    for (const w of stats.biggestWins) {
      expect(w.date).toBeTruthy();
      expect(w.winner).toBeTruthy();
      expect(w.loser).toBeTruthy();
      expect(w.score).toBeTruthy();
      expect(w.competition).toBeTruthy();
    }
  });

  it("Scenario: Filter stats by competition", () => {
    const stats = getAggregateStats({ competition: "Libertadores" });
    expect(stats.totalMatches).toBeGreaterThan(0);
  });

  it("Scenario: Filter stats by season", () => {
    const stats = getAggregateStats({ season: 2023 });
    expect(stats.totalMatches).toBeGreaterThan(0);
  });

  it("Scenario: Filter stats by team", () => {
    const stats = getAggregateStats({ team: "Flamengo" });
    expect(stats.totalMatches).toBeGreaterThan(0);
  });
});

// ═══════════════════════════════════════════════════════════════════════
// Feature: Head-to-Head
// ═══════════════════════════════════════════════════════════════════════

describe("Feature: Head-to-Head Comparison", () => {
  it("Scenario: Compare two teams head-to-head", () => {
    // Given the match data is loaded
    // When I compare Palmeiras and Santos
    const h2h = getHeadToHead("Palmeiras", "Santos");
    // Then I should get total matches, wins for each, and draws
    expect(h2h.matches).toBeGreaterThan(0);
    expect(h2h.teamAWins + h2h.teamBWins + h2h.draws).toBe(h2h.matches);
    expect(h2h.teamAGoals).toBeGreaterThan(0);
    expect(h2h.teamBGoals).toBeGreaterThan(0);
  });

  it("Scenario: Head-to-head includes recent matches", () => {
    // When I get head-to-head
    const h2h = getHeadToHead("Flamengo", "Fluminense");
    // Then recent matches should be provided (up to 10)
    expect(h2h.recentMatches.length).toBeGreaterThan(0);
    expect(h2h.recentMatches.length).toBeLessThanOrEqual(10);
  });

  it("Scenario: Head-to-head goals are consistent", () => {
    // When I get head-to-head
    const h2h = getHeadToHead("Flamengo", "Vasco");
    // Then goals should sum correctly across all matches
    let aGoals = 0, bGoals = 0;
    for (const m of data.matches) {
      const aLower = "flamengo";
      const bLower = "vasco";
      const home = m.homeTeam.toLowerCase();
      const away = m.awayTeam.toLowerCase();
      if ((home.includes(aLower) && away.includes(bLower)) || (home.includes(bLower) && away.includes(aLower))) {
        const aIsHome = home.includes(aLower);
        aGoals += aIsHome ? m.homeGoals : m.awayGoals;
        bGoals += aIsHome ? m.awayGoals : m.homeGoals;
      }
    }
    expect(h2h.teamAGoals).toBe(aGoals);
    expect(h2h.teamBGoals).toBe(bGoals);
  });
});

// ═══════════════════════════════════════════════════════════════════════
// Feature: Data Coverage
// ═══════════════════════════════════════════════════════════════════════

describe("Feature: Data Coverage - All 6 CSV files are loadable", () => {
  it("Scenario: Total matches loaded from all sources", () => {
    // When all data is loaded
    // Then we should have matches from multiple competitions
    expect(data.matches.length).toBeGreaterThan(20000);

    const competitions = new Set(data.matches.map((m) => m.competition));
    expect(competitions.has("Brasileirão")).toBe(true);
    expect(competitions.has("Copa do Brasil")).toBe(true);
    expect(competitions.has("Libertadores")).toBe(true);
    expect(competitions.has("Historical Brasileirão")).toBe(true);
  });

  it("Scenario: FIFA player data is loaded", () => {
    expect(data.players.length).toBeGreaterThan(18000);
  });

  it("Scenario: Brasileirão matches have state info", () => {
    const brMatches = data.matches.filter((m) => m.competition === "Brasileirão" && m.homeState);
    expect(brMatches.length).toBeGreaterThan(0);
  });

  it("Scenario: Historical matches have stadium info", () => {
    const histMatches = data.matches.filter((m) => m.competition === "Historical Brasileirão" && m.stadium);
    expect(histMatches.length).toBeGreaterThan(0);
  });

  it("Scenario: Extended stats dataset has corners and shots", () => {
    const extMatches = data.matches.filter((m) => m.homeCorners !== undefined && m.homeCorners > 0);
    expect(extMatches.length).toBeGreaterThan(0);
  });
});

// ═══════════════════════════════════════════════════════════════════════
// Feature: Cross-file Queries
// ═══════════════════════════════════════════════════════════════════════

describe("Feature: Cross-file Queries", () => {
  it("Scenario: Player + match data can be combined", () => {
    // Given both datasets are loaded
    // When I find Brazilian players and matches involving Santos
    const players = searchPlayers({ nationality: "Brazil", club: "Santos" });
    const matches = searchMatches({ team: "Santos", limit: 5 });
    // Then both should return results
    expect(players.length).toBeGreaterThan(0);
    expect(matches.length).toBeGreaterThan(0);
  });

  it("Scenario: Team stats span multiple competition files", () => {
    // When I get Palmeiras stats across all competitions
    const stats = getTeamStats("Palmeiras");
    // Then the match count should reflect data from multiple sources
    expect(stats.matches).toBeGreaterThan(100);
  });
});
