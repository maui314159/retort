/**
 * brazilian-soccer-mcp — BDD tests for formatters
 *
 * Context block
 * ============
 * See src/types.ts for the top-level project context block.
 *
 * Verifies the human-readable output formats match the shapes specified in
 * TASK.md (match lines, H2H summary, standings, player lists, biggest wins).
 */

import { describe, it, expect } from "vitest";
import * as fmt from "../src/format.js";
import type { MatchRecord, PlayerRecord } from "../src/types.js";

function match(over: Partial<MatchRecord> = {}): MatchRecord {
  return {
    source: "brasileirao",
    competition: "Brasileirão",
    date: "2023-09-03",
    datetime: "2023-09-03",
    homeTeam: "Flamengo",
    awayTeam: "Fluminense",
    homeState: "RJ",
    awayState: "RJ",
    homeGoal: 2,
    awayGoal: 1,
    season: 2023,
    round: "22",
    arena: null,
    ...over,
  };
}

describe("Feature: Match formatting", () => {
  it("Scenario: a match line shows date, score, competition and round", () => {
    const line = fmt.formatMatchLine(match());
    expect(line).toBe("- 2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Round 22)");
  });

  it("Scenario: a match list truncates beyond 20 with a footer", () => {
    const rows = Array.from({ length: 25 }, (_, i) => match({ round: String(i) }));
    const out = fmt.formatMatchList("Derbies", rows);
    expect(out).toContain("Derbies:");
    expect(out).toContain("... (5 more matches in dataset)");
  });
});

describe("Feature: Head-to-head formatting", () => {
  it("Scenario: H2H summary includes wins, draws and a record line", () => {
    const out = fmt.formatHeadToHead({
      teamA: "Flamengo",
      teamB: "Fluminense",
      matches: 2,
      teamAWins: 1,
      teamBWins: 0,
      draws: 1,
      teamAGoals: 3,
      teamBGoals: 2,
      matchesList: [match()],
    });
    expect(out).toContain("Flamengo vs Fluminense");
    expect(out).toContain("Head-to-head in dataset: Flamengo 1 wins, Fluminense 0 wins, 1 draws");
  });
});

describe("Feature: Team stats formatting", () => {
  it("Scenario: team stats show matches, wins, goals, win rate, splits", () => {
    const out = fmt.formatTeamStats(
      {
        team: "Corinthians",
        matches: 19,
        wins: 11,
        draws: 5,
        losses: 3,
        goalsFor: 28,
        goalsAgainst: 15,
        points: 38,
        home: { matches: 10, wins: 8, draws: 1, losses: 1, goalsFor: 18, goalsAgainst: 6, points: 25 },
        away: { matches: 9, wins: 3, draws: 4, losses: 2, goalsFor: 10, goalsAgainst: 9, points: 13 },
      },
      "Corinthians home record (2022 Brasileirão)",
    );
    expect(out).toContain("Corinthians home record (2022 Brasileirão):");
    expect(out).toContain("Matches: 19");
    expect(out).toContain("Wins: 11, Draws: 5, Losses: 3");
    expect(out).toContain("Win rate: 57.9%");
    expect(out).toContain("Home: 10");
    expect(out).toContain("Away: 9");
  });
});

describe("Feature: Standings formatting", () => {
  it("Scenario: standings table has a header and a champion", () => {
    const out = fmt.formatStandings([
      { position: 1, team: "Flamengo", played: 38, wins: 28, draws: 6, losses: 4, goalsFor: 80, goalsAgainst: 30, goalDifference: 50, points: 90 },
      { position: 2, team: "Santos", played: 38, wins: 22, draws: 8, losses: 8, goalsFor: 60, goalsAgainst: 40, goalDifference: 20, points: 74 },
    ]);
    expect(out).toContain("Pos | Team | P | W | D | L | GF | GA | GD | Pts");
    expect(out).toContain("Champion: Flamengo");
    expect(out).toContain("+50");
  });
});

describe("Feature: Player formatting", () => {
  it("Scenario: player list numbers players and shows overall/position/club", () => {
    const players: PlayerRecord[] = [
      { id: 1, name: "Neymar Jr", age: 27, nationality: "Brazil", overall: 92, potential: 93, club: "Paris Saint-Germain", position: "LW", jerseyNumber: 10, height: null, weight: null, preferredFoot: null },
    ];
    const out = fmt.formatPlayerList("Top-rated Brazilian players", players);
    expect(out).toContain("1. Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain");
  });

  it("Scenario: empty player list reports no players", () => {
    expect(fmt.formatPlayerList("Nobody", [])).toContain("(no players found)");
  });
});

describe("Feature: Biggest wins + averages formatting", () => {
  it("Scenario: biggest wins show date, score, competition, diff", () => {
    const out = fmt.formatBiggestWins([match({ homeGoal: 8, awayGoal: 0 })]);
    expect(out).toContain("Biggest victories (provided data):");
    expect(out).toContain("Flamengo 8-0 Fluminense");
    expect(out).toContain("+8");
  });

  it("Scenario: average goals summary shows matches, avg, rates", () => {
    const out = fmt.formatAverageGoals({
      matches: 4000,
      avgGoals: 2.47,
      homeWinRate: 0.473,
      awayWinRate: 0.27,
      drawRate: 0.257,
    });
    expect(out).toContain("Average goals per match: 2.47");
    expect(out).toContain("Home win rate: 47.3%");
  });
});
