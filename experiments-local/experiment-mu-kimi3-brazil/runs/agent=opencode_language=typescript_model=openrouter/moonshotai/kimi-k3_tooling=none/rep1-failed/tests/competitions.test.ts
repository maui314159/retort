/**
 * Feature: Competition Queries
 *   Standings by season (calculated from match results),
 *   cup finals, season coverage.
 */
import { describe, it, expect } from "vitest";
import type { Dataset } from "../src/types.js";
import { givenDatasetLoaded } from "./helpers.js";
import {
  competitionSeasons,
  findFinals,
  standings,
} from "../src/services/competitions.js";

let ds: Dataset;
givenDatasetLoaded((d) => (ds = d));

describe("Feature: Competition Queries", () => {
  it("Scenario: 2019 Brasileirão standings are calculated correctly", () => {
    // When I calculate the 2019 Brasileirão table
    const table = standings(ds, {
      competition: "Brasileirão Série A",
      season: 2019,
    });
    // Then Flamengo are champions with 90 points (28W 6D 4L)
    expect(table.length).toBe(20);
    expect(table[0].team).toBe("Flamengo");
    expect(table[0].points).toBe(90);
    expect(table[0].wins).toBe(28);
    expect(table[0].draws).toBe(6);
    expect(table[0].losses).toBe(4);
    // And Santos and Palmeiras follow with 74 points each
    expect(table[1].team).toBe("Santos");
    expect(table[1].points).toBe(74);
    expect(table[2].team).toBe("Palmeiras");
    expect(table[2].points).toBe(74);
    // And every team played 38 matches
    for (const row of table) expect(row.played).toBe(38);
  });

  it("Scenario: Standings positions are sequential", () => {
    const table = standings(ds, { competition: "Brasileirão", season: 2018 });
    table.forEach((row, i) => expect(row.position).toBe(i + 1));
  });

  it("Scenario: Relegation zone is the bottom four", () => {
    // When I look at the 2019 table bottom
    const table = standings(ds, { competition: "Brasileirão", season: 2019 });
    const bottom4 = table.slice(-4).map((r) => r.team);
    // Then Cruzeiro is among the relegated (historically true)
    expect(bottom4).toContain("Cruzeiro");
  });

  it("Scenario: Find Copa do Brasil finals", () => {
    // When I search for Copa do Brasil finals
    const finals = findFinals(ds, { competition: "Copa do Brasil" });
    // Then multiple final matches are returned with scores
    expect(finals.length).toBeGreaterThan(5);
    for (const m of finals) {
      expect(m.competition).toBe("Copa do Brasil");
      expect(m.stage).toBe("final");
    }
  });

  it("Scenario: Libertadores finals are found via stage", () => {
    const finals = findFinals(ds, { competition: "Libertadores" });
    expect(finals.length).toBeGreaterThan(3);
    for (const m of finals) expect(m.competition).toBe("Copa Libertadores");
  });

  it("Scenario: Season coverage is reported per competition", () => {
    // When I list Brasileirão seasons
    const seasons = competitionSeasons(ds, "Brasileirão Série A");
    // Then historical and modern seasons are covered
    expect(seasons).toContain(2003);
    expect(seasons).toContain(2023);
  });
});
