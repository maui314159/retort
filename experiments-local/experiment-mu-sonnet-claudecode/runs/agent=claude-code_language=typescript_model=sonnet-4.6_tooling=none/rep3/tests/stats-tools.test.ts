import { describe, it, expect } from "vitest";
import { getAggregateStats, getSeasonComparison, getMostGoals } from "../src/tools/stats-tools.js";

describe("getAggregateStats", () => {
  it("returns aggregate statistics", () => {
    const result = getAggregateStats({});
    expect(result).toContain("Total Matches:");
    expect(result).toContain("Average Goals/Match:");
    expect(result).toContain("Home Wins:");
    expect(result).toContain("Away Wins:");
    expect(result).toContain("Draws:");
  });

  it("can filter by competition", () => {
    const result = getAggregateStats({ competition: "brasileirao" });
    expect(result).toContain("Total Matches:");
    expect(result).toContain("brasileirao");
  });

  it("can filter by season", () => {
    const result = getAggregateStats({ season: 2019 });
    expect(result).toContain("Season 2019");
  });

  it("returns no results for unknown criteria", () => {
    const result = getAggregateStats({ season: 1800 });
    expect(result).toContain("No matches found");
  });

  it("calculates avg goals as a reasonable number", () => {
    const result = getAggregateStats({ competition: "brasileirao" });
    const match = result.match(/Average Goals\/Match: ([\d.]+)/);
    expect(match).not.toBeNull();
    const avg = parseFloat(match![1]);
    expect(avg).toBeGreaterThan(1);
    expect(avg).toBeLessThan(6);
  });
});

describe("getSeasonComparison", () => {
  it("compares two seasons", () => {
    const result = getSeasonComparison({ season1: 2018, season2: 2019 });
    expect(result).toContain("2018");
    expect(result).toContain("2019");
    expect(result).toContain("Matches");
    expect(result).toContain("Total Goals");
  });

  it("returns message for unknown seasons", () => {
    const result = getSeasonComparison({ season1: 1800, season2: 1801 });
    expect(result).toContain("No data found");
  });

  it("shows avg goals", () => {
    const result = getSeasonComparison({ season1: 2018, season2: 2019 });
    expect(result).toContain("Avg Goals/Match");
  });
});

describe("getMostGoals", () => {
  it("returns teams with most goals", () => {
    const result = getMostGoals({ season: 2019 });
    expect(result).toContain("Top Goal-Scoring Teams");
    expect(result).toContain("goals");
    expect(result).toContain("1.");
  });

  it("can filter by competition", () => {
    const result = getMostGoals({ competition: "brasileirao", season: 2019 });
    expect(result).toContain("brasileirao");
  });

  it("respects limit", () => {
    const result = getMostGoals({ limit: 5 });
    const numbered = result.match(/^\d+\./gm);
    expect(numbered?.length).toBeLessThanOrEqual(5);
  });

  it("Flamengo high in 2019 goal scorers", () => {
    const result = getMostGoals({ season: 2019 });
    // Flamengo was the top scorer in 2019
    const lines = result.split("\n");
    const top5 = lines.slice(1, 6).map((l) => l.toLowerCase());
    const hasFlamengo = top5.some((l) => l.includes("flamengo"));
    expect(hasFlamengo).toBe(true);
  });
});
