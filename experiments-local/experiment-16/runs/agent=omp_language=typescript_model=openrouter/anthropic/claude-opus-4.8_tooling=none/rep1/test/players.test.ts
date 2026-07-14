/**
 * Context
 * -------
 * BDD scenarios for the Player and Competition capability areas. Player tests
 * cover name/nationality/club/position filtering and Overall-rating sorting over
 * the FIFA dataset; competition tests verify that standings computed from match
 * results reproduce a known historical fact (Flamengo won the 2019 Brasileirão
 * with 90 points) and that the table is internally consistent.
 */

import { describe, it, expect, beforeAll } from "vitest";
import { findPlayers, standings } from "../src/queries.js";
import { normalizeText } from "../src/normalize.js";
import type { DataStore } from "../src/store.js";
import { getStore } from "./fixture.js";

let store: DataStore;
beforeAll(async () => {
  store = await getStore();
});

describe("Feature: Player Queries", () => {
  it("Scenario: find all Brazilian players", () => {
    // When I filter by nationality Brazil
    const br = findPlayers(store, { nationality: "Brazil" });
    // Then I get many players, all Brazilian, sorted by Overall descending
    expect(br.length).toBeGreaterThan(500);
    for (const p of br) expect(p.nationality).toBe("Brazil");
    for (let i = 1; i < br.length; i++) {
      expect(br[i].overall ?? 0).toBeLessThanOrEqual(br[i - 1].overall ?? 0);
    }
    // And the top Brazilian is a world-class rating
    expect(br[0].overall ?? 0).toBeGreaterThanOrEqual(88);
  });

  it("Scenario: search a player by name (partial, accent-insensitive)", () => {
    // When I search for "Neymar"
    const found = findPlayers(store, { name: "neymar" });
    // Then at least one match contains the name
    expect(found.length).toBeGreaterThan(0);
    expect(normalizeText(found[0].name)).toContain("neymar");
  });

  it("Scenario: filter players by position", () => {
    // When I search for goalkeepers
    const gks = findPlayers(store, { position: "GK", nationality: "Brazil" });
    expect(gks.length).toBeGreaterThan(0);
    for (const p of gks) expect(p.position).toBe("GK");
  });

  it("Scenario: filter players by club (Brazilian club)", () => {
    // When I list players at Santos (a club present in the FIFA dataset)
    const santos = findPlayers(store, { club: "Santos" });
    // Then every result's club resolves to Santos and never the unrelated
    // "Santos Laguna" (token-bounded matching, not naive substring)
    expect(santos.length).toBeGreaterThan(0);
    for (const p of santos) {
      expect(normalizeText(p.club)).toContain("santos");
      expect(normalizeText(p.club)).not.toContain("laguna");
    }
  });

  it("Scenario: minOverall threshold filters low-rated players", () => {
    const elite = findPlayers(store, { minOverall: 85 });
    expect(elite.length).toBeGreaterThan(0);
    for (const p of elite) expect(p.overall ?? 0).toBeGreaterThanOrEqual(85);
  });
});

describe("Feature: Competition Queries", () => {
  it("Scenario: 2019 Brasileirão standings reproduce the known champion", () => {
    // When I compute the 2019 Brasileirão table from match results
    const table = standings(store, "Brasileirão", 2019);
    // Then it has 20 teams
    expect(table.length).toBe(20);
    // And Flamengo are champions with 90 points (historical fact)
    expect(normalizeText(table[0].team)).toContain("flamengo");
    expect(table[0].points).toBe(90);
    // And every team played 38 matches
    for (const row of table) expect(row.played).toBe(38);
  });

  it("Scenario: equal-points teams are ordered wins-first (CBF tiebreaker)", () => {
    // 2019: Santos and Palmeiras both finished on 74 points; Santos placed
    // higher on the wins tiebreaker (22W vs 21W).
    const table = standings(store, "Brasileirão", 2019);
    const santos = table.findIndex((r) => normalizeText(r.team).includes("santos"));
    const palmeiras = table.findIndex((r) =>
      normalizeText(r.team).includes("palmeiras"),
    );
    expect(santos).toBeGreaterThanOrEqual(0);
    expect(palmeiras).toBeGreaterThanOrEqual(0);
    expect(table[santos].points).toBe(table[palmeiras].points);
    expect(table[santos].wins).toBeGreaterThan(table[palmeiras].wins);
    expect(santos).toBeLessThan(palmeiras);
  });

  it("Scenario: standings are internally consistent", () => {
    const table = standings(store, "Brasileirão", 2019);
    for (const row of table) {
      // points == 3*wins + draws
      expect(row.points).toBe(row.wins * 3 + row.draws);
      // played == wins + draws + losses
      expect(row.played).toBe(row.wins + row.draws + row.losses);
      // goal diff == GF - GA
      expect(row.goalDiff).toBe(row.goalsFor - row.goalsAgainst);
    }
    // And the table is sorted by points descending
    for (let i = 1; i < table.length; i++) {
      expect(table[i].points).toBeLessThanOrEqual(table[i - 1].points);
    }
  });

  it("Scenario: empty season yields an empty table (no crash)", () => {
    const table = standings(store, "Brasileirão", 1900);
    expect(table).toEqual([]);
  });
});
