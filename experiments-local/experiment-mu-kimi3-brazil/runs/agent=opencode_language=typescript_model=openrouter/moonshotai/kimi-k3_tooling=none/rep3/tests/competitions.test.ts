/**
 * Feature: Competition Queries
 *
 * Standings calculated from match results, champions, relegation,
 * brackets and season coverage.
 */

import { beforeAll, describe, expect, it } from "vitest";
import { givenDataLoaded } from "./helpers.js";
import type { SoccerQueries } from "../src/queries.js";

let q: SoccerQueries;

beforeAll(() => {
  q = givenDataLoaded().queries;
});

describe("Feature: Competition Queries", () => {
  it("Scenario: Who won the 2019 Brasileirão?", () => {
    // When I calculate the 2019 standings
    const table = q.standings(2019);
    // Then there are 20 teams, each with 38 matches
    expect(table.length).toBe(20);
    for (const row of table) expect(row.matches).toBe(38);
    // And Flamengo is champion with the historically correct 90 points
    expect(table[0].team).toBe("Flamengo");
    expect(table[0].points).toBe(90);
    expect(table[0].wins).toBe(28);
    expect(table[0].draws).toBe(6);
    expect(table[0].losses).toBe(4);
    expect(table[0].note).toContain("Champion");
    // And the podium matches history: Santos 74, Palmeiras 74
    expect(table[1].team).toBe("Santos");
    expect(table[1].points).toBe(74);
    expect(table[2].team).toBe("Palmeiras");
    expect(table[2].points).toBe(74);
  });

  it("Scenario: Which teams were relegated in 2019?", () => {
    // When I look at the bottom of the 2019 table
    const table = q.standings(2019);
    const relegated = table.slice(-4).map((r) => r.team);
    // Then the historically relegated clubs appear (Cruzeiro, CSA, Chapecoense, Avaí)
    expect(relegated).toContain("Cruzeiro");
    expect(relegated).toContain("CSA");
    expect(relegated).toContain("Chapecoense");
    expect(relegated).toContain("Avaí");
    for (const row of table.slice(-4)) expect(row.note).toContain("Relegated");
  });

  it("Scenario: Standings are internally consistent", () => {
    // For any season, total wins must equal total losses,
    // and drawn games must contribute evenly
    const table = q.standings(2018);
    const wins = table.reduce((s, r) => s + r.wins, 0);
    const losses = table.reduce((s, r) => s + r.losses, 0);
    const draws = table.reduce((s, r) => s + r.draws, 0);
    expect(wins).toBe(losses);
    expect(draws % 2).toBe(0);
    // Points = 3W + D for every row
    for (const r of table) expect(r.points).toBe(3 * r.wins + r.draws);
    // Goal difference = GF - GA
    for (const r of table) expect(r.goalDifference).toBe(r.goalsFor - r.goalsAgainst);
  });

  it("Scenario: Older seasons use the right league format", () => {
    // The 2003 Brasileirão had 24 clubs and 46 rounds
    const t2003 = q.standings(2003);
    expect(t2003.length).toBe(24);
    for (const r of t2003) expect(r.matches).toBe(46);
    // Cruzeiro won the 2003 title with 100 points (historical fact)
    expect(t2003[0].team).toBe("Cruzeiro");
    expect(t2003[0].points).toBe(100);
  });

  it("Scenario: 2020 season (COVID-delayed) is assigned correctly", () => {
    // The 2020 Brasileirão ran Aug 2020 - Feb 2021; all 380 matches must
    // count towards season 2020 even when played in early 2021
    const table = q.standings(2020);
    expect(table.length).toBe(20);
    for (const r of table) expect(r.matches).toBe(38);
    // Flamengo won the 2020 title (71 points)
    expect(table[0].team).toBe("Flamengo");
    expect(table[0].points).toBe(71);
  });

  it("Scenario: Show the 2018 Copa Libertadores knockout bracket", () => {
    // When I list 2018 Libertadores knockout stages
    const stages = ["round of 16", "quarterfinals", "semifinals", "final"];
    const bracket = stages.map((stage) => ({
      stage,
      matches: q.findMatches({ competition: "Libertadores", season: 2018, stage, limit: 100 }),
    }));
    // Then every stage has matches and the final is River vs Boca
    for (const b of bracket) expect(b.matches.length).toBeGreaterThan(0);
    const final = bracket[3].matches;
    const keys = final.flatMap((m) => [m.homeTeam.key, m.awayTeam.key]);
    expect(keys).toContain("river-plate");
    expect(keys).toContain("boca-juniors");
  });

  it("Scenario: Competition season coverage is reported", () => {
    const coverage = q.competitionSeasons();
    expect(coverage["Brasileirão Série A"]).toContain(2003);
    expect(coverage["Brasileirão Série A"]).toContain(2023);
    expect(coverage["Copa do Brasil"]).toContain(2012);
    expect(coverage["Copa Libertadores"]).toContain(2013);
    expect(coverage["Brasileirão Série B"].length).toBeGreaterThan(0);
    expect(coverage["Brasileirão Série C"].length).toBeGreaterThan(0);
  });

  it("Scenario: League standings work for Série B too", () => {
    const table = q.standings(2022, "Serie B");
    expect(table.length).toBe(20);
    // Cruzeiro won the 2022 Série B (historical fact)
    expect(table[0].team).toBe("Cruzeiro");
  });
});
