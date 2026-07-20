/**
 * Feature: Statistical Analysis
 *
 * Aggregated statistics: goal averages, home/away performance,
 * biggest wins, dataset coverage and cross-file consistency.
 */

import { beforeAll, describe, expect, it } from "vitest";
import { givenDataLoaded } from "./helpers.js";
import type { SoccerQueries } from "../src/queries.js";
import type { AppContext } from "../src/context.js";

let q: SoccerQueries;
let ctx: AppContext;

beforeAll(() => {
  ctx = givenDataLoaded();
  q = ctx.queries;
});

describe("Feature: Statistical Analysis", () => {
  it("Scenario: Average goals per match in the Brasileirão", () => {
    // When I request aggregate stats for the Brasileirão Série A
    const stats = q.competitionStats({ competition: "Brasileirão Série A" });
    // Then the average is in the historically typical 2.2-2.9 band
    expect(stats.averageGoalsPerMatch).toBeGreaterThan(2.0);
    expect(stats.averageGoalsPerMatch).toBeLessThan(3.0);
    // And the W/D/L counts add up
    expect(stats.homeWins + stats.draws + stats.awayWins).toBe(stats.matchesPlayed);
    expect(stats.homeWinRate + stats.drawRate + stats.awayWinRate).toBeCloseTo(100, 0);
  });

  it("Scenario: Home advantage exists", () => {
    const stats = q.competitionStats({ competition: "Brasileirão Série A" });
    // Home win rate exceeds away win rate (classic home advantage)
    expect(stats.homeWinRate).toBeGreaterThan(stats.awayWinRate);
    expect(stats.homeWinRate).toBeGreaterThan(40);
  });

  it("Scenario: Stats can be computed per season", () => {
    const s2023 = q.competitionStats({ competition: "Serie A", season: 2023 });
    // The 2023 season is nearly complete in the data (377 of 380 matches)
    expect(s2023.matchesPlayed).toBeGreaterThanOrEqual(375);
    const s2019 = q.competitionStats({ competition: "Serie A", season: 2019 });
    expect(s2019.matchesPlayed).toBe(380);
  });

  it("Scenario: Show me the biggest wins in the dataset", () => {
    // When I request the biggest victories
    const wins = q.biggestWins({ limit: 10 });
    // Then they are sorted by goal margin
    const margins = wins.map((m) => Math.abs(m.homeGoals! - m.awayGoals!));
    for (let i = 1; i < margins.length; i++) {
      expect(margins[i - 1]).toBeGreaterThanOrEqual(margins[i]);
    }
    // And the top margin is at least 8 goals
    expect(margins[0]).toBeGreaterThanOrEqual(8);
  });

  it("Scenario: Biggest wins can be filtered by competition", () => {
    const wins = q.biggestWins({ competition: "Brasileirão Série A", limit: 10 });
    for (const m of wins) expect(m.competition).toBe("Brasileirão Série A");
    expect(wins.length).toBe(10);
  });

  it("Scenario: Which team has the best away record?", () => {
    const best = q.bestAwayRecords({ season: 2023, competition: "Serie A", limit: 3, minMatches: 15 });
    expect(best.length).toBeGreaterThan(0);
    for (let i = 1; i < best.length; i++) {
      expect(best[i - 1].winRate).toBeGreaterThanOrEqual(best[i].winRate);
    }
  });

  it("Scenario: Head-to-head totals equal the sum of outcomes", () => {
    const h2h = q.headToHead("Flamengo", "Fluminense");
    const played = h2h.matches.filter((m) => m.homeGoals != null).length;
    expect(h2h.summary.winsA + h2h.summary.winsB + h2h.summary.draws).toBe(played);
    // Goals must be consistent with the match list
    let goalsA = 0, goalsB = 0;
    for (const m of h2h.matches) {
      if (m.homeGoals == null) continue;
      const aHome = m.homeTeam.key === "flamengo-rj";
      goalsA += aHome ? m.homeGoals : m.awayGoals!;
      goalsB += aHome ? m.awayGoals! : m.homeGoals;
    }
    expect(h2h.summary.goalsA).toBe(goalsA);
    expect(h2h.summary.goalsB).toBe(goalsB);
  });
});

