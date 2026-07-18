/**
 * BDD Feature: Player Queries
 * -----------------------------------------------------------------------------
 * Covers the spec's "Player Queries" category: search by name, nationality
 * (Brazilian players), club, position, and rating; plus the Brazilian-players-
 * at-Brazilian-clubs grouping (which must NOT misclassify Portuguese clubs
 * sharing a substring like "Vitória" or "Sport").
 */

import { describe, it, expect } from "vitest";
import { dataset } from "./helpers.js";
import { findPlayers, brazilianPlayersAtBrazilianClubs } from "../src/data/query.js";

describe("Feature: Player Queries", () => {
  const ds = dataset();

  describe('Scenario: Who is Gabriel Barbosa?', () => {
    it("finds a player by name substring", () => {
      const players = findPlayers(ds, { name: "Neymar" });
      expect(players.length).toBeGreaterThan(0);
      expect(players[0].name).toContain("Neymar");
      expect(players[0].overall).toBeGreaterThan(85);
    });
  });

  describe("Scenario: Find all Brazilian players", () => {
    it("filters by nationality = Brazil and ranks by overall", () => {
      const players = findPlayers(ds, { nationality: "Brazil", limit: 5 });
      expect(players.length).toBe(5);
      for (const p of players) expect(p.nationality).toBe("Brazil");
      // Ranked descending by overall.
      for (let i = 1; i < players.length; i++) {
        expect(players[i - 1].overall!).toBeGreaterThanOrEqual(players[i].overall!);
      }
    });
  });

  describe("Scenario: Brazilian players at Brazilian clubs", () => {
    it("groups Brazilian players by Brazilian club with counts and avg ratings", () => {
      const groups = brazilianPlayersAtBrazilianClubs(ds);
      expect(groups.length).toBeGreaterThan(0);
      for (const g of groups) {
        expect(g.count).toBeGreaterThan(0);
        expect(g.averageOverall).toBeGreaterThan(0);
      }
    });

    it("does NOT include Portuguese clubs that share a substring", () => {
      const groups = brazilianPlayersAtBrazilianClubs(ds);
      const names = groups.map((g) => g.club);
      // "Vitória Guimarães" and "Sporting CP" must never appear as Brazilian.
      expect(names).not.toContain("Sporting CP");
      expect(names).not.toContain("Vitória Guimarães");
      expect(names).not.toContain("Vitória de Setúbal");
      // The real Brazilian Vitória and Sport Club do appear.
      expect(names).toContain("Vitória");
      expect(names).toContain("Sport Club do Recife");
    });
  });

  describe("Scenario: Filter by minimum overall rating", () => {
    it("returns only players at or above the threshold", () => {
      const players = findPlayers(ds, { nationality: "Brazil", minOverall: 88 });
      expect(players.length).toBeGreaterThan(0);
      for (const p of players) expect(p.overall!).toBeGreaterThanOrEqual(88);
    });
  });
});
