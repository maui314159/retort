/**
 * Brazilian Soccer MCP Server — BDD player & competition tests
 * -----------------------------------------------------------
 * Context block:
 *   BDD scenarios for Player Queries (FIFA dataset) and Competition Queries
 *   (computed standings). Uses the deterministic fixture dataset.
 */

import { describe, expect, it } from "vitest";
import { buildDataset } from "./fixtures.js";
import { queryPlayers, standings } from "../src/queries.js";

describe("Feature: Player Queries", () => {
  const ds = buildDataset();

  describe("Scenario: Find all Brazilian players", () => {
    it("Given FIFA data, When I filter by nationality Brazil, Then I receive Brazilian players", () => {
      const players = queryPlayers(ds, { nationality: "Brazil" });
      expect(players.length).toBe(6);
      expect(players.every((p) => p.nationality === "Brazil")).toBe(true);
    });
  });

  describe("Scenario: Highest-rated Brazilian players", () => {
    it("returns Brazilian players sorted by overall descending", () => {
      const players = queryPlayers(ds, { nationality: "Brazil", sortBy: "overall", limit: 3 });
      expect(players[0].name).toBe("Neymar Jr");
      expect(players[0].overall).toBe(92);
      expect(players[1].overall).toBe(89);
    });
  });

  describe("Scenario: Players at Flamengo", () => {
    it("filters by club containing Flamengo", () => {
      const players = queryPlayers(ds, { club: "Flamengo", sortBy: "overall" });
      expect(players.length).toBe(2);
      expect(players[0].name).toBe("Gabriel Barbosa");
      expect(players[0].club).toBe("Flamengo");
    });
  });

  describe("Scenario: Find player by name", () => {
    it("matches a substring of the name", () => {
      const players = queryPlayers(ds, { name: "Gabriel" });
      expect(players.length).toBe(1);
      expect(players[0].name).toBe("Gabriel Barbosa");
    });
  });

  describe("Scenario: Forwards with minimum rating", () => {
    it("filters by position and minOverall", () => {
      const players = queryPlayers(ds, { position: "ST", minOverall: 75 });
      expect(players.length).toBe(1);
      expect(players[0].name).toBe("Gabriel Barbosa");
    });
  });
});

describe("Feature: Competition Queries", () => {
  const ds = buildDataset();

  describe("Scenario: 2023 Brasileirão standings", () => {
    it("Given matches, When I request 2023 standings, Then teams are sorted by points", () => {
      const table = standings(ds, { competition: "Brasileirão", season: 2023 });
      expect(table.length).toBe(5);
      // Flamengo: 2 W (Fluminense 2-1, Palmeiras 5-0) = 6 pts.
      expect(table[0].team).toBe("flamengo");
      expect(table[0].points).toBe(6);
      expect(table[0].position).toBe(1);
      // Positions are sequential.
      expect(table.map((r) => r.position)).toEqual([1, 2, 3, 4, 5]);
    });

    it("skips matches with null goals", () => {
      // The Libertadores final has null goals → must not appear in standings.
      const table = standings(ds, { competition: "Libertadores", season: 2024 });
      expect(table.length).toBe(0);
    });

    it("computes goal difference correctly", () => {
      const table = standings(ds, { competition: "Brasileirão", season: 2023 });
      const flamengo = table.find((r) => r.team === "flamengo")!;
      expect(flamengo.goalDifference).toBe(5); // 7 for, 2 against (incl. away loss)
    });
  });
});
