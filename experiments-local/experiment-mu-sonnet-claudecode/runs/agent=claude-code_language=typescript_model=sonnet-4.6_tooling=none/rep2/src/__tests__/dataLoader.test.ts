import { describe, it, expect, beforeAll } from "vitest";
import { loadAllMatches, loadFifaPlayers, normalizeTeamName, teamsMatch, clearCache } from "../dataLoader.js";
import type { NormalizedMatch, FifaPlayer } from "../types.js";

describe("Data Loader", () => {
  beforeAll(() => {
    clearCache();
  });

  describe("normalizeTeamName", () => {
    it("strips state suffix from team names", () => {
      expect(normalizeTeamName("Palmeiras-SP")).toBe("palmeiras");
      expect(normalizeTeamName("Flamengo-RJ")).toBe("flamengo");
    });

    it("handles names without suffix", () => {
      expect(normalizeTeamName("Palmeiras")).toBe("palmeiras");
    });

    it("strips parenthetical notes", () => {
      expect(
        normalizeTeamName("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ")
      ).toBe("boavista sport club");
    });

    it("normalizes accented characters", () => {
      expect(normalizeTeamName("Grêmio")).toBe("gremio");
      expect(normalizeTeamName("São Paulo")).toBe("sao paulo");
    });
  });

  describe("teamsMatch", () => {
    it("matches team with and without state suffix", () => {
      expect(teamsMatch("Palmeiras-SP", "Palmeiras")).toBe(true);
    });

    it("matches same team regardless of case/accents", () => {
      expect(teamsMatch("Grêmio", "Gremio")).toBe(true);
    });

    it("does not match different teams", () => {
      expect(teamsMatch("Flamengo", "Fluminense")).toBe(false);
    });
  });

  describe("loadAllMatches", () => {
    let matches: NormalizedMatch[];

    beforeAll(() => {
      matches = loadAllMatches();
    });

    it("loads a large number of matches", () => {
      expect(matches.length).toBeGreaterThan(10000);
    });

    it("every match has required fields", () => {
      for (const m of matches.slice(0, 100)) {
        expect(m).toHaveProperty("home_team");
        expect(m).toHaveProperty("away_team");
        expect(m).toHaveProperty("home_goal");
        expect(m).toHaveProperty("away_goal");
        expect(m).toHaveProperty("competition");
        expect(m).toHaveProperty("season");
        expect(typeof m.home_goal).toBe("number");
        expect(typeof m.away_goal).toBe("number");
      }
    });

    it("includes all competitions", () => {
      const competitions = new Set(matches.map((m) => m.competition));
      expect(competitions.has("Brasileirao")).toBe(true);
      expect(competitions.has("Copa do Brasil")).toBe(true);
      expect(competitions.has("Libertadores")).toBe(true);
    });

    it("returns cached results on second call", () => {
      const second = loadAllMatches();
      expect(second).toBe(matches); // same reference due to caching
    });
  });

  describe("loadFifaPlayers", () => {
    let players: FifaPlayer[];

    beforeAll(() => {
      players = loadFifaPlayers();
    });

    it("loads a large number of players", () => {
      expect(players.length).toBeGreaterThan(1000);
    });

    it("every player has required fields", () => {
      for (const p of players.slice(0, 50)) {
        expect(p).toHaveProperty("name");
        expect(p).toHaveProperty("overall");
        expect(p).toHaveProperty("club");
        expect(p).toHaveProperty("nationality");
        expect(typeof p.overall).toBe("number");
      }
    });

    it("contains Brazilian players", () => {
      const brazilians = players.filter((p) =>
        p.nationality.toLowerCase().includes("brazil")
      );
      expect(brazilians.length).toBeGreaterThan(100);
    });
  });
});
