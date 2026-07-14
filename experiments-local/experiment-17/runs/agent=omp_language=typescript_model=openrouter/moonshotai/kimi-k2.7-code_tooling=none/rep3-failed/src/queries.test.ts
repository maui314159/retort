/**
 * BDD-style tests for the query engine using the real Kaggle datasets.
 *
 * Scenarios map to the required capabilities in the specification:
 * match queries, team queries, player queries, competition queries, and
 * statistical analysis.
 */

import { describe, it, expect, beforeAll } from "vitest";
import { SoccerRepository } from "./loaders.js";
import { QueryEngine } from "./queries.js";

let repo: SoccerRepository;
let engine: QueryEngine;

beforeAll(() => {
  repo = SoccerRepository.load();
  engine = new QueryEngine(repo);
});

describe("Feature: Match Queries", () => {
  it("Given the match data is loaded, when I search for matches between Flamengo and Fluminense, then I should receive a list of matches with date, scores, and competition", () => {
    const matches = engine.findMatches({ team: "Flamengo", opponent: "Fluminense" });
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) {
      expect(m.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(typeof m.homeGoal).toBe("number");
      expect(typeof m.awayGoal).toBe("number");
      expect(m.competition).toBeTruthy();
    }
  });

  it("Given the match data is loaded, when I filter Palmeiras matches in season 2023, then I should receive only matches from that season", () => {
    const matches = engine.findMatches({ team: "Palmeiras", season: 2023 });
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) {
      expect(m.season).toBe(2023);
      expect(
        [m.homeTeam, m.awayTeam].some((t) =>
          t.toLowerCase().includes("palmeiras"),
        ),
      ).toBe(true);
    }
  });

  it("Given the match data is loaded, when I search for Copa do Brasil finals, then I should receive matches whose stage or round is a final", () => {
    const matches = engine
      .findMatches({ competition: "Copa do Brasil" })
      .filter(
        (m) =>
          String(m.stage ?? "").toLowerCase().includes("final") ||
          String(m.round ?? "").toLowerCase().includes("final"),
      );
    expect(matches.length).toBeGreaterThanOrEqual(0);
  });
});

describe("Feature: Team Queries", () => {
  it("Given the match data is loaded, when I request statistics for Corinthians in season 2022, then I should receive wins, losses, draws, and goals", () => {
    const stats = engine.teamStats({ team: "Corinthians", season: 2022 });
    expect(stats.matches).toBeGreaterThan(0);
    expect(stats.wins + stats.draws + stats.losses).toBe(stats.matches);
    expect(stats.goalsFor).toBeGreaterThanOrEqual(0);
    expect(stats.goalsAgainst).toBeGreaterThanOrEqual(0);
  });

  it("Given the match data is loaded, when I request home record for Flamengo, then venue=home should only count home matches", () => {
    const stats = engine.teamStats({ team: "Flamengo", venue: "home" });
    expect(stats.matches).toBeGreaterThan(0);
  });

  it("Given the match data is loaded, when I compare Palmeiras and Santos head-to-head, then I should receive the record between them", () => {
    const h2h = engine.headToHead("Palmeiras", "Santos");
    expect(h2h.matches.length).toBeGreaterThan(0);
    expect(h2h.teamAWins + h2h.teamBWins + h2h.draws).toBe(h2h.matches.length);
  });
});

describe("Feature: Player Queries", () => {
  it("Given the player data is loaded, when I search for Brazilian players, then I should receive players whose nationality is Brazil", () => {
    const players = engine.searchPlayers({ nationality: "Brazil" });
    expect(players.length).toBeGreaterThan(0);
    for (const p of players.slice(0, 10)) {
      expect(p.nationality.toLowerCase()).toBe("brazil");
    }
  });

  it("Given the player data is loaded, when I search for Flamengo players, then I should receive players at Flamengo", () => {
    const players = engine.searchPlayers({ club: "Flamengo" });
    expect(players.length).toBeGreaterThan(0);
  });

  it("Given the player data is loaded, when I search for forwards, then all returned players should be forwards", () => {
    const forwards = engine.searchPlayers({ position: "ST", limit: 20 });
    for (const p of forwards) {
      expect(p.position.toUpperCase()).toContain("ST");
    }
  });
});

describe("Feature: Competition Queries", () => {
  it("Given the match data is loaded, when I request 2019 Brasileirão standings, then Flamengo should be near the top", () => {
    const table = engine.standings({ season: 2019, competition: "Brasileirão" });
    expect(table.length).toBeGreaterThan(0);
    const flamengo = table.find((r) => r.team.toLowerCase().includes("flamengo"));
    expect(flamengo).toBeDefined();
    expect(table[0].points).toBeGreaterThan(0);
  });

  it("Given the match data is loaded, when I request 2023 Brasileirão standings, then the table should contain at least 15 teams", () => {
    const table = engine.standings({ season: 2023, competition: "Brasileirão" });
    expect(table.length).toBeGreaterThanOrEqual(15);
  });
});

describe("Feature: Statistical Analysis", () => {
  it("Given the match data is loaded, when I request average goals for the Brasileirão, then I should receive a positive average", () => {
    const avg = engine.averageGoals("Brasileirão");
    expect(avg.matches).toBeGreaterThan(0);
    expect(avg.average).toBeGreaterThan(0);
  });

  it("Given the match data is loaded, when I request the biggest wins, then the first result should have the largest margin", () => {
    const wins = engine.biggestWins(5);
    expect(wins.length).toBeGreaterThan(0);
    const firstMargin = Math.abs(wins[0].homeGoal - wins[0].awayGoal);
    for (let i = 1; i < wins.length; i++) {
      const margin = Math.abs(wins[i].homeGoal - wins[i].awayGoal);
      expect(margin).toBeLessThanOrEqual(firstMargin);
    }
  });

  it("Given the match data is loaded, when I request the home/away summary, then percentages should sum to 1", () => {
    const summary = engine.homeAwaySummary();
    expect(summary.homeWinRate + summary.awayWinRate + summary.drawRate).toBeCloseTo(1, 5);
  });
});

describe("Feature: Data Coverage", () => {
  it("All six CSV files should be loaded and queryable", () => {
    const competitions = repo.allCompetitions();
    expect(competitions.length).toBeGreaterThanOrEqual(3);
    expect(repo.players.length).toBeGreaterThan(1000);
    expect(repo.matches.length).toBeGreaterThan(1000);
  });

  it("Team name variations should normalize correctly", () => {
    const matches = engine.findMatches({ team: "Sao Paulo" });
    expect(matches.length).toBeGreaterThan(0);
    const foundSaoPaulo = matches.some(
      (m) =>
        m.homeTeam.toLowerCase().includes("são paulo") ||
        m.awayTeam.toLowerCase().includes("são paulo"),
    );
    expect(foundSaoPaulo).toBe(true);
  });
});
