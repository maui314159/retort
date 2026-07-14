/**
 * BDD Tests - Competition Queries
 *
 * Feature: Competition Queries
 * Scenarios for computing standings from match results for
 * Brasileirão, Copa do Brasil, and Libertadores.
 */

import { describe, it, expect, beforeAll } from "vitest";
import { DataLoader } from "../loader.js";
import { getStandings } from "../query.js";
import type { Match } from "../types.js";

let matches: Match[];

beforeAll(() => {
  const loader = new DataLoader();
  matches = loader.matches;
});

describe("Feature: Competition Queries", () => {
  describe("Scenario: Get Brasileirão standings for a season", () => {
    it("Given the match data is loaded, When I request 2019 Brasileirão standings, Then I should get a sorted table of teams", () => {
      const standings = getStandings(matches, "Brasileirão", 2019);
      expect(standings.length).toBeGreaterThan(0);
      expect(standings[0].position).toBe(1);
    });

    it("And Flamengo should be near the top of the 2019 standings", () => {
      const standings = getStandings(matches, "Brasileirão", 2019);
      const flamengo = standings.find((e) =>
        e.team.toLowerCase().includes("flamengo")
      );
      expect(flamengo).toBeDefined();
      expect(flamengo!.position).toBeLessThanOrEqual(3);
    });

    it("And each entry should have points, wins, draws, losses, goals", () => {
      const standings = getStandings(matches, "Brasileirão", 2019);
      for (const entry of standings) {
        expect(entry.points).toBeGreaterThanOrEqual(0);
        expect(entry.wins + entry.draws + entry.losses).toBe(entry.matches);
        expect(entry.goalDifference).toBe(
          entry.goalsFor - entry.goalsAgainst
        );
      }
    });
  });

  describe("Scenario: Standings are sorted correctly", () => {
    it("Given the match data is loaded, When I get standings, Then entries should be sorted by points descending, then goal difference", () => {
      const standings = getStandings(matches, "Brasileirão", 2023);
      for (let i = 1; i < standings.length; i++) {
        const prev = standings[i - 1];
        const curr = standings[i];
        if (prev.points === curr.points) {
          expect(prev.goalDifference).toBeGreaterThanOrEqual(
            curr.goalDifference
          );
        } else {
          expect(prev.points).toBeGreaterThan(curr.points);
        }
      }
    });
  });

  describe("Scenario: Points calculation consistency", () => {
    it("Given the match data is loaded, When I get standings, Then points should equal 3*wins + draws", () => {
      const standings = getStandings(matches, "Brasileirão", 2023);
      for (const entry of standings) {
        expect(entry.points).toBe(entry.wins * 3 + entry.draws);
      }
    });
  });

  describe("Scenario: Standings for Copa do Brasil", () => {
    it("Given the match data is loaded, When I request Copa do Brasil standings, Then I should get results", () => {
      const standings = getStandings(matches, "Copa do Brasil", 2023);
      // Copa do Brasil is knockout, but we can still aggregate
      expect(standings.length).toBeGreaterThan(0);
    });
  });

  describe("Scenario: Standings for Libertadores", () => {
    it("Given the match data is loaded, When I request Libertadores standings, Then I should get results", () => {
      const standings = getStandings(matches, "Libertadores", 2019);
      expect(standings.length).toBeGreaterThan(0);
    });
  });

  describe("Scenario: Non-existent season returns empty", () => {
    it("Given the match data is loaded, When I request standings for a year with no data, Then I should get an empty result", () => {
      const standings = getStandings(matches, "Brasileirão", 1990);
      expect(standings.length).toBe(0);
    });
  });
});
