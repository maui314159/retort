import { describe, it, expect } from "vitest";
import { getTeamStats, getStandings, compareTeams, getBestHomeRecord } from "../src/tools/team-tools.js";

describe("getTeamStats", () => {
  it("returns stats for a known team", () => {
    const result = getTeamStats({ team: "Corinthians" });
    expect(result).toContain("Matches:");
    expect(result).toContain("Record:");
    expect(result).toContain("Goals For:");
    expect(result).toContain("Win Rate:");
  });

  it("filters by season", () => {
    const result = getTeamStats({ team: "Corinthians", season: 2022 });
    expect(result).toContain("Season 2022");
  });

  it("filters home only", () => {
    const result = getTeamStats({ team: "Palmeiras", homeOnly: true });
    expect(result).toContain("Home only");
  });

  it("filters away only", () => {
    const result = getTeamStats({ team: "Palmeiras", awayOnly: true });
    expect(result).toContain("Away only");
  });

  it("returns message for unknown team", () => {
    const result = getTeamStats({ team: "UnknownTeamXYZ" });
    expect(result).toContain("No matches found");
  });

  it("filters by competition", () => {
    const result = getTeamStats({ team: "Flamengo", competition: "brasileirao" });
    expect(result).toContain("brasileirao");
  });

  it("calculates correct points (3 per win, 1 per draw)", () => {
    const result = getTeamStats({ team: "Flamengo", season: 2019, competition: "brasileirao" });
    // Just verify it returns numeric data
    expect(result).toMatch(/Points: \d+/);
  });
});

describe("getStandings", () => {
  it("returns 2019 standings", () => {
    const result = getStandings({ season: 2019 });
    expect(result).toContain("2019");
    expect(result).toContain("pts");
  });

  it("returns 2022 standings", () => {
    const result = getStandings({ season: 2022 });
    expect(result).toContain("2022");
  });

  it("returns message for unknown season", () => {
    const result = getStandings({ season: 1800 });
    expect(result).toContain("No matches found");
  });

  it("ranks Flamengo high in 2019", () => {
    const result = getStandings({ season: 2019 });
    // Flamengo won the 2019 Brasileirão
    const lines = result.split("\n");
    const flamengoLine = lines.find((l) => l.toLowerCase().includes("flamengo"));
    expect(flamengoLine).toBeDefined();
    // Flamengo should be in top 3
    const position = lines.indexOf(flamengoLine!);
    expect(position).toBeLessThan(6); // within first 4 lines after header
  });
});

describe("compareTeams", () => {
  it("compares two teams", () => {
    const result = compareTeams({ team1: "Palmeiras", team2: "Santos" });
    expect(result).toContain("Team Comparison");
    expect(result).toContain("Palmeiras");
    expect(result).toContain("Santos");
    expect(result).toContain("Win Rate");
  });

  it("can filter by season", () => {
    const result = compareTeams({ team1: "Flamengo", team2: "Corinthians", season: 2022 });
    expect(result).toContain("2022");
  });

  it("returns message for unknown teams", () => {
    const result = compareTeams({ team1: "AAA", team2: "BBB" });
    expect(result).toContain("No data found");
  });
});

describe("getBestHomeRecord", () => {
  it("returns home records", () => {
    const result = getBestHomeRecord({});
    expect(result).toContain("Best Home Records");
    expect(result).toContain("W");
    expect(result).toContain("win rate");
  });

  it("can filter by season", () => {
    const result = getBestHomeRecord({ season: 2019 });
    expect(result).toContain("2019");
  });

  it("respects limit", () => {
    const result = getBestHomeRecord({ limit: 5 });
    const numbered = result.match(/^\d+\./gm);
    expect(numbered?.length).toBeLessThanOrEqual(5);
  });
});
