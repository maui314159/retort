/**
 * Context
 * -------
 * BDD (Given/When/Then) scenarios for the query engine (src/queries.ts) run
 * against the REAL Kaggle datasets in data/kaggle/. These assert the behaviors
 * the spec calls out, using values cross-checked against the source files:
 *   - 2019 Brasileirão Série A: Flamengo champions on 90 pts (28W-6D-4L)
 *   - cross-file fixtures are deduplicated (20-team season => 380 matches)
 *   - distinct same-base clubs (Atlético-MG vs Athletico-PR) stay separate
 *   - head-to-head, player search, and aggregate stats behave sensibly
 *
 * The dataset is loaded once and shared across the suite for speed.
 */

import { beforeAll, describe, it, expect } from "vitest";
import { loadSoccerData } from "../src/loader.js";
import { SoccerKnowledgeBase } from "../src/queries.js";
import type { SoccerData } from "../src/types.js";

let data: SoccerData;
let kb: SoccerKnowledgeBase;

beforeAll(() => {
  data = loadSoccerData();
  kb = new SoccerKnowledgeBase(data);
});

describe("Feature: data loading", () => {
  describe("Scenario: all six datasets are loaded", () => {
    it("Given the CSV files, When loaded, Then matches and players are present", () => {
      // Given the dataset directory
      // When the knowledge base is built
      // Then it holds a substantial number of matches and the FIFA players
      expect(kb.matchCount).toBeGreaterThan(10_000);
      expect(kb.playerCount).toBe(18_207);
    });

    it("Given multiple competitions, When listed, Then all are represented", () => {
      // Then each competition reports at least one season
      expect(kb.seasonsFor("Brasileirão Série A").length).toBeGreaterThan(0);
      expect(kb.seasonsFor("Copa do Brasil").length).toBeGreaterThan(0);
      expect(kb.seasonsFor("Copa Libertadores").length).toBeGreaterThan(0);
    });
  });
});

describe("Feature: match queries", () => {
  describe("Scenario: find matches between two teams", () => {
    it("Given match data, When searching Flamengo vs Fluminense, Then fixtures with scores are returned", () => {
      // Given the loaded match data
      // When I search for matches between the two clubs
      const matches = kb.findMatches({ team: "Flamengo", opponent: "Fluminense" });
      // Then I receive matches, each describing the two clubs with a date
      expect(matches.length).toBeGreaterThan(0);
      for (const m of matches) {
        const teams = `${m.homeKey} ${m.awayKey}`;
        expect(teams).toMatch(/flamengo/);
        expect(teams).toMatch(/fluminense/);
        expect(m.date).toBeDefined();
      }
    });

    it("Given a season filter, When searching, Then only that season is returned", () => {
      // When I restrict the search to 2019
      const matches = kb.findMatches({ team: "Palmeiras", season: 2019 });
      // Then every result is from 2019
      expect(matches.length).toBeGreaterThan(0);
      for (const m of matches) expect(m.season).toBe(2019);
    });

    it("Given results, When returned, Then they are sorted newest-first", () => {
      const matches = kb.findMatches({ team: "Santos", limit: 50 });
      for (let i = 1; i < matches.length; i++) {
        const prev = matches[i - 1].date ?? "";
        const cur = matches[i].date ?? "";
        if (prev && cur) expect(prev >= cur).toBe(true);
      }
    });
  });

  describe("Scenario: cross-file fixtures are deduplicated", () => {
    it("Given a 20-team season across 3 files, When counted, Then it is 380 matches", () => {
      // Given the 2019 Série A appears in three overlapping source files
      const matches = kb.findMatches({ competition: "Brasileirão Série A", season: 2019 });
      // When counted after deduplication
      // Then exactly one round-robin season remains (20 teams * 19 * 2)
      expect(matches.length).toBe(380);
    });
  });
});

describe("Feature: team queries", () => {
  describe("Scenario: get a team's home record for a season", () => {
    it("Given 2022 data, When requesting Corinthians' home Série A record, Then W/D/L and goals are returned", () => {
      // Given match data for 2022
      // When I request Corinthians' home record in the Brasileirão
      const rec = kb.teamRecord("Corinthians", {
        season: 2022,
        competition: "Brasileirão Série A",
        side: "home",
      });
      // Then I receive a coherent record (wins + draws + losses == matches)
      expect(rec.matches).toBeGreaterThan(0);
      expect(rec.wins + rec.draws + rec.losses).toBe(rec.matches);
      expect(rec.goalsFor).toBeGreaterThanOrEqual(0);
      expect(rec.winRate).toBeGreaterThanOrEqual(0);
      expect(rec.winRate).toBeLessThanOrEqual(1);
    });
  });

  describe("Scenario: head-to-head record", () => {
    it("Given two clubs, When computing head-to-head, Then totals reconcile", () => {
      // Given Flamengo and Fluminense
      const h = kb.headToHead("Flamengo", "Fluminense");
      // Then wins + draws account for every scored match
      expect(h.totalMatches).toBeGreaterThan(0);
      expect(h.teamAWins + h.teamBWins + h.draws).toBeLessThanOrEqual(h.totalMatches);
      expect(h.teamAGoals).toBeGreaterThanOrEqual(0);
      expect(h.teamBGoals).toBeGreaterThanOrEqual(0);
    });
  });
});

