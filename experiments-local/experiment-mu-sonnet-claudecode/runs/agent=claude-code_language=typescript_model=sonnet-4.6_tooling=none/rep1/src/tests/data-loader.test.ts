import { describe, it, expect } from "vitest";
import {
  loadBrasileiraoMatches,
  loadCupMatches,
  loadLibertadoresMatches,
  loadExtendedMatches,
  loadHistoricalMatches,
  loadFifaPlayers,
  buildNormalizedMatches,
  normalizeTeam,
  teamMatches,
} from "../data-loader.js";

describe("Data loading", () => {
  it("loads Brasileirão matches", () => {
    const matches = loadBrasileiraoMatches();
    expect(matches.length).toBeGreaterThan(100);
    const m = matches[0];
    expect(m).toHaveProperty("datetime");
    expect(m).toHaveProperty("home_team");
    expect(m).toHaveProperty("away_team");
    expect(typeof m.home_goal).toBe("number");
    expect(typeof m.season).toBe("number");
  });

  it("loads Copa do Brasil matches", () => {
    const matches = loadCupMatches();
    expect(matches.length).toBeGreaterThan(100);
    const m = matches[0];
    expect(m).toHaveProperty("round");
    expect(m).toHaveProperty("home_team");
  });

  it("loads Libertadores matches", () => {
    const matches = loadLibertadoresMatches();
    expect(matches.length).toBeGreaterThan(100);
    const m = matches[0];
    expect(m).toHaveProperty("stage");
  });

  it("loads extended match stats", () => {
    const matches = loadExtendedMatches();
    expect(matches.length).toBeGreaterThan(100);
    const m = matches[0];
    expect(m).toHaveProperty("tournament");
    expect(m).toHaveProperty("home_shots");
  });

  it("loads historical Brasileirão matches", () => {
    const matches = loadHistoricalMatches();
    expect(matches.length).toBeGreaterThan(100);
    const m = matches[0];
    expect(m).toHaveProperty("Equipe_mandante");
    expect(m).toHaveProperty("Gols_mandante");
  });

  it("loads FIFA player data", () => {
    const players = loadFifaPlayers();
    expect(players.length).toBeGreaterThan(100);
    const p = players[0];
    expect(p).toHaveProperty("Name");
    expect(p).toHaveProperty("Overall");
    expect(p).toHaveProperty("Nationality");
  });

  it("builds normalized matches from all sources", () => {
    const brasileirao = loadBrasileiraoMatches();
    const cup = loadCupMatches();
    const libertadores = loadLibertadoresMatches();
    const historical = loadHistoricalMatches();
    const normalized = buildNormalizedMatches(brasileirao, cup, libertadores, historical);
    expect(normalized.length).toBeGreaterThan(1000);
    const m = normalized[0];
    expect(m).toHaveProperty("date");
    expect(m).toHaveProperty("competition");
    expect(m).toHaveProperty("home_goal");
  });
});

describe("Team name normalization", () => {
  it("strips state suffix", () => {
    expect(normalizeTeam("Palmeiras-SP")).toBe("palmeiras");
    expect(normalizeTeam("Flamengo-RJ")).toBe("flamengo");
  });

  it("handles accented characters", () => {
    expect(normalizeTeam("Grêmio")).toBe("gremio");
    expect(normalizeTeam("São Paulo")).toBe("sao paulo");
  });

  it("teamMatches handles partial and normalized names", () => {
    expect(teamMatches("Palmeiras", "Palmeiras-SP")).toBe(true);
    expect(teamMatches("Flamengo", "Flamengo-RJ")).toBe(true);
    expect(teamMatches("Flamengo", "Palmeiras-SP")).toBe(false);
  });
});
