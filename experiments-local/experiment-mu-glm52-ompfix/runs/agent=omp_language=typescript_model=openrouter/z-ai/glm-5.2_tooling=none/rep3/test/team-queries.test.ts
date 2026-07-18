/**
 * BDD Feature: Team Queries
 * -----------------------------------------------------------------------------
 * Covers the spec's "Team Queries" + the standings (Competition Queries)
 * category. Verifies win/draw/loss records, goals, points, and that distinct
 * clubs sharing a base name (the Atletico family) are NOT merged.
 *   Given the match data is loaded
 *   When I request statistics for "Palmeiras" in season "2019"
 *   Then I should receive wins, losses, draws, and goals
 */

import { describe, it, expect } from "vitest";
import { dataset } from "./helpers.js";
import { teamStats, standings } from "../src/data/query.js";

describe("Feature: Team Queries", () => {
  const ds = dataset();

  describe("Scenario: Get team statistics for a season", () => {
    it("computes W/D/L and goals for Flamengo in 2019 Brasileirão", () => {
      const st = teamStats(ds, "Flamengo", { competition: "brasileirao", season: 2019 });
      expect(st.played).toBe(38);
      expect(st.wins).toBe(28);
      expect(st.draws).toBe(6);
      expect(st.losses).toBe(4);
      expect(st.points).toBe(90);
      expect(st.goalsFor).toBeGreaterThan(st.goalsAgainst);
      expect(st.winRate).toBeCloseTo(28 / 38, 4);
    });

    it("reports 0 for an out-of-range season without throwing", () => {
      const st = teamStats(ds, "Flamengo", { competition: "brasileirao", season: 1999 });
      expect(st.played).toBe(0);
      expect(st.wins).toBe(0);
    });
  });

  describe("Scenario: Distinct clubs sharing a base name stay separate", () => {
    // Given the Atletico-MG / Atletico-GO / Athletico-PR clubs
    // Then standings must list each as a distinct row
    it("does not merge Atlético-MG, Atlético-GO and Athletico-PR", () => {
      const rows = standings(ds, { competition: "brasileirao", season: 2019 });
      const names = rows.map((r) => r.team);
      const mg = names.find((n) => n === "Atlético-MG");
      const pr = names.find((n) => n === "Athletico-PR");
      expect(mg).toBeDefined();
      expect(pr).toBeDefined();
      // No single "Atletico" row should claim >38 matches (the merge bug).
      const overCount = rows.filter((r) => r.played > 38);
      expect(overCount).toHaveLength(0);
    });
  });

  describe("Scenario: Standings compute a champion from match results", () => {
    it("crowns Flamengo as 2019 Brasileirão champion with 90 points", () => {
      const rows = standings(ds, { competition: "brasileirao", season: 2019 });
      expect(rows[0].team).toBe("Flamengo-RJ");
      expect(rows[0].points).toBe(90);
    });

    it("orders standings by points, then wins, then goal difference", () => {
      const rows = standings(ds, { competition: "brasileirao", season: 2019 });
      for (let i = 1; i < rows.length; i++) {
        const a = rows[i - 1], b = rows[i];
        const ok = a.points > b.points
          || (a.points === b.points && a.wins > b.wins)
          || (a.points === b.points && a.wins === b.wins && a.goalDifference >= b.goalDifference);
        expect(ok).toBe(true);
      }
    });
  });

  describe("Scenario: Historical and modern Brasileirão align team identity", () => {
    it("normalizes a historical no-suffix team to the same key as the modern suffixed form", () => {
      // Historical "Corinthians" (UF=SP) and modern "Corinthians-SP" must key alike.
      const modern = [...ds.matches].find(
        (m) => m.source === "Brasileirao_Matches" && m.homeTeam === "Corinthians-SP",
      );
      const historical = [...ds.matches].find(
        (m) => m.source === "novo_campeonato_brasileiro" && m.homeTeam === "Corinthians-SP",
      );
      expect(modern).toBeDefined();
      expect(historical).toBeDefined();
    });
  });
});
