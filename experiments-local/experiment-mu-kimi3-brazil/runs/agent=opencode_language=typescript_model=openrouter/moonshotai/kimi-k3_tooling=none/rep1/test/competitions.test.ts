/**
 * Feature: Competition Queries
 *
 * Standings by season calculated from match results, plus cup/Libertadores
 * bracket lookups by stage.
 */
import { describe, it, expect } from "vitest";
import { getDataset } from "./helpers.js";
import { computeStandings, findMatches, resolveCompetition } from "../src/lib/queries.js";
import { Competition } from "../src/lib/types.js";

describe("Feature: Competition Queries", () => {
  it("Scenario: Who won the 2019 Brasileirão (standings from match results)", () => {
    // Given the match data is loaded
    const { dataset } = getDataset();
    // When the 2019 standings are calculated from match results
    const rows = computeStandings(dataset, Competition.BrasileiraoSerieA, 2019);
    // Then Flamengo is champion with 90 points and 28 wins
    expect(rows).toHaveLength(20);
    expect(rows[0].team.name).toBe("Flamengo");
    expect(rows[0].points).toBe(90);
    expect(rows[0].wins).toBe(28);
    // And Santos and Palmeiras follow with 74 points each
    expect(rows[1].team.name).toBe("Santos");
    expect(rows[1].points).toBe(74);
    expect(rows[2].team.name).toBe("Palmeiras");
    expect(rows[2].points).toBe(74);
    // And every team played all 38 rounds
    for (const r of rows) expect(r.played).toBe(38);
    // And the relegation zone matches reality
    expect(rows.slice(-4).map((r) => r.team.name)).toEqual([
      "Cruzeiro",
      "Csa",
      "Chapecoense",
      "Avaí",
    ]);
  });

  it("Scenario: Standings are internally consistent (points = 3W + D)", () => {
    const { dataset } = getDataset();
    for (const season of [2003, 2010, 2018, 2021, 2022]) {
      const rows = computeStandings(dataset, Competition.BrasileiraoSerieA, season);
      expect(rows.length, `season ${season}`).toBeGreaterThanOrEqual(20);
      for (const r of rows) {
        expect(r.points).toBe(3 * r.wins + r.draws);
        expect(r.played).toBe(r.wins + r.draws + r.losses);
        expect(r.goalDifference).toBe(r.goalsFor - r.goalsAgainst);
      }
      // Correct sorting: points, then wins, then GD.
      for (let i = 1; i < rows.length; i++) {
        const a = rows[i - 1], b = rows[i];
        expect(
          a.points > b.points ||
            (a.points === b.points && a.wins > b.wins) ||
            (a.points === b.points && a.wins === b.wins && a.goalDifference >= b.goalDifference),
        ).toBe(true);
      }
    }
  });

  it("Scenario: Champions across eras match football history", () => {
    const { dataset } = getDataset();
    const champions: [number, string, number][] = [
      [2003, "Cruzeiro", 100],
      [2009, "Flamengo", 67],
      [2016, "Palmeiras", 80],
      [2020, "Flamengo", 71],
      [2021, "Atlético Mineiro", 84],
      [2022, "Palmeiras", 81],
    ];
    for (const [season, name, points] of champions) {
      const rows = computeStandings(dataset, Competition.BrasileiraoSerieA, season);
      expect(rows[0].team.name, `champion ${season}`).toBe(name);
      expect(rows[0].points, `points ${season}`).toBe(points);
    }
  });

  it("Scenario: Show the 2018 Copa Libertadores bracket by stage", () => {
    const { dataset } = getDataset();
    const lib2018 = findMatches(dataset, { competition: Competition.Libertadores, season: 2018, playedOnly: true });
    const stages = new Set(lib2018.map((m) => m.round));
    expect(stages).toContain("group stage");
    expect(stages).toContain("round of 16");
    expect(stages).toContain("quarterfinals");
    expect(stages).toContain("semifinals");
    expect(stages).toContain("final");
    // 2018 finalists: River Plate and Boca Juniors.
    const finals = lib2018.filter((m) => m.round === "final");
    const finalists = new Set(finals.flatMap((m) => [m.homeTeam.name, m.awayTeam.name]));
    expect(finalists).toContain("River Plate");
    expect(finalists).toContain("Boca Juniors");
  });

  it("Scenario: Copa Libertadores finals list (Flamengo 2019)", () => {
    const { dataset } = getDataset();
    const finals = findMatches(dataset, { competition: Competition.Libertadores, round: "final", playedOnly: true });
    expect(finals.length).toBeGreaterThanOrEqual(13);
    const f2019 = finals.find((m) => m.season === 2019)!;
    expect(f2019.homeTeam.name).toBe("Flamengo");
    expect(f2019.homeGoals).toBe(2);
    expect(f2019.awayGoals).toBe(1);
    expect(f2019.awayTeam.name).toBe("River Plate");
  });

  it("Scenario: Competition aliases resolve", () => {
    expect(resolveCompetition("brasileirao")).toBe(Competition.BrasileiraoSerieA);
    expect(resolveCompetition("Brasileirão Série A")).toBe(Competition.BrasileiraoSerieA);
    expect(resolveCompetition("serie a")).toBe(Competition.BrasileiraoSerieA);
    expect(resolveCompetition("Serie B")).toBe(Competition.SerieB);
    expect(resolveCompetition("copa do brasil")).toBe(Competition.CopaDoBrasil);
    expect(resolveCompetition("Brazilian Cup")).toBe(Competition.CopaDoBrasil);
    expect(resolveCompetition("Libertadores")).toBe(Competition.Libertadores);
    expect(resolveCompetition("copa libertadores")).toBe(Competition.Libertadores);
    expect(resolveCompetition("champions league")).toBeNull();
  });

  it("Scenario: Série B and Série C standings are available", () => {
    const { dataset } = getDataset();
    const serieB = computeStandings(dataset, Competition.SerieB, 2022);
    expect(serieB.length).toBeGreaterThanOrEqual(20);
    const serieC = computeStandings(dataset, Competition.SerieC, 2022);
    expect(serieC.length).toBeGreaterThanOrEqual(18);
  });
});
