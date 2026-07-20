import { beforeAll, describe, expect, it } from "vitest";
import type { KnowledgeGraph } from "../src/knowledgeGraph.js";
import { getGraph } from "../src/knowledgeGraph.js";

/**
 * Feature: Player Queries (spec section 3)
 */
describe("Feature: Player Queries", () => {
  let graph: KnowledgeGraph;

  beforeAll(async () => {
    graph = await getGraph();
  });

  it("Scenario: Find all Brazilian players in the dataset", () => {
    // When I filter players by nationality "Brazil"
    const players = graph.searchPlayers({ nationality: "Brazil", limit: 100 });
    // Then I receive many Brazilian players, highest rated first
    expect(players.length).toBe(100);
    expect(players.every((p) => p.nationality === "Brazil")).toBe(true);
    expect(players[0].overall!).toBeGreaterThanOrEqual(players[99].overall!);
  });

  it("Scenario: Top-rated Brazilian is Neymar", () => {
    const players = graph.searchPlayers({ nationality: "Brazil", limit: 1 });
    expect(players[0].name).toBe("Neymar Jr");
    expect(players[0].overall).toBe(92);
  });

  it("Scenario: Search player by name", () => {
    // When I search for "Gabriel Jesus"
    const players = graph.searchPlayers({ name: "Gabriel Jesus" });
    expect(players.length).toBeGreaterThanOrEqual(1);
    expect(players[0].name).toContain("Gabriel");
  });

  it("Scenario: Filter players by Brazilian club", () => {
    // When I ask who plays for Grêmio
    const players = graph.searchPlayers({ club: "Grêmio", limit: 50 });
    expect(players.length).toBeGreaterThan(5);
    for (const p of players) {
      expect(p.club.toLowerCase()).toContain("grêmio");
    }
  });

  it("Scenario: Filter players by position", () => {
    const players = graph.searchPlayers({ club: "Santos", position: "ST", limit: 50 });
    expect(players.length).toBeGreaterThan(0);
    for (const p of players) {
      expect(p.position.toUpperCase()).toContain("ST");
    }
  });

  it("Scenario: Brazilian players grouped at Brazilian clubs", () => {
    const rows = graph.playersByClubSummary({ nationality: "Brazil", brazilianClubsOnly: true });
    expect(rows.length).toBeGreaterThan(5);
    for (const r of rows) {
      expect(r.players).toBeGreaterThan(0);
      expect(r.avgOverall).toBeGreaterThan(50);
      expect(r.avgOverall).toBeLessThan(95);
    }
  });

  it("Scenario: Minimum overall filter", () => {
    const players = graph.searchPlayers({ minOverall: 90, limit: 50 });
    expect(players.length).toBeGreaterThan(0);
    for (const p of players) expect(p.overall!).toBeGreaterThanOrEqual(90);
  });
});
