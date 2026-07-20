import { beforeAll, describe, expect, it } from "vitest";
import type { KnowledgeGraph } from "../src/knowledgeGraph.js";
import { getGraph } from "../src/knowledgeGraph.js";

/**
 * Feature: Statistical Analysis (spec section 5)
 */
describe("Feature: Statistical Analysis", () => {
  let graph: KnowledgeGraph;

  beforeAll(async () => {
    graph = await getGraph();
  });

  it("Scenario: Average goals per match is realistic", () => {
    // When I ask for the average goals per match in the Brasileirão
    const s = graph.goalsStats({ competition: "Brasileirão" });
    // Then the average is in the historical 2-3 range
    expect(s.avgGoalsPerMatch).toBeGreaterThan(2);
    expect(s.avgGoalsPerMatch).toBeLessThan(3);
    expect(s.matches).toBeGreaterThan(10000);
  });

  it("Scenario: Home advantage exists", () => {
    const s = graph.goalsStats({ competition: "Brasileirão" });
    expect(s.homeWinRate).toBeGreaterThan(s.awayWinRate);
    expect(s.homeWinRate).toBeGreaterThan(0.4);
    expect(s.homeWinRate + s.awayWinRate + s.drawRate).toBeCloseTo(1, 5);
  });

  it("Scenario: Biggest wins are sorted by margin", () => {
    const wins = graph.biggestWins({}, 10);
    expect(wins.length).toBe(10);
    for (let i = 1; i < wins.length; i++) {
      const prev = Math.abs(wins[i - 1].homeGoals! - wins[i - 1].awayGoals!);
      const cur = Math.abs(wins[i].homeGoals! - wins[i].awayGoals!);
      expect(prev).toBeGreaterThanOrEqual(cur);
    }
    // The largest margin in the data is 9-1 or better
    const top = wins[0];
    expect(Math.abs(top.homeGoals! - top.awayGoals!)).toBeGreaterThanOrEqual(8);
  });

  it("Scenario: Biggest wins scoped to a competition", () => {
    const wins = graph.biggestWins({ competition: "Brasileirão" }, 5);
    for (const w of wins) {
      expect(w.competition).toContain("Brasileirão");
    }
  });

  it("Scenario: Compare two seasons via aggregate stats", () => {
    const s2018 = graph.goalsStats({ competition: "Brasileirão Série A", season: 2018 });
    const s2019 = graph.goalsStats({ competition: "Brasileirão Série A", season: 2019 });
    // Full seasons of 380 matches each
    expect(s2018.matches).toBe(380);
    expect(s2019.matches).toBe(380);
    expect(s2018.avgGoalsPerMatch).toBeGreaterThan(1.5);
    expect(s2019.avgGoalsPerMatch).toBeGreaterThan(1.5);
  });

  it("Scenario: Team-scoped stats", () => {
    const s = graph.goalsStats({ team: "Flamengo", season: 2019, competition: "Brasileirão Série A" });
    expect(s.matches).toBe(38);
    expect(s.totalGoals).toBeGreaterThan(0);
  });
});
