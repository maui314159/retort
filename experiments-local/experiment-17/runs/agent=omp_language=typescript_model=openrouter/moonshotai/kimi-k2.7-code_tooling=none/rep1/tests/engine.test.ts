import { describe, it, expect, beforeAll } from "vitest";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { loadAllData } from "../src/loader.js";
import { SoccerEngine } from "../src/engine.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const dataDir = resolve(__dirname, "../data/kaggle");

describe("SoccerEngine", () => {
  let engine: SoccerEngine;

  beforeAll(async () => {
    const { matches, players } = await loadAllData(dataDir);
    engine = new SoccerEngine(matches, players);
  });

  it("loads all six CSV files with matches and players", () => {
    expect(engine.matches.length).toBeGreaterThan(20000);
    expect(engine.players.length).toBeGreaterThan(18000);
  });

  it("finds matches between Flamengo and Fluminense", () => {
    const matches = engine.findMatchesBetween("Flamengo", "Fluminense", { limit: 5 });
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) {
      const teams = [m.home.toLowerCase(), m.away.toLowerCase()];
      expect(teams).toContain("flamengo");
      expect(teams).toContain("fluminense");
    }
  });

  it("filters Palmeiras matches in 2023", () => {
    const matches = engine.findMatches({ team: "Palmeiras", season: 2023, limit: 100 });
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) {
      expect(m.season).toBe(2023);
      const teams = [m.home.toLowerCase(), m.away.toLowerCase()];
      expect(teams.some((t) => t.includes("palmeiras"))).toBe(true);
    }
  });

  it("calculates team stats for Corinthians", () => {
    const stats = engine.getTeamStats("Corinthians", { season: 2022 });
    expect(stats.matches).toBeGreaterThan(0);
    expect(stats.matches).toBeGreaterThanOrEqual(stats.wins + stats.draws + stats.losses);
    expect(stats.goalsFor).toBeGreaterThanOrEqual(0);
    expect(stats.goalsAgainst).toBeGreaterThanOrEqual(0);
  });

  it("calculates 2019 Brasileirao standings with Flamengo at the top", () => {
    const standings = engine.getStandings(2019, "Brasileirao");
    expect(standings.length).toBeGreaterThan(0);
    expect(standings[0].team).toBe("Flamengo");
    expect(standings[0].points).toBeGreaterThan(0);
  });

  it("finds Brazilian players", () => {
    const players = engine.getPlayers({ nationality: "Brazil", limit: 5 });
    expect(players.length).toBe(5);
    for (const p of players) {
      expect(p.nationality?.toLowerCase()).toBe("brazil");
    }
  });

  it("finds top-rated players at Fluminense", () => {
    const players = engine.getPlayers({ club: "Fluminense", limit: 5 });
    expect(players.length).toBeGreaterThan(0);
    for (const p of players) {
      expect(p.club?.toLowerCase()).toContain("fluminense");
    }
  });

  it("computes average goals and home win rate", () => {
    const stats = engine.getAverageGoals({ competition: "Brasileirao" });
    expect(stats.totalMatches).toBeGreaterThan(0);
    expect(stats.averageGoals).toBeGreaterThan(0);
    expect(stats.homeWinRate).toBeGreaterThan(0);
  });

  it("finds derbies", () => {
    const derbies = engine.getDerbies({ season: 2023, limit: 5 });
    expect(derbies.length).toBeGreaterThan(0);
  });
});
