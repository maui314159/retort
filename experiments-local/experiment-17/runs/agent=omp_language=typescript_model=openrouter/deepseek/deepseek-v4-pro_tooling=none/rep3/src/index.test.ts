/**
 * Brazilian Soccer MCP Server - Tests
 *
 * Tests the data loading and query capabilities.
 * Run with: npx tsx --test src/*.test.ts
 */

import { describe, it } from "node:test";
import * as assert from "node:assert/strict";

import {
  searchMatches,
  getTeamStats,
  getHeadToHead,
  getStandings,
  getBiggestWins,
  getGoalAverages,
  getHomeAwayStats,
  getAllMatches,
} from "./match-db.js";

import {
  searchPlayers,
  getPlayerDetails,
  getTopPlayers,
  getClubSummaries,
  getAllPlayers,
} from "./player-db.js";

import { normalizeTeam, teamMatches } from "./team-normalizer.js";

// ============================================================================
// Data Loading Tests
// ============================================================================

describe("Data Loading", () => {
  it("loads all matches", () => {
    const matches = getAllMatches();
    assert.ok(matches.length > 10000, `Expected >10000 matches, got ${matches.length}`);
  });

  it("loads all players", () => {
    const players = getAllPlayers();
    assert.ok(players.length > 10000, `Expected >10000 players, got ${players.length}`);
  });

  it("loads within reasonable time", () => {
    // Already loaded (cached), this is just verifying the cache works
    const start = Date.now();
    const matches = getAllMatches();
    const elapsed = Date.now() - start;
    assert.ok(matches.length > 0);
    assert.ok(elapsed < 100, `Cached load should be fast, took ${elapsed}ms`);
  });
});

// ============================================================================
// Team Name Normalization Tests
// ============================================================================

describe("Team Normalizer", () => {
  it("normalizes team names with state suffix", () => {
    assert.equal(normalizeTeam("Flamengo-RJ"), "Flamengo");
    assert.equal(normalizeTeam("Palmeiras-SP"), "Palmeiras");
    assert.equal(normalizeTeam("Corinthians-SP"), "Corinthians");
  });

  it("normalizes accented team names", () => {
    assert.equal(normalizeTeam("São Paulo"), "São Paulo");
    assert.equal(normalizeTeam("Sao Paulo"), "São Paulo");
    assert.equal(normalizeTeam("Grêmio"), "Grêmio");
    assert.equal(normalizeTeam("Gremio"), "Grêmio");
  });

  it("normalizes Atlético Mineiro variations", () => {
    assert.equal(normalizeTeam("Atlético-MG"), "Atlético-MG");
    assert.equal(normalizeTeam("Atletico-MG"), "Atlético-MG");
    assert.equal(normalizeTeam("Atlético Mineiro"), "Atlético-MG");
    assert.equal(normalizeTeam("Atletico Mineiro"), "Atlético-MG");
  });

  it("normalizes Athletico Paranaense variations", () => {
    assert.equal(normalizeTeam("Athletico-PR"), "Athletico-PR");
    assert.equal(normalizeTeam("Atlético-PR"), "Athletico-PR");
    assert.equal(normalizeTeam("Athletico Paranaense"), "Athletico-PR");
    assert.equal(normalizeTeam("Atlético Paranaense"), "Athletico-PR");
  });

  it("normalizes EC Bahia to Bahia", () => {
    assert.equal(normalizeTeam("EC Bahia"), "Bahia");
    assert.equal(normalizeTeam("Bahia-BA"), "Bahia");
  });

  it("teamMatches works for partial queries", () => {
    assert.ok(teamMatches("Flamengo-RJ", "Flamengo"));
    assert.ok(teamMatches("São Paulo-SP", "Sao Paulo"));
    assert.ok(teamMatches("Atlético Mineiro", "Atletico"));
    assert.ok(teamMatches("Grêmio-RS", "Gremio"));
  });
});

// ============================================================================
// Match Query Tests
// ============================================================================