describe("Feature: Data coverage and quality", () => {
  it("Scenario: All 6 CSV files are loadable and queryable", () => {
    const ov = q.overview(ctx.dataset.sourceRowCounts, ctx.dataset.duplicateCounts);
    // All six files contributed rows
    expect(ov.sources["Brasileirao_Matches.csv"]).toBe(4180);
    expect(ov.sources["Brazilian_Cup_Matches.csv"]).toBe(1337);
    expect(ov.sources["Libertadores_Matches.csv"]).toBe(1255);
    expect(ov.sources["novo_campeonato_brasileiro.csv"]).toBe(6886);
    expect(ov.sources["BR-Football-Dataset.csv"]).toBe(10296);
    expect(ov.sources["fifa_data.csv"]).toBe(18207);
    // And the unified store is non-trivial
    expect(ov.uniqueMatches).toBeGreaterThan(16000);
    expect(ov.players).toBe(18207);
    expect(ov.teams).toBeGreaterThan(300);
  });

  it("Scenario: Cross-source deduplication produces complete league seasons", () => {
    // Every Brasileirão Série A season 2003-2022 has the full match count
    const expected: Record<number, number> = {
      2003: 552, 2004: 552, 2005: 462,
      2006: 380, 2007: 380, 2008: 380, 2009: 380, 2010: 380, 2011: 380,
      2012: 380, 2013: 380, 2014: 380, 2015: 380, 2016: 380, 2017: 380,
      2018: 380, 2019: 380, 2020: 380, 2021: 380, 2022: 380,
    };
    for (const [season, count] of Object.entries(expected)) {
      const matches = ctx.dataset.matches.filter(
        (m) => m.competition === "Brasileirão Série A" && m.season === Number(season),
      );
      expect(matches.length, `season ${season}`).toBe(count);
    }
  });

  it("Scenario: No fixture is double-counted", () => {
    // Within any league season, a (home, away) pairing occurs at most once
    // per team per season for Série A 2006+ (round-robin)
    const s2019 = ctx.dataset.matches.filter(
      (m) => m.competition === "Brasileirão Série A" && m.season === 2019,
    );
    const seen = new Set<string>();
    for (const m of s2019) {
      const k = `${m.homeTeam.key}|${m.awayTeam.key}`;
      expect(seen.has(k), `duplicate fixture ${k}`).toBe(false);
      seen.add(k);
    }
  });

  it("Scenario: Cross-file queries work (player club -> match data)", () => {
    // Players at Santos (FIFA data) and Santos matches (match data)
    // must share the same canonical team key
    const santosPlayers = q.searchPlayers({ club: "Santos", limit: 5 });
    expect(santosPlayers.length).toBeGreaterThan(0);
    expect(santosPlayers[0].clubKey).toBe("santos-sp");
    const santosMatches = q.findMatches({ team: "Santos", limit: 5 });
    expect(santosMatches.length).toBeGreaterThan(0);
    expect(
      santosMatches.some(
        (m) => m.homeTeam.key === "santos-sp" || m.awayTeam.key === "santos-sp",
      ),
    ).toBe(true);
  });
});

describe("Feature: Query performance", () => {
  it("Scenario: Simple lookups respond in well under 2 seconds", () => {
    const t0 = performance.now();
    for (let i = 0; i < 50; i++) q.findMatches({ team: "Flamengo", opponent: "Fluminense" });
    const dt = (performance.now() - t0) / 50;
    expect(dt).toBeLessThan(100); // ms per lookup, 20x headroom
  });

  it("Scenario: Aggregate queries respond in well under 5 seconds", () => {
    const t0 = performance.now();
    q.standings(2019);
    q.competitionStats({});
    q.biggestWins({ limit: 100 });
    const dt = performance.now() - t0;
    expect(dt).toBeLessThan(2000); // 2.5x headroom
  });
});
