/**
 * Feature: Match Queries
 *
 * Scenario: Find matches between two teams
 *   Given the match data is loaded
 *   When I search for matches between "Flamengo" and "Fluminense"
 *   Then I should receive a list of matches
 *   And each match should have date, scores, and competition
 */
import { describe, it, expect } from "vitest";
import { getDataset } from "./helpers.js";
import { findMatches, headToHead, resolveTeamOrError } from "../src/lib/queries.js";
import { Competition, Match } from "../src/lib/types.js";

function expectWellFormed(m: Match): void {
  expect(m.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  expect(m.homeTeam.name.length).toBeGreaterThan(0);
  expect(m.awayTeam.name.length).toBeGreaterThan(0);
  expect(m.homeGoals).not.toBeNull();
  expect(m.awayGoals).not.toBeNull();
  expect(Object.values(Competition)).toContain(m.competition);
}

describe("Feature: Match Queries", () => {
  it("Scenario: Find matches between two teams (Fla-Flu derby)", () => {
    // Given the match data is loaded
    const { dataset } = getDataset();
    // When I search for matches between "Flamengo" and "Fluminense"
    const flamengo = resolveTeamOrError(dataset, "Flamengo").team!;
    const fluminense = resolveTeamOrError(dataset, "Fluminense").team!;
    const matches = findMatches(dataset, { team: flamengo, opponent: fluminense });
    // Then I should receive a list of matches
    expect(matches.length).toBeGreaterThan(20);
    // And each match should have date, scores, and competition
    for (const m of matches.slice(0, 25)) expectWellFormed(m);
    // And both teams are involved in every match
    for (const m of matches) {
      const keys = [m.homeTeam.key, m.awayTeam.key];
      expect(keys).toContain(flamengo.key);
      expect(keys).toContain(fluminense.key);
    }
  });

  it("Scenario: Head-to-head aggregate is consistent with the match list", () => {
    const { dataset } = getDataset();
    const flamengo = resolveTeamOrError(dataset, "Flamengo").team!;
    const fluminense = resolveTeamOrError(dataset, "Fluminense").team!;
    const h2h = headToHead(dataset, flamengo, fluminense);
    const played = h2h.matches.filter((m) => m.homeGoals !== null);
    expect(h2h.winsA + h2h.winsB + h2h.draws).toBe(played.length);
    // Flamengo is historically dominant in this derby in the dataset era.
    expect(h2h.winsA).toBeGreaterThan(h2h.winsB);
  });

  it("Scenario: Find matches by team and season (Palmeiras in 2023)", () => {
    const { dataset } = getDataset();
    const palmeiras = resolveTeamOrError(dataset, "Palmeiras").team!;
    const matches = findMatches(dataset, { team: palmeiras, season: 2023, playedOnly: true });
    expect(matches.length).toBeGreaterThan(30);
    for (const m of matches) {
      expect(m.season).toBe(2023);
      expectWellFormed(m);
    }
  });

  it("Scenario: Find matches by competition (all Copa do Brasil finals)", () => {
    const { dataset } = getDataset();
    // Copa do Brasil finals are round "8" in the cup dataset.
    const finals = findMatches(dataset, { competition: Competition.CopaDoBrasil, round: "8", playedOnly: true });
    expect(finals.length).toBeGreaterThanOrEqual(10);
    for (const m of finals) {
      expect(m.competition).toBe(Competition.CopaDoBrasil);
      expectWellFormed(m);
    }
  });

  it("Scenario: Find matches by date range", () => {
    const { dataset } = getDataset();
    const flamengo = resolveTeamOrError(dataset, "Flamengo").team!;
    // Flamengo enters the dataset's 2023 season in April (Copa do Brasil R3).
    const matches = findMatches(dataset, {
      team: flamengo,
      dateFrom: "2023-04-01",
      dateTo: "2023-06-30",
      playedOnly: true,
    });
    expect(matches.length).toBeGreaterThan(5);
    for (const m of matches) {
      expect(m.date! >= "2023-04-01" && m.date! <= "2023-06-30").toBe(true);
    }
  });

  it("Scenario: Venue filter returns only home or only away matches", () => {
    const { dataset } = getDataset();
    const corinthians = resolveTeamOrError(dataset, "Corinthians").team!;
    const home = findMatches(dataset, { team: corinthians, season: 2022, venue: "home", competition: Competition.BrasileiraoSerieA });
    const away = findMatches(dataset, { team: corinthians, season: 2022, venue: "away", competition: Competition.BrasileiraoSerieA });
    expect(home.every((m) => m.homeTeam.key === corinthians.key)).toBe(true);
    expect(away.every((m) => m.awayTeam.key === corinthians.key)).toBe(true);
    // A complete Serie A season is 19 home + 19 away.
    expect(home.length).toBe(19);
    expect(away.length).toBe(19);
  });

  it("Scenario: Team name variations resolve to the same matches", () => {
    const { dataset } = getDataset();
    for (const spelling of ["São Paulo", "Sao Paulo-SP", "sao paulo", "São Paulo FC"]) {
      const res = resolveTeamOrError(dataset, spelling);
      expect(res.error, spelling).toBeUndefined();
      expect(res.team!.key).toBe("sao paulo-sp");
    }
    const athletico = resolveTeamOrError(dataset, "Athletico-PR").team!;
    const atletico = resolveTeamOrError(dataset, "Atletico Paranaense").team!;
    expect(atletico.key).toBe(athletico.key);
  });

  it("Scenario: Ambiguous and unknown teams produce helpful errors", () => {
    const { dataset } = getDataset();
    const ambiguous = resolveTeamOrError(dataset, "Atletico");
    expect(ambiguous.team).toBeUndefined();
    expect(ambiguous.error).toContain("ambiguous");
    const unknown = resolveTeamOrError(dataset, "Wolverhampton Wanderers");
    expect(unknown.error).toContain("Team not found");
  });
});