describe("Feature: competition queries", () => {
  describe("Scenario: who won the 2019 Brasileirão", () => {
    it("Given 2019 results, When standings are calculated, Then Flamengo are champions on 90 pts", () => {
      // Given the 2019 Série A matches
      // When standings are computed from results
      const table = kb.standings("Brasileirão Série A", 2019);
      // Then a full 20-team table is produced, led by Flamengo on 90 points
      expect(table).toHaveLength(20);
      expect(table[0].rank).toBe(1);
      expect(table[0].team).toMatch(/Flamengo/);
      expect(table[0].points).toBe(90);
      expect(table[0].wins).toBe(28);
      expect(table[0].draws).toBe(6);
      expect(table[0].losses).toBe(4);
    });

    it("Given the table, When inspected, Then points are non-increasing by rank", () => {
      const table = kb.standings("Brasileirão Série A", 2019);
      for (let i = 1; i < table.length; i++) {
        expect(table[i - 1].points >= table[i].points).toBe(true);
      }
    });

    it("Given same-base clubs, When in the table, Then Atlético-MG and Athletico-PR are distinct rows", () => {
      // Regression: suffix stripping previously merged these into one team.
      const table = kb.standings("Brasileirão Série A", 2019);
      const mg = table.find((r) => /-mg$|mineiro/i.test(r.team));
      const pr = table.find((r) => /-pr$|paranaense/i.test(r.team));
      expect(mg).toBeDefined();
      expect(pr).toBeDefined();
      expect(mg!.team).not.toBe(pr!.team);
    });
  });
});

describe("Feature: player queries", () => {
  describe("Scenario: search a player by name", () => {
    it("Given the FIFA data, When searching 'Neymar', Then the player and rating are returned", () => {
      // When I search for Neymar
      const players = kb.findPlayers({ name: "Neymar" });
      // Then the top Brazilian forward is found with his overall rating
      expect(players.length).toBeGreaterThan(0);
      expect(players[0].name).toMatch(/Neymar/);
      expect(players[0].overall).toBe(92);
      expect(players[0].nationality).toBe("Brazil");
    });
  });

  describe("Scenario: filter players by nationality", () => {
    it("Given nationality 'Brazil', When filtered, Then all results are Brazilian and rating-sorted", () => {
      // When I filter to Brazilian players
      const players = kb.findPlayers({ nationality: "Brazil", limit: 25 });
      // Then every result is Brazilian and sorted by overall descending
      expect(players.length).toBe(25);
      for (const p of players) expect(p.nationality).toBe("Brazil");
      for (let i = 1; i < players.length; i++) {
        expect((players[i - 1].overall ?? 0) >= (players[i].overall ?? 0)).toBe(true);
      }
      expect(players[0].name).toMatch(/Neymar/);
    });
  });

  describe("Scenario: filter players by club", () => {
    it("Given a club present in FIFA data, When filtered, Then only that club's players return", () => {
      // Note: FIFA 19 only licenses some Brazilian clubs (e.g. Santos), so we
      // assert on one that is present rather than Flamengo (which is absent).
      const players = kb.findPlayers({ club: "Santos" });
      expect(players.length).toBeGreaterThan(0);
      for (const p of players) expect(p.clubKey).toContain("santos");
    });
  });

  describe("Scenario: Brazilian players grouped by club", () => {
    it("Given nationality 'Brazil', When grouped by club, Then squads have counts and averages", () => {
      const squads = kb.clubSquads({ nationality: "Brazil", limit: 10 });
      expect(squads.length).toBeGreaterThan(0);
      for (const s of squads) {
        expect(s.playerCount).toBeGreaterThan(0);
        expect(s.averageOverall).toBeGreaterThan(0);
      }
      // Sorted by squad size descending.
      for (let i = 1; i < squads.length; i++) {
        expect(squads[i - 1].playerCount >= squads[i].playerCount).toBe(true);
      }
    });
  });
});

describe("Feature: statistical analysis", () => {
  describe("Scenario: average goals per match in the Brasileirão", () => {
    it("Given Série A matches, When aggregated, Then the average is a plausible ~2.5", () => {
      // When I aggregate Série A statistics
      const stats = kb.aggregateStats({ competition: "Brasileirão Série A" });
      // Then the average goals per match sits in a realistic football range
      expect(stats.matches).toBeGreaterThan(1000);
      expect(stats.averageGoals).toBeGreaterThan(2);
      expect(stats.averageGoals).toBeLessThan(3.5);
      // And outcome rates form a probability distribution.
      const sum = stats.homeWinRate + stats.awayWinRate + stats.drawRate;
      expect(sum).toBeCloseTo(1, 5);
      expect(stats.homeWinRate).toBeGreaterThan(stats.awayWinRate);
    });
  });

  describe("Scenario: biggest wins in the dataset", () => {
    it("Given match data, When listing biggest wins, Then they are ordered by margin", () => {
      const wins = kb.biggestWins({ competition: "Brasileirão Série A" }, 5);
      expect(wins.length).toBe(5);
      for (let i = 1; i < wins.length; i++) {
        const prev = Math.abs((wins[i - 1].homeGoals ?? 0) - (wins[i - 1].awayGoals ?? 0));
        const cur = Math.abs((wins[i].homeGoals ?? 0) - (wins[i].awayGoals ?? 0));
        expect(prev >= cur).toBe(true);
      }
      // The largest margin should be a blowout.
      const top = wins[0];
      expect(Math.abs((top.homeGoals ?? 0) - (top.awayGoals ?? 0))).toBeGreaterThanOrEqual(6);
    });
  });
});
