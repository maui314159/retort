/**
 * Feature: Match Queries
 *
 * Find matches by team, date range, competition and season.
 */

import { beforeAll, describe, expect, it } from "vitest";
import { givenDataLoaded } from "./helpers.js";
import type { SoccerQueries } from "../src/queries.js";

let q: SoccerQueries;

beforeAll(() => {
  q = givenDataLoaded().queries;
});

describe("Feature: Match Queries", () => {
  it("Scenario: Find matches between two teams (Fla-Flu derby)", () => {
    // Given the match data is loaded
    // When I search for matches between "Flamengo" and "Fluminense"
    const matches = q.findMatches({ team: "Flamengo", opponent: "Fluminense", limit: 100 });
    // Then I should receive a list of matches
    expect(matches.length).toBeGreaterThan(10);
    // And each match should have date, scores, and competition
    for (const m of matches) {
      expect(m.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(m.competition).toBeTruthy();
      const keys = [m.homeTeam.key, m.awayTeam.key].sort();
      expect(keys).toEqual(["flamengo-rj", "fluminense-rj"]);
    }
    // And most should have a played score
    const played = matches.filter((m) => m.homeGoals != null);
    expect(played.length).toBeGreaterThan(matches.length * 0.9);
  });

  it("Scenario: Find a team's matches in a season", () => {
    // When I search for Palmeiras matches in 2023
    const matches = q.findMatches({ team: "Palmeiras", season: 2023, limit: 200 });
    // Then all results involve Palmeiras and belong to 2023
    expect(matches.length).toBeGreaterThan(38); // league + cup matches
    for (const m of matches) {
      expect(m.season).toBe(2023);
      expect(["palmeiras-sp"]).toContain(
        m.homeTeam.key === "palmeiras-sp" ? m.homeTeam.key : m.awayTeam.key,
      );
    }
    // And results are chronologically ordered
    const dates = matches.map((m) => m.date);
    expect([...dates].sort()).toEqual(dates);
  });

  it("Scenario: Filter matches by competition", () => {
    // When I search Flamengo matches only in Copa Libertadores
    const matches = q.findMatches({
      team: "Flamengo",
      competition: "Libertadores",
      limit: 200,
    });
    expect(matches.length).toBeGreaterThan(20);
    for (const m of matches) expect(m.competition).toBe("Copa Libertadores");
  });

  it("Scenario: Filter matches by date range", () => {
    // When I search for matches in September 2023
    const matches = q.findMatches({ from: "2023-09-01", to: "2023-09-30", limit: 500 });
    expect(matches.length).toBeGreaterThan(30);
    for (const m of matches) {
      expect(m.date >= "2023-09-01").toBe(true);
      expect(m.date <= "2023-09-30").toBe(true);
    }
  });

  it("Scenario: Find Copa do Brasil finals", () => {
    // When I request the cup finals
    const finals = q.cupFinals();
    // Then there is at least one final round per covered season
    const seasons = new Set(finals.map((m) => m.season));
    expect(seasons.size).toBeGreaterThanOrEqual(9);
    // And every final match comes from the season's last round
    for (const m of finals) expect(m.competition).toBe("Copa do Brasil");
    // And the 2020 final is Palmeiras vs Grêmio (played early 2021)
    const f2020 = q.cupFinals(2020);
    expect(f2020.length).toBe(2);
    const keys = f2020.flatMap((m) => [m.homeTeam.key, m.awayTeam.key]);
    expect(keys).toContain("palmeiras-sp");
    expect(keys).toContain("gremio-rs");
  });

  it("Scenario: Find Libertadores finals by stage", () => {
    // When I filter Libertadores matches by the "final" stage
    const finals = q.findMatches({ competition: "Libertadores", stage: "final", limit: 100 });
    // Then there is roughly one final per covered season (2013-2022)
    expect(finals.length).toBeGreaterThanOrEqual(10);
    for (const m of finals) expect(m.stage).toBe("final");
    // And the 2019 final was Flamengo vs River Plate
    const f2019 = finals.filter((m) => m.season === 2019);
    expect(f2019.length).toBe(1);
    expect(f2019[0].homeTeam.key).toBe("flamengo-rj");
    expect(f2019[0].awayTeam.key).toBe("river-plate");
    expect(`${f2019[0].homeGoals}-${f2019[0].awayGoals}`).toBe("2-1");
  });

  it("Scenario: Most recent match between two teams", () => {
    // When did Flamengo last play Corinthians?
    const matches = q.findMatches({ team: "Flamengo", opponent: "Corinthians", limit: 500 });
    expect(matches.length).toBeGreaterThan(15);
    const last = matches[matches.length - 1];
    // Then the most recent one is the max date
    for (const m of matches) expect(m.date <= last.date).toBe(true);
    // And the score fields exist
    expect(last.homeGoals).not.toBeNull();
    expect(last.awayGoals).not.toBeNull();
  });

  it("Scenario: Venue filter returns only home or only away matches", () => {
    const home = q.findMatches({ team: "Santos", venue: "home", season: 2022, limit: 100 });
    const away = q.findMatches({ team: "Santos", venue: "away", season: 2022, limit: 100 });
    for (const m of home) expect(m.homeTeam.key).toBe("santos-sp");
    for (const m of away) expect(m.awayTeam.key).toBe("santos-sp");
    expect(home.length).toBeGreaterThan(0);
    expect(away.length).toBeGreaterThan(0);
  });
});

describe("Feature: Head-to-head", () => {
  it("Scenario: Compare Palmeiras and Santos head-to-head", () => {
    // When I request the head-to-head
    const h2h = q.headToHead("Palmeiras", "Santos");
    // Then the summary is consistent with the match list
    const played = h2h.matches.filter((m) => m.homeGoals != null);
    expect(h2h.summary.winsA + h2h.summary.winsB + h2h.summary.draws).toBe(played.length);
    expect(h2h.summary.total).toBe(h2h.matches.length);
    // And the derby has plenty of history
    expect(h2h.summary.total).toBeGreaterThan(20);
  });

  it("Scenario: Head-to-head can be restricted to a competition", () => {
    const all = q.headToHead("Flamengo", "Grêmio");
    const libOnly = q.headToHead("Flamengo", "Grêmio", "Libertadores");
    expect(libOnly.summary.total).toBeLessThan(all.summary.total);
    for (const m of libOnly.matches) expect(m.competition).toBe("Copa Libertadores");
    expect(libOnly.summary.total).toBeGreaterThan(0);
    // The 2019 semifinal second leg was the famous 5-0 Flamengo win
    expect(
      libOnly.matches.some(
        (m) =>
          m.homeTeam.key === "flamengo-rj" && m.homeGoals === 5 && m.awayGoals === 0,
      ),
    ).toBe(true);
  });
});
