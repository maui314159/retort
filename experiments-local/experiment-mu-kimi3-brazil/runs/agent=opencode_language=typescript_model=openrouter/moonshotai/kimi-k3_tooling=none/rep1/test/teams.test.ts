/**
 * Feature: Team Queries
 *
 * Scenario: Get team statistics
 *   Given the match data is loaded
 *   When I request statistics for "Palmeiras" in season "2023"
 *   Then I should receive wins, losses, draws, and goals
 */
import { describe, it, expect } from "vitest";
import { getDataset } from "./helpers.js";
import { findMatches, headToHead, resolveTeamOrError, teamRecord } from "../src/lib/queries.js";
import { Competition } from "../src/lib/types.js";

describe("Feature: Team Queries", () => {
  it("Scenario: Get team statistics (Palmeiras 2023)", () => {
    // Given the match data is loaded
    const { dataset } = getDataset();
    // When I request statistics for "Palmeiras" in season "2023"
    const palmeiras = resolveTeamOrError(dataset, "Palmeiras").team!;
    const matches = findMatches(dataset, { team: palmeiras, season: 2023, playedOnly: true });
    const record = teamRecord(matches, palmeiras);
    // Then I should receive wins, losses, draws, and goals
    expect(record.matches).toBeGreaterThan(30);
    expect(record.wins + record.draws + record.losses).toBe(record.matches);
    expect(record.wins).toBeGreaterThan(15); // Palmeiras finished top-2 in 2023
    expect(record.goalsFor).toBeGreaterThan(record.goalsAgainst);
    expect(record.winRate).toBeGreaterThan(40);
  });

  it("Scenario: Home record (Corinthians 2022 Brasileirão)", () => {
    const { dataset } = getDataset();
    const corinthians = resolveTeamOrError(dataset, "Corinthians").team!;
    const homeMatches = findMatches(dataset, {
      team: corinthians,
      season: 2022,
      competition: Competition.BrasileiraoSerieA,
      venue: "home",
      playedOnly: true,
    });
    const record = teamRecord(homeMatches, corinthians);
    // Complete home season: exactly 19 matches, sums consistent.
    expect(record.matches).toBe(19);
    expect(record.wins + record.draws + record.losses).toBe(19);
    expect(record.goalsFor).toBeGreaterThan(0);
    expect(record.goalsAgainst).toBeGreaterThan(0);
    expect(record.winRate).toBeGreaterThan(0);
    expect(record.winRate).toBeLessThanOrEqual(100);
  });

  it("Scenario: Records differ correctly by venue", () => {
    const { dataset } = getDataset();
    const team = resolveTeamOrError(dataset, "Flamengo").team!;
    const homeRecord = teamRecord(
      findMatches(dataset, { team, season: 2019, competition: Competition.BrasileiraoSerieA, venue: "home", playedOnly: true }),
      team,
    );
    const awayRecord = teamRecord(
      findMatches(dataset, { team, season: 2019, competition: Competition.BrasileiraoSerieA, venue: "away", playedOnly: true }),
      team,
    );
    expect(homeRecord.matches).toBe(19);
    expect(awayRecord.matches).toBe(19);
    // 2019 Flamengo (champion, 90 pts): 28 wins in total.
    expect(homeRecord.wins + awayRecord.wins).toBe(28);
  });

  it("Scenario: Performance by competition", () => {
    const { dataset } = getDataset();
    const palmeiras = resolveTeamOrError(dataset, "Palmeiras").team!;
    const serieA = teamRecord(
      findMatches(dataset, { team: palmeiras, competition: Competition.BrasileiraoSerieA, playedOnly: true }),
      palmeiras,
    );
    const libertadores = teamRecord(
      findMatches(dataset, { team: palmeiras, competition: Competition.Libertadores, playedOnly: true }),
      palmeiras,
    );
    expect(serieA.matches).toBeGreaterThan(300);
    expect(libertadores.matches).toBeGreaterThan(50);
  });

  it("Scenario: Compare teams head-to-head (Palmeiras vs Santos)", () => {
    const { dataset } = getDataset();
    const palmeiras = resolveTeamOrError(dataset, "Palmeiras").team!;
    const santos = resolveTeamOrError(dataset, "Santos").team!;
    const h2h = headToHead(dataset, palmeiras, santos);
    expect(h2h.matches.length).toBeGreaterThan(15);
    expect(h2h.winsA + h2h.winsB + h2h.draws).toBe(
      h2h.matches.filter((m) => m.homeGoals !== null).length,
    );
    expect(h2h.goalsA).toBeGreaterThan(0);
    expect(h2h.goalsB).toBeGreaterThan(0);
  });

  it("Scenario: Which team scored the most goals in Série A 2022", () => {
    const { dataset } = getDataset();
    const matches = findMatches(dataset, { competition: Competition.BrasileiraoSerieA, season: 2022, playedOnly: true });
    const goals = new Map<string, { name: string; goals: number }>();
    for (const m of matches) {
      for (const [t, g] of [[m.homeTeam, m.homeGoals!], [m.awayTeam, m.awayGoals!]] as const) {
        const e = goals.get(t.key) ?? { name: t.name, goals: 0 };
        e.goals += g;
        goals.set(t.key, e);
      }
    }
    const top = [...goals.values()].sort((a, b) => b.goals - a.goals)[0];
    // 2022 top attack: Palmeiras. (The source files record 64 of its 66
    // real-world goals; two postponed-match scores differ between sources.)
    expect(top.name).toBe("Palmeiras");
    expect(top.goals).toBeGreaterThanOrEqual(60);
  });
});
