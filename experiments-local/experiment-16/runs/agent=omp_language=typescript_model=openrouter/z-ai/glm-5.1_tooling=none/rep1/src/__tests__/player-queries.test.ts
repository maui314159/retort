/**
 * BDD Tests - Player Queries
 *
 * Feature: Player Queries
 * Scenarios for searching FIFA player data by name, nationality,
 * club, and position.
 */

import { describe, it, expect, beforeAll } from "vitest";
import { DataLoader } from "../loader.js";
import { searchPlayers } from "../query.js";
import type { Player } from "../types.js";

let players: Player[];

beforeAll(() => {
  const loader = new DataLoader();
  players = loader.players;
});

describe("Feature: Player Queries", () => {
  describe("Scenario: Search player by name", () => {
    it("Given the player data is loaded, When I search for Neymar, Then I should find at least one player with that name", () => {
      const result = searchPlayers(players, { name: "Neymar" });
      expect(result.length).toBeGreaterThan(0);
      expect(result[0].name.toLowerCase()).toContain("neymar");
    });

    it("When I search for Gabriel Jesus, Then I should find matching players", () => {
      const result = searchPlayers(players, { name: "Gabriel Jesus" });
      expect(result.length).toBeGreaterThan(0);
    });
  });

  describe("Scenario: Filter by nationality", () => {
    it("Given the player data is loaded, When I filter for Brazilian players, Then all results should have nationality Brazil", () => {
      const result = searchPlayers(players, { nationality: "Brazil", limit: 50 });
      expect(result.length).toBeGreaterThan(0);
      for (const p of result) {
        expect(p.nationality.toLowerCase()).toContain("brazil");
      }
    });
  });

  describe("Scenario: Filter by club", () => {
    it("Given the player data is loaded, When I filter for players at Santos, Then all results should play for a club containing Santos", () => {
      const result = searchPlayers(players, { club: "Santos" });
      expect(result.length).toBeGreaterThan(0);
      for (const p of result) {
        expect(p.club.toLowerCase()).toContain("santos");
      }
    });
  });

  describe("Scenario: Filter by position", () => {
    it("Given the player data is loaded, When I filter for goalkeepers, Then all results should be GK", () => {
      const result = searchPlayers(players, { position: "GK", limit: 20 });
      expect(result.length).toBeGreaterThan(0);
      for (const p of result) {
        expect(p.position.toUpperCase()).toContain("GK");
      }
    });
  });

  describe("Scenario: Filter by minimum overall rating", () => {
    it("Given the player data is loaded, When I filter for players with overall >= 85, Then all results should meet that threshold", () => {
      const result = searchPlayers(players, { minOverall: 85 });
      expect(result.length).toBeGreaterThan(0);
      for (const p of result) {
        expect(p.overall).toBeGreaterThanOrEqual(85);
      }
    });
  });

  describe("Scenario: Results sorted by overall rating", () => {
    it("Given the player data is loaded, When I search for Brazilian players, Then results should be sorted by overall descending", () => {
      const result = searchPlayers(players, {
        nationality: "Brazil",
        limit: 20,
      });
      for (let i = 1; i < result.length; i++) {
        expect(result[i - 1].overall).toBeGreaterThanOrEqual(
          result[i].overall
        );
      }
    });
  });

  describe("Scenario: Combine multiple player filters", () => {
    it("Given the player data is loaded, When I search for Brazilian forwards at São Paulo, Then results should match all criteria", () => {
      const result = searchPlayers(players, {
        nationality: "Brazil",
        position: "ST",
        club: "São Paulo",
      });
      for (const p of result) {
        expect(p.nationality.toLowerCase()).toContain("brazil");
        expect(p.position.toUpperCase()).toContain("ST");
        expect(p.club.toLowerCase()).toContain("são paulo");
      }
    });
  });

  describe("Scenario: Player data completeness", () => {
    it("Given the player data is loaded, Then each player should have essential fields populated", () => {
      expect(players.length).toBeGreaterThan(0);
      // Check a sample of players for data completeness
      const sample = players.slice(0, 100);
      for (const p of sample) {
        expect(p.id).toBeGreaterThan(0);
        expect(p.name).toBeTruthy();
        expect(p.overall).toBeGreaterThan(0);
        expect(p.nationality).toBeTruthy();
      }
    });
  });
});
