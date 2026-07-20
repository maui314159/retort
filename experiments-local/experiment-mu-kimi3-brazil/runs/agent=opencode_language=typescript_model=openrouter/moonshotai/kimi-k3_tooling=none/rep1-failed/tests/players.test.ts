/**
 * Feature: Player Queries
 *   Search by name, filter by nationality and club,
 *   inspect ratings and attributes.
 */
import { describe, it, expect } from "vitest";
import type { Dataset } from "../src/types.js";
import { givenDatasetLoaded } from "./helpers.js";
import { playersPerClub, searchPlayers } from "../src/services/players.js";

let ds: Dataset;
givenDatasetLoaded((d) => (ds = d));

describe("Feature: Player Queries", () => {
  it("Scenario: Find all Brazilian players in the dataset", () => {
    // When I filter players by nationality "Brazil"
    const players = searchPlayers(ds, { nationality: "Brazil", limit: 1000 });
    // Then I receive hundreds of Brazilian players
    expect(players.length).toBeGreaterThan(500);
    for (const p of players) expect(p.nationality).toBe("Brazil");
  });

  it("Scenario: Top-rated Brazilian players come first", () => {
    // When I list Brazilian players sorted by rating
    const players = searchPlayers(ds, { nationality: "Brazil", limit: 3 });
    // Then Neymar Jr tops the list (Overall 92 in this dataset)
    expect(players[0].name).toBe("Neymar Jr");
    expect(players[0].overall).toBe(92);
    // And the list is sorted descending
    expect(players[0].overall!).toBeGreaterThanOrEqual(players[1].overall!);
    expect(players[1].overall!).toBeGreaterThanOrEqual(players[2].overall!);
  });

  it("Scenario: Search players by name", () => {
    // When I search for "Gabriel Jesus"
    const players = searchPlayers(ds, { name: "Gabriel Jesus" });
    // Then I find the Manchester City striker
    expect(players.length).toBeGreaterThan(0);
    expect(players[0].name).toContain("Gabriel Jesus");
    expect(players[0].nationality).toBe("Brazil");
    expect(players[0].club?.toLowerCase()).toContain("manchester city");
  });

  it("Scenario: Searching a name absent from the dataset is graceful", () => {
    // When I search for "Gabriel Barbosa" (not in this FIFA edition)
    const players = searchPlayers(ds, { name: "Gabriel Barbosa" });
    // Then I get an empty result, not an error
    expect(players).toEqual([]);
  });

  it("Scenario: Filter players by club", () => {
    // When I filter FIFA data by Club containing "Santos"
    const players = searchPlayers(ds, { club: "Santos", limit: 50 });
    // Then every result plays for a Santos club
    expect(players.length).toBeGreaterThan(0);
    for (const p of players) expect(p.club?.toLowerCase()).toContain("santos");
  });

  it("Scenario: Filter by position group", () => {
    // When I ask for forwards from Santos
    const players = searchPlayers(ds, {
      club: "Santos",
      position: "forward",
      limit: 50,
    });
    // Then only attacking positions are returned
    expect(players.length).toBeGreaterThan(0);
    const fwd = new Set(["ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"]);
    for (const p of players) expect(fwd.has(p.position!)).toBe(true);
  });

  it("Scenario: Filter by minimum rating", () => {
    // When I ask for elite players (85+)
    const players = searchPlayers(ds, { minOverall: 85, limit: 200 });
    expect(players.length).toBeGreaterThan(10);
    for (const p of players) expect(p.overall!).toBeGreaterThanOrEqual(85);
  });

  it("Scenario: Brazilian players grouped per club", () => {
    // When I aggregate Brazilian players per club
    const rows = playersPerClub(ds, { nationality: "Brazil", limit: 20 });
    // Then Brazilian clubs appear with player counts and average ratings
    expect(rows.length).toBeGreaterThan(0);
    const clubs = rows.map((r) => r.club);
    expect(clubs.some((c) => c.includes("Santos") || c.includes("Grêmio"))).toBe(true);
    for (const r of rows) {
      expect(r.players).toBeGreaterThan(0);
      expect(r.avgOverall).toBeGreaterThan(50);
    }
  });
});
