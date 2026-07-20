import { beforeAll, describe, expect, it } from "vitest";
import type { KnowledgeGraph } from "../src/knowledgeGraph.js";
import { getGraph } from "../src/knowledgeGraph.js";

/**
 * Feature: Competition Queries (spec section 4)
 */
describe("Feature: Competition Queries", () => {
  let graph: KnowledgeGraph;

  beforeAll(async () => {
    graph = await getGraph();
  });

  it("Scenario: 2019 Brasileirão standings are computed correctly", () => {
    // When I ask who won the 2019 Brasileirão
    const rows = graph.standings(2019);
    // Then the table has 20 teams playing 38 rounds
    expect(rows.length).toBe(20);
    expect(rows.every((r) => r.played === 38)).toBe(true);
    // And Flamengo is champion with 90 points (matches official record)
    expect(rows[0].team.toLowerCase()).toContain("flamengo");
    expect(rows[0].points).toBe(90);
    expect(rows[0].wins).toBe(28);
    // And Santos/Palmeiras follow with 74 points each
    expect(rows[1].points).toBe(74);
    expect(rows[2].points).toBe(74);
  });

  it("Scenario: Points are internally consistent", () => {
    const rows = graph.standings(2018);
    for (const r of rows) {
      expect(r.points).toBe(r.wins * 3 + r.draws);
      expect(r.played).toBe(r.wins + r.draws + r.losses);
      expect(r.goalDifference).toBe(r.goalsFor - r.goalsAgainst);
    }
  });

  it("Scenario: Historical champion 2003 season", () => {
    const rows = graph.standings(2003);
    expect(rows.length).toBeGreaterThan(20);
    // Cruzeiro won the 2003 Brasileirão
    expect(rows[0].team.toLowerCase()).toContain("cruzeiro");
  });

  it("Scenario: Relegation zone belongs to the table bottom", () => {
    const rows = graph.standings(2019);
    const bottom4 = rows.slice(-4);
    expect(bottom4.length).toBe(4);
    for (const r of bottom4) {
      expect(r.points).toBeLessThan(rows[0].points);
    }
  });

  it("Scenario: Libertadores data is available by stage", () => {
    const matches = graph.findMatches({ competition: "Libertadores", season: 2019, limit: 500 });
    expect(matches.length).toBeGreaterThan(50);
    const stages = new Set(matches.map((m) => m.stage).filter(Boolean));
    expect(stages.size).toBeGreaterThan(1);
  });
});
