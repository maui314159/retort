import { beforeAll, describe, expect, it } from "vitest";
import type { KnowledgeGraph } from "../src/knowledgeGraph.js";
import { getGraph } from "../src/knowledgeGraph.js";

/**
 * Feature: Match Queries (spec section 1)
 */
describe("Feature: Match Queries", () => {
  let graph: KnowledgeGraph;

  beforeAll(async () => {
    graph = await getGraph();
  });

  it("Scenario: Find matches between two teams", () => {
    // Given the match data is loaded
    // When I search for matches between "Flamengo" and "Fluminense"
    const matches = graph.findMatches({ teamA: "Flamengo", teamB: "Fluminense", limit: 100 });
    // Then I should receive a list of matches
    expect(matches.length).toBeGreaterThan(15);
    // And each match should have date, scores, and competition
    for (const m of matches) {
      expect(m.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(m.homeGoals).not.toBeNull();
      expect(m.awayGoals).not.toBeNull();
      expect(m.competition).toBeTruthy();
    }
  });

  it("Scenario: Matches by team and season", () => {
    // When I ask what matches Palmeiras played in 2023
    const matches = graph.findMatches({ team: "Palmeiras", season: 2023, limit: 200 });
    // Then all returned matches involve Palmeiras in 2023
    expect(matches.length).toBeGreaterThan(30);
    for (const m of matches) {
      expect(m.season).toBe(2023);
      expect(["palmeiras"]).toContainEqual(
        m.homeKey === "palmeiras" ? "palmeiras" : m.awayKey,
      );
    }
  });

  it("Scenario: Matches filtered by competition", () => {
    // When I search Copa do Brasil matches only
    const matches = graph.findMatches({ team: "Flamengo", competition: "Copa do Brasil", limit: 100 });
    expect(matches.length).toBeGreaterThan(10);
    for (const m of matches) {
      expect(m.competition).toBe("Copa do Brasil");
    }
  });

  it("Scenario: Matches filtered by date range", () => {
    const matches = graph.findMatches({
      team: "Corinthians",
      dateFrom: "2023-01-01",
      dateTo: "2023-12-31",
      limit: 200,
    });
    expect(matches.length).toBeGreaterThan(20);
    for (const m of matches) {
      expect(m.date! >= "2023-01-01").toBe(true);
      expect(m.date! <= "2023-12-31").toBe(true);
    }
  });

  it("Scenario: Most recent match between two teams", () => {
    // When I ask when Flamengo last played Corinthians
    const m = graph.lastMatch("Flamengo", "Corinthians");
    // Then I get the latest dated match with a score
    expect(m).not.toBeNull();
    expect(m!.date).toBeTruthy();
    expect(m!.homeGoals).not.toBeNull();
    const keys = [m!.homeKey, m!.awayKey].sort();
    expect(keys).toEqual(["corinthians", "flamengo"]);
  });

  it("Scenario: Find Copa do Brasil finals", () => {
    // The cup file numbers rounds 1-8, where 8 is the two-legged final.
    const cup = graph
      .findMatches({ competition: "Copa do Brasil", limit: 10000 })
      .filter((m) => m.round === "8");
    expect(cup.length).toBeGreaterThan(0);
    for (const m of cup) {
      expect(m.competition).toBe("Copa do Brasil");
      expect(m.date).toBeTruthy();
    }
  });
});