describe("Match Queries", () => {
  it("finds matches by team", () => {
    const matches = searchMatches({ team: "Flamengo", limit: 10 });
    assert.ok(matches.length > 0, "Should find Flamengo matches");
    for (const m of matches) {
      const hasFlamengo =
        m.home_team === "Flamengo" || m.away_team === "Flamengo";
      assert.ok(hasFlamengo, `Match should involve Flamengo: ${m.home_team} vs ${m.away_team}`);
    }
  });

  it("finds matches by season", () => {
    const matches = searchMatches({ season: 2023, limit: 20 });
    assert.ok(matches.length > 0, "Should find 2023 matches");
    for (const m of matches) {
      assert.equal(m.season, 2023, `Expected season 2023, got ${m.season}`);
    }
  });

  it("finds matches by competition", () => {
    const copa = searchMatches({ competition: "Copa do Brasil", limit: 10 });
    assert.ok(copa.length > 0, "Should find Copa do Brasil matches");
    for (const m of copa) {
      assert.ok(
        m.competition.toLowerCase().includes("copa do brasil"),
        `Expected Copa do Brasil, got ${m.competition}`,
      );
    }
  });

  it("finds Libertadores matches", () => {
    const lib = searchMatches({ competition: "Libertadores", limit: 10 });
    assert.ok(lib.length > 0, "Should find Libertadores matches");
    for (const m of lib) {
      assert.ok(
        m.competition.toLowerCase().includes("libertadores"),
        `Expected Libertadores, got ${m.competition}`,
      );
    }
  });

  it("finds Libertadores finals", () => {
    const finals = searchMatches({ competition: "Libertadores", round: "final", limit: 10 });
    assert.ok(finals.length > 0, "Should find Libertadores finals");
  });

  it("finds Flamengo vs Fluminense derbies", () => {
    const matches = searchMatches({ homeTeam: "Flamengo", awayTeam: "Fluminense", limit: 10 });
    // Also search the other way
    const matches2 = searchMatches({ homeTeam: "Fluminense", awayTeam: "Flamengo", limit: 10 });
    const total = matches.length + matches2.length;
    assert.ok(total > 0, `Should find Fla-Flu matches, got ${total}`);
  });

  it("finds Copa do Brasil round 8 (final) matches", () => {
    const finals = searchMatches({ competition: "Copa do Brasil", round: "8", limit: 10 });
    assert.ok(finals.length > 0, "Should find Copa do Brasil round 8 matches");
  });

  it("returns matches sorted by date descending", () => {
    const matches = searchMatches({ team: "Flamengo", limit: 5 });
    if (matches.length >= 2) {
      assert.ok(matches[0].date >= matches[1].date, "First match should be more recent");
    }
  });
});

// ============================================================================
// Team Stats Tests
// ============================================================================

describe("Team Statistics", () => {
  it("gets Flamengo stats", () => {
    const stats = getTeamStats("Flamengo");
    assert.ok(stats.matches > 0, "Flamengo should have matches");
    assert.ok(stats.wins + stats.draws + stats.losses === stats.matches,
      "W+D+L should equal total matches");
    assert.ok(stats.goalDiff === stats.goalsFor - stats.goalsAgainst,
      "Goal difference should be correct");
  });

  it("gets Palmeiras 2022 stats", () => {
    const stats = getTeamStats("Palmeiras", 2022);
    assert.ok(stats.matches > 0, "Palmeiras should have 2022 matches");
  });

  it("gets Copa do Brasil stats for a team", () => {
    const stats = getTeamStats("Flamengo", undefined, "Copa do Brasil");
    assert.ok(stats.matches > 0, "Flamengo should have Copa do Brasil matches");
  });

  it("handles unknown teams", () => {
    const stats = getTeamStats("ZZZUnknownTeam");
    assert.equal(stats.matches, 0);
  });
});

// ============================================================================
// Head-to-Head Tests
// ============================================================================

describe("Head-to-Head", () => {
  it("gets Flamengo vs Fluminense head-to-head", () => {
    const h2h = getHeadToHead("Flamengo", "Fluminense");
    assert.ok(h2h.totalMatches > 0, "Should have Fla-Flu history");
    assert.equal(h2h.team1, "Flamengo");
    assert.equal(h2h.team2, "Fluminense");
    assert.equal(
      h2h.team1Wins + h2h.team2Wins + h2h.draws,
      h2h.totalMatches,
      "Wins + draws should equal total matches",
    );
  });

  it("gets Palmeiras vs Corinthians head-to-head", () => {
    const h2h = getHeadToHead("Palmeiras", "Corinthians");
    assert.ok(h2h.totalMatches > 0, "Should have Derby Paulista history");
  });
});

// ============================================================================
// Standings Tests
// ============================================================================

describe("Standings", () => {
  it("computes 2019 Brasileirão standings", () => {
    const standings = getStandings(2019);
    assert.ok(standings.length >= 15, `Should have at least 15 teams, got ${standings.length}`);

    // First place should have the most points
    assert.ok(
      standings[0].points >= standings[1].points,
      `1st place should have >= points than 2nd: ${standings[0].points} vs ${standings[1].points}`,
    );

    // Check that points calculation is correct
    for (const s of standings) {
      const calculatedPoints = s.wins * 3 + s.draws;
      assert.equal(s.points, calculatedPoints,
        `${s.team}: points ${s.points} should be ${calculatedPoints} (${s.wins}W ${s.draws}D)`);
    }
  });

  it("computes 2023 Brasileirão standings", () => {
    const standings = getStandings(2023);
    assert.ok(standings.length > 0, "Should have 2023 standings");
  });
});

// ============================================================================
// Statistical Analysis Tests
// ============================================================================

