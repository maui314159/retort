/**
 * Feature: Player Queries
 *
 * Search the FIFA player database by name, nationality, club and position,
 * including cross-file queries that resolve Brazilian clubs to match teams.
 */
import { describe, it, expect } from "vitest";
import { getDataset } from "./helpers.js";
import { brazilianPlayersByClub, resolveTeamOrError, searchPlayers } from "../src/lib/queries.js";

describe("Feature: Player Queries", () => {
  it("Scenario: Search players by name", () => {
    // Given the player data is loaded
    const { dataset } = getDataset();
    // When I search for "Neymar"
    const results = searchPlayers(dataset, { name: "Neymar", limit: 5 });
    // Then the top result is Neymar Jr with rating and club info
    expect(results[0].name).toBe("Neymar Jr");
    expect(results[0].overall).toBe(92);
    expect(results[0].club).toBe("Paris Saint-Germain");
  });

  it("Scenario: Find all Brazilian players in the dataset", () => {
    const { dataset } = getDataset();
    const results = searchPlayers(dataset, { nationality: "Brazil", limit: 100 });
    expect(results.length).toBe(100); // capped, far more exist
    for (const p of results) {
      expect(p.nationality).toBe("Brazil");
    }
    // Sorted by overall rating, best first.
    expect(results[0].name).toBe("Neymar Jr");
    expect(results[0].overall).toBeGreaterThanOrEqual(results[1].overall!);
    // The dataset holds 827 Brazilian players in total.
    const all = searchPlayers(dataset, { nationality: "Brazil", limit: 1000 });
    expect(all.length).toBe(827);
  });

  it("Scenario: Filter players by club (highest-rated at Grêmio)", () => {
    const { dataset } = getDataset();
    const gremio = resolveTeamOrError(dataset, "Grêmio").team!;
    const results = searchPlayers(dataset, { teamKey: gremio.key, limit: 20 });
    expect(results.length).toBe(20);
    for (const p of results) {
      expect(p.club).toBe("Grêmio");
    }
    // Descending rating order.
    for (let i = 1; i < results.length; i++) {
      expect(results[i - 1].overall!).toBeGreaterThanOrEqual(results[i].overall!);
    }
  });

  it("Scenario: Filter players by position group (Santos forwards)", () => {
    const { dataset } = getDataset();
    const santos = resolveTeamOrError(dataset, "Santos").team!;
    const forwards = searchPlayers(dataset, { teamKey: santos.key, position: "forward", limit: 20 });
    expect(forwards.length).toBeGreaterThan(0);
    const forwardCodes = ["ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"];
    for (const p of forwards) {
      expect(forwardCodes).toContain(p.position);
    }
  });

  it("Scenario: Filter by minimum overall rating", () => {
    const { dataset } = getDataset();
    const elite = searchPlayers(dataset, { minOverall: 90, limit: 50 });
    expect(elite.length).toBeGreaterThan(0);
    for (const p of elite) {
      expect(p.overall!).toBeGreaterThanOrEqual(90);
    }
  });

  it("Scenario: Brazilian players at Brazilian clubs summary", () => {
    const { dataset } = getDataset();
    const rows = brazilianPlayersByClub(dataset);
    expect(rows.length).toBeGreaterThan(10);
    for (const r of rows) {
      expect(r.count).toBeGreaterThan(0);
      expect(r.avgOverall).toBeGreaterThan(50);
      expect(r.avgOverall).toBeLessThan(90);
    }
    const gremio = rows.find((r) => r.team.key === "gremio-rs");
    expect(gremio).toBeDefined();
  });

  it("Scenario: Unknown player returns an empty result, not an error", () => {
    const { dataset } = getDataset();
    // Gabriel Barbosa is not present in this FIFA 19 snapshot.
    expect(searchPlayers(dataset, { name: "Gabriel Barbosa", limit: 5 })).toHaveLength(0);
    expect(searchPlayers(dataset, { name: "Zzzz Nonexistent", limit: 5 })).toHaveLength(0);
  });
});
