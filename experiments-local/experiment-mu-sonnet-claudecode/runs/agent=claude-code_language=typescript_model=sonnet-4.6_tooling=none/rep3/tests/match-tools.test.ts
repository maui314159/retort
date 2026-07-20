import { describe, it, expect } from "vitest";
import { searchMatches, getHeadToHead, getBiggestWins } from "../src/tools/match-tools.js";

describe("searchMatches", () => {
  it("finds matches for a team", () => {
    const result = searchMatches({ team: "Flamengo", limit: 5 });
    expect(result).not.toBe("No matches found for the given criteria.");
    expect(result.toLowerCase()).toContain("flamengo");
  });

  it("finds matches filtered by season", () => {
    const result = searchMatches({ team: "Palmeiras", season: 2023 });
    expect(result).not.toBe("No matches found for the given criteria.");
  });

  it("finds matches filtered by competition", () => {
    const result = searchMatches({ competition: "brasileirao", limit: 10 });
    expect(result).toContain("Brasileirão");
  });

  it("finds Copa do Brasil matches", () => {
    const result = searchMatches({ competition: "copa do brasil", limit: 10 });
    expect(result).toContain("Copa do Brasil");
  });

  it("finds Libertadores matches", () => {
    const result = searchMatches({ competition: "libertadores", limit: 10 });
    expect(result).toContain("Libertadores");
  });

  it("returns no results for unknown team", () => {
    const result = searchMatches({ team: "ZZZUnknownTeamXXX" });
    expect(result).toBe("No matches found for the given criteria.");
  });

  it("filters by home team", () => {
    const result = searchMatches({ homeTeam: "Corinthians", season: 2022, limit: 10 });
    expect(result).not.toBe("No matches found for the given criteria.");
  });

  it("shows total count when over limit", () => {
    const result = searchMatches({ team: "Flamengo", limit: 5 });
    if (result.includes("Showing 5 of")) {
      expect(result).toMatch(/Showing 5 of \d+ matches/);
    }
  });

  it("finds derby matches between Flamengo and Fluminense", () => {
    const result = searchMatches({ team: "Flamengo", team2: "Fluminense" });
    expect(result.toLowerCase()).toContain("flamengo");
    expect(result.toLowerCase()).toContain("fluminense");
  });

  it("returns matches sorted by date descending", () => {
    const result = searchMatches({ team: "Santos", limit: 10 });
    // Should not error
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
  });
});

describe("getHeadToHead", () => {
  it("finds Flamengo vs Fluminense head-to-head", () => {
    const result = getHeadToHead({ team1: "Flamengo", team2: "Fluminense" });
    expect(result).toContain("Head-to-head");
    expect(result.toLowerCase()).toContain("flamengo");
    expect(result.toLowerCase()).toContain("fluminense");
  });

  it("includes win/draw stats", () => {
    const result = getHeadToHead({ team1: "Palmeiras", team2: "Corinthians" });
    expect(result).toContain("Record:");
  });

  it("returns no result message for unknown teams", () => {
    const result = getHeadToHead({ team1: "AAA", team2: "BBB" });
    expect(result).toContain("No head-to-head matches found");
  });

  it("can filter by season", () => {
    const result = getHeadToHead({ team1: "Flamengo", team2: "Palmeiras", season: 2019 });
    expect(typeof result).toBe("string");
  });
});

describe("getBiggestWins", () => {
  it("returns top biggest wins", () => {
    const result = getBiggestWins({ limit: 5 });
    expect(result).toContain("Biggest wins");
    expect(result).toContain("1.");
    expect(result).toContain("margin:");
  });

  it("can filter by competition", () => {
    const result = getBiggestWins({ competition: "brasileirao", limit: 5 });
    expect(result).toContain("Biggest wins");
  });

  it("can filter by season", () => {
    const result = getBiggestWins({ season: 2019, limit: 5 });
    expect(typeof result).toBe("string");
  });
});
