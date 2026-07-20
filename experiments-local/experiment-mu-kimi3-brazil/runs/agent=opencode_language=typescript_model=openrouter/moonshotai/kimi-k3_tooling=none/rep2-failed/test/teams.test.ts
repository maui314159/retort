import { beforeAll, describe, expect, it } from "vitest";
import type { KnowledgeGraph } from "../src/knowledgeGraph.js";
import { getGraph } from "../src/knowledgeGraph.js";

/**
 * Feature: Team Queries (spec section 2)
 */
describe("Feature: Team Queries", () => {
  let graph: KnowledgeGraph;

  beforeAll(async () => {
    graph = await getGraph();
  });

  it("Scenario: Get team statistics for a season", () => {
    // Given the match data is loaded
    // When I request statistics for "Palmeiras" in season "2023"
    const rec = graph.teamStats("Palmeiras", { season: 2023 });
    // Then I should receive wins, losses, draws, and goals
    expect(rec.matches).toBeGreaterThan(0);
    expect(rec.wins + rec.draws + rec.losses).toBe(rec.matches);
    expect(rec.goalsFor).toBeGreaterThan(0);
    expect(rec.goalsAgainst).toBeGreaterThanOrEqual(0);
  });

  it("Scenario: Home record scoped to competition", () => {
    // When I ask for Corinthians' home record in the 2022 Brasileirão
    const rec = graph.teamStats("Corinthians", {
      season: 2022,
      competition: "Brasileirão",
      venue: "home",
    });
    // Then I get a consistent home-only record
    expect(rec.matches).toBeGreaterThan(0);
    expect(rec.wins + rec.draws + rec.losses).toBe(rec.matches);
    // And it must be home-only, so matches <= season total
    const all = graph.teamStats("Corinthians", { season: 2022, competition: "Brasileirão" });
    expect(rec.matches).toBeLessThanOrEqual(all.matches);
  });

  it("Scenario: Team with most goals in a season", () => {
    // When I ask which team scored the most goals in Serie A 2019
    const top = graph.topScoringTeams(2019, "Brasileirão", 5);
    // Then I get a ranked list led by a real high scorer
    expect(top.length).toBe(5);
    expect(top[0].goals).toBeGreaterThanOrEqual(top[1].goals);
    // Flamengo scored 86 goals in the real 2019 season
    expect(top[0].team.toLowerCase()).toContain("flamengo");
    expect(top[0].goals).toBeGreaterThanOrEqual(80);
  });

  it("Scenario: Compare two teams head-to-head", () => {
    // When I compare Palmeiras and Santos
    const h2h = graph.headToHead("Palmeiras", "Santos");
    // Then I get matches and a W/D/L summary that adds up
    expect(h2h.total).toBeGreaterThan(20);
    expect(h2h.winsA + h2h.winsB + h2h.draws).toBe(h2h.total);
  });

  it("Scenario: What competitions has a team played in", () => {
    const comps = graph.teamCompetitions("Palmeiras");
    const names = comps.map((c) => c.competition);
    expect(names).toContain("Brasileirão Série A");
    expect(names).toContain("Copa do Brasil");
    expect(names).toContain("Copa Libertadores");
    for (const c of comps) expect(c.matches).toBeGreaterThan(0);
  });
});
