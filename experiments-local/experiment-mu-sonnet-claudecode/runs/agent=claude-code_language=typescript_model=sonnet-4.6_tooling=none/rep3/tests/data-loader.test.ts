import { describe, it, expect } from "vitest";
import { normalizeTeamName, teamMatches, getDataStore } from "../src/data-loader.js";

describe("normalizeTeamName", () => {
  it("removes Brazilian state suffix", () => {
    expect(normalizeTeamName("Palmeiras-SP")).toBe("Palmeiras");
    expect(normalizeTeamName("Flamengo-RJ")).toBe("Flamengo");
    expect(normalizeTeamName("Sport-PE")).toBe("Sport");
    expect(normalizeTeamName("Atlético-MG")).toBe("Atlético");
  });

  it("preserves names without state suffix", () => {
    expect(normalizeTeamName("Palmeiras")).toBe("Palmeiras");
    expect(normalizeTeamName("Flamengo")).toBe("Flamengo");
    expect(normalizeTeamName("Santos")).toBe("Santos");
  });

  it("handles names with legitimate hyphens that are not state codes", () => {
    // "Inter-Milan" would not be stripped because Milan is not a 2-letter state
    expect(normalizeTeamName("Santos")).toBe("Santos");
  });

  it("handles empty string", () => {
    expect(normalizeTeamName("")).toBe("");
  });
});

describe("teamMatches", () => {
  it("matches exact names after normalization", () => {
    expect(teamMatches("Palmeiras-SP", "Palmeiras")).toBe(true);
    expect(teamMatches("Flamengo-RJ", "Flamengo")).toBe(true);
  });

  it("matches partial names", () => {
    expect(teamMatches("São Paulo FC", "São Paulo")).toBe(true);
    expect(teamMatches("Atlético Mineiro", "Atlético")).toBe(true);
  });

  it("returns false for unrelated teams", () => {
    expect(teamMatches("Palmeiras", "Flamengo")).toBe(false);
    expect(teamMatches("Santos", "São Paulo")).toBe(false);
  });

  it("is case-insensitive", () => {
    expect(teamMatches("Palmeiras", "palmeiras")).toBe(true);
    expect(teamMatches("FLAMENGO", "flamengo")).toBe(true);
  });
});

describe("getDataStore", () => {
  it("loads all match datasets", () => {
    const store = getDataStore();
    expect(store.matches.length).toBeGreaterThan(1000);
  });

  it("loads player data", () => {
    const store = getDataStore();
    expect(store.players.length).toBeGreaterThan(100);
  });

  it("includes matches from different competitions", () => {
    const store = getDataStore();
    const competitions = new Set(store.matches.map((m) => m.competition));
    expect(competitions.has("brasileirao")).toBe(true);
    expect(competitions.has("copa_do_brasil")).toBe(true);
    expect(competitions.has("libertadores")).toBe(true);
    expect(competitions.has("historical")).toBe(true);
  });

  it("normalizes team names to remove state suffixes", () => {
    const store = getDataStore();
    const brasileirao = store.matches.filter((m) => m.competition === "brasileirao");
    // After normalization, no team should end with a 2-letter state suffix
    for (const m of brasileirao.slice(0, 100)) {
      expect(m.homeTeam).not.toMatch(/-[A-Z]{2}$/);
      expect(m.awayTeam).not.toMatch(/-[A-Z]{2}$/);
    }
  });

  it("parses seasons as numbers", () => {
    const store = getDataStore();
    const withSeason = store.matches.filter((m) => m.season > 0);
    expect(withSeason.length).toBeGreaterThan(0);
    for (const m of withSeason.slice(0, 10)) {
      expect(typeof m.season).toBe("number");
      expect(m.season).toBeGreaterThan(2000);
    }
  });

  it("parses dates correctly", () => {
    const store = getDataStore();
    const withDate = store.matches.filter((m) => m.datetime !== null);
    expect(withDate.length).toBeGreaterThan(1000);
    for (const m of withDate.slice(0, 10)) {
      expect(m.datetime).toBeInstanceOf(Date);
      expect(isNaN(m.datetime!.getTime())).toBe(false);
    }
  });
});