describe("Statistical Analysis", () => {
  it("gets biggest wins", () => {
    const wins = getBiggestWins(5);
    assert.ok(wins.length > 0, "Should have big wins");
    // First result should have the largest goal difference
    const firstDiff = Math.abs(wins[0].home_goal - wins[0].away_goal);
    assert.ok(firstDiff >= 5, `Goal difference should be >= 5, got ${firstDiff}`);
  });

  it("gets goal averages", () => {
    const stats = getGoalAverages();
    assert.ok(stats.totalMatches > 0, "Should have matches");
    assert.ok(stats.avgGoalsPerMatch > 0, "Should have positive goal average");
    assert.ok(stats.avgGoalsPerMatch < 10, "Goal average should be reasonable");
    // Home win rate + draw rate + away win rate should be ~1.0
    const total = stats.homeWinRate + stats.drawRate + stats.awayWinRate;
    assert.ok(Math.abs(total - 1.0) < 0.01, `Rates should sum to 1.0, got ${total}`);
  });

  it("gets home/away stats for a team", () => {
    const stats = getHomeAwayStats("Flamengo");
    assert.equal(stats.home.matches + stats.away.matches, stats.overall.matches,
      "Home + away matches should equal overall");
    assert.ok(stats.home.matches > 0, "Should have home matches");
    assert.ok(stats.away.matches > 0, "Should have away matches");
  });
});

// ============================================================================
// Player Query Tests
// ============================================================================

describe("Player Queries", () => {
  it("searches players by name", () => {
    const players = searchPlayers({ name: "Neymar", limit: 5 });
    assert.ok(players.length > 0, "Should find Neymar");
    assert.ok(players[0].name.toLowerCase().includes("neymar"));
  });

  it("searches Brazilian players", () => {
    const players = searchPlayers({ nationality: "Brazil", limit: 10 });
    assert.ok(players.length > 0, "Should find Brazilian players");
    for (const p of players) {
      assert.equal(p.nationality.toLowerCase(), "brazil");
    }
  });

  it("searches players by club", () => {
    const players = searchPlayers({ club: "Flamengo", limit: 10 });
    assert.ok(players.length > 0, "Should find Flamengo players");
  });

  it("searches players by position", () => {
    const gks = searchPlayers({ position: "GK", limit: 5 });
    assert.ok(gks.length > 0, "Should find goalkeepers");
    for (const p of gks) {
      assert.ok(p.position.includes("GK"), `Expected GK, got ${p.position}`);
    }
  });

  it("searches top-rated Brazilian players", () => {
    const players = searchPlayers({
      nationality: "Brazil",
      minOverall: 80,
      sortBy: "overall",
      limit: 5,
    });
    assert.ok(players.length > 0, "Should find high-rated Brazilians");
    assert.ok(players[0].overall >= 80);
  });

  it("gets player details", () => {
    const player = getPlayerDetails("Neymar Jr");
    assert.ok(player !== null, "Should find Neymar Jr");
    assert.ok(player!.name.includes("Neymar"));
    assert.ok(player!.overall > 80, "Neymar should be highly rated");
  });

  it("gets player details for Gabriel Barbosa", () => {
    const player = getPlayerDetails("Gabriel Barbosa");
    // May or may not be in the dataset - just verify no crash
    if (player) {
      assert.ok(player.name.toLowerCase().includes("gabriel"));
    }
  });

  it("gets top players overall", () => {
    const players = getTopPlayers(5);
    assert.equal(players.length, 5);
    assert.ok(players[0].overall >= players[1].overall,
      "First player should have highest rating");
  });

  it("gets top Brazilian players", () => {
    const players = getTopPlayers(5, "Brazil");
    assert.ok(players.length > 0, "Should find Brazilian top players");
    for (const p of players) {
      assert.equal(p.nationality.toLowerCase(), "brazil");
    }
  });

  it("gets club summaries", () => {
    const summaries = getClubSummaries();
    assert.ok(summaries.length > 0, "Should have club summaries");

    // Find Flamengo
    const flamengo = summaries.find((s) => s.club.toLowerCase().includes("flamengo"));
    if (flamengo) {
      assert.ok(flamengo.playerCount > 0);
      assert.ok(flamengo.avgRating > 0);
    }
  });
});

// ============================================================================
// Cross-File Query Tests
// ============================================================================

describe("Cross-File Queries", () => {
  it("can combine match and player data (e.g. Flamengo players and matches)", () => {
    const matches = searchMatches({ team: "Flamengo", limit: 5 });
    const players = searchPlayers({ club: "Flamengo", limit: 5 });
    assert.ok(matches.length > 0, "Should find Flamengo matches");
    assert.ok(players.length > 0, "Should find Flamengo players");
  });

  it("checks Palmeiras participation across competitions", () => {
    const stats = getTeamStats("Palmeiras");
    assert.ok(stats.competitions.length >= 1,
      `Palmeiras should appear in at least 1 competition, found ${stats.competitions.length}`);
  });
});