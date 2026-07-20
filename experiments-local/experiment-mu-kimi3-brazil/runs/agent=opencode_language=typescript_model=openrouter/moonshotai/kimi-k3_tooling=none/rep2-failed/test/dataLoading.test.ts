import { beforeAll, describe, expect, it } from "vitest";
import type { KnowledgeGraph } from "../src/knowledgeGraph.js";
import { getGraph } from "../src/knowledgeGraph.js";

/**
 * BDD scenarios for the shared fixture: all six CSV files load and the
 * graph indexes them.
 */
describe("Feature: Data loading", () => {
  let graph: KnowledgeGraph;

  beforeAll(async () => {
    graph = await getGraph();
  });

  it("Scenario: All 6 CSV files are loadable and queryable", () => {
    // Given the datasets on disk
    // When the graph loads
    // Then all six sources contribute matches/players
    const sources = new Set(graph.matches.map((m) => m.source));
    expect(sources).toContain("Brasileirao_Matches.csv");
    expect(sources).toContain("Brazilian_Cup_Matches.csv");
    expect(sources).toContain("Libertadores_Matches.csv");
    expect(sources).toContain("BR-Football-Dataset.csv");
    expect(sources).toContain("novo_campeonato_brasileiro.csv");
    expect(graph.players.length).toBeGreaterThan(18000);
    expect(graph.matches.length).toBeGreaterThan(15000);
  });

  it("Scenario: Competitions are recognized", () => {
    const comps = graph.competitions();
    expect(comps).toContain("Brasileirão Série A");
    expect(comps).toContain("Copa do Brasil");
    expect(comps).toContain("Copa Libertadores");
  });
});
