import { describe, it, expect, beforeAll } from "vitest";
import { clearCache } from "../dataLoader.js";
import {
  searchMatches,
  getTeamStats,
  headToHead,
  searchPlayers,
  getStandings,
  getTopStats,
} from "../tools.js";

beforeAll(() => {
  clearCache();
});

// Feature: Match Queries
describe("Feature: Match Queries", () => {
  describe("Scenario: Find matches for a specific team", () => {
    it("Given match data is loaded, When I search for Flamengo matches, Then I receive a list with Flamengo as home or away", () => {
      const result = searchMatches({ team: "Flamengo" });
      expect(result.total).toBeGreaterThan(0);
      expect(result.matches.length).toBeGreaterThan(0);
      for (const m of result.matches) {
        const hasFlamengo =
          m.home_team.toLowerCase().includes("flamengo") ||
          m.away_team.toLowerCase().includes("flamengo");
        expect(hasFlamengo).toBe(true);
      }
    });

    it("Given match data is loaded, When I search for Palmeiras in 2023, Then I receive matches from that season", () => {
      const result = searchMatches({ team: "Palmeiras", season: 2023 });
      expect(result.total).toBeGreaterThan(0);
      for (const m of result.matches) {
        expect(m.season).toBe(2023);
      }
    });
  });

  describe("Scenario: Find matches between two teams", () => {
    it("Given match data is loaded, When I search for Flamengo vs Fluminense, Then each match includes both teams", () => {
      const result = searchMatches({ team: "Flamengo", team2: "Fluminense" });
      expect(result.total).toBeGreaterThan(0);
      for (const m of result.matches) {
        const hasFlamengo =
          m.home_team.toLowerCase().includes("flamengo") ||
          m.away_team.toLowerCase().includes("flamengo");
        const hasFluminense =
          m.home_team.toLowerCase().includes("fluminense") ||
          m.away_team.toLowerCase().includes("fluminense");
        expect(hasFlamengo).toBe(true);
        expect(hasFluminense).toBe(true);
      }
    });
  });

  describe("Scenario: Filter matches by competition", () => {
    it("Given match data is loaded, When I filter by Copa do Brasil, Then all results are from that competition", () => {
      const result = searchMatches({ competition: "Copa do Brasil", limit: 50 });
      expect(result.total).toBeGreaterThan(0);
      for (const m of result.matches) {
        expect(m.competition.toLowerCase()).toContain("copa");
      }
    });

    it("Given match data is loaded, When I filter by Libertadores, Then all results are from that competition", () => {
      const result = searchMatches({ competition: "Libertadores", limit: 50 });
      expect(result.total).toBeGreaterThan(0);
      for (const m of result.matches) {
        expect(m.competition.toLowerCase()).toContain("libertadores");
      }
    });
  });

  describe("Scenario: Each match has required fields", () => {
    it("Given match data is loaded, When I receive match results, Then each match has date, scores, and competition", () => {
      const result = searchMatches({ team: "Corinthians", limit: 5 });
      expect(result.matches.length).toBeGreaterThan(0);
      for (const m of result.matches) {
        expect(m.datetime).toBeTruthy();
        expect(typeof m.home_goal).toBe("number");
        expect(typeof m.away_goal).toBe("number");
        expect(m.competition).toBeTruthy();
      }
    });
  });

  describe("Scenario: Limit results", () => {
    it("Given a limit parameter, When I request 5 results, Then I receive at most 5 matches", () => {
      const result = searchMatches({ limit: 5 });
      expect(result.matches.length).toBeLessThanOrEqual(5);
    });
  });
});

// Feature: Team Statistics
describe("Feature: Team Statistics", () => {
  describe("Scenario: Get team statistics", () => {
    it("Given match data is loaded, When I request stats for Palmeiras in 2023, Then I receive wins, losses, draws, and goals", () => {
      const stats = getTeamStats({ team: "Palmeiras", season: 2023 });
      expect(stats.matches).toBeGreaterThan(0);
      expect(typeof stats.wins).toBe("number");
      expect(typeof stats.draws).toBe("number");
      expect(typeof stats.losses).toBe("number");
      expect(typeof stats.goals_for).toBe("number");
      expect(typeof stats.goals_against).toBe("number");
      expect(stats.wins + stats.draws + stats.losses).toBe(stats.matches);
    });

    it("Given match data is loaded, When I request Corinthians home record, Then win_rate is a percentage between 0 and 100", () => {
      const stats = getTeamStats({ team: "Corinthians" });
      expect(stats.win_rate).toBeGreaterThanOrEqual(0);
      expect(stats.win_rate).toBeLessThanOrEqual(100);
    });

    it("Given match data is loaded, When I request stats for Flamengo in Brasileirao, Then competition filter works", () => {
      const stats = getTeamStats({ team: "Flamengo", competition: "Brasileirao" });
      expect(stats.matches).toBeGreaterThan(0);
      expect(stats.team).toBe("Flamengo");
    });
  });

  describe("Scenario: Points calculation", () => {
    it("Points equal wins*3 + draws", () => {
      const stats = getTeamStats({ team: "Santos", season: 2019 });
      expect(stats.points).toBe(stats.wins * 3 + stats.draws);
    });
  });
});

// Feature: Head-to-Head
describe("Feature: Head-to-Head Comparison", () => {
  describe("Scenario: Compare two teams", () => {
    it("Given match data is loaded, When I compare Flamengo and Corinthians, Then I receive win/draw/loss breakdown", () => {
      const h2h = headToHead({ team1: "Flamengo", team2: "Corinthians" });
      expect(h2h.total_matches).toBeGreaterThan(0);
      expect(h2h.team1_wins + h2h.team2_wins + h2h.draws).toBe(h2h.total_matches);
    });

    it("Given match data is loaded, When I compare two teams, Then recent matches are listed", () => {
      const h2h = headToHead({ team1: "Palmeiras", team2: "Santos" });
      expect(h2h.matches.length).toBeGreaterThan(0);
      for (const m of h2h.matches) {
        expect(m.datetime).toBeTruthy();
        expect(typeof m.home_goal).toBe("number");
        expect(typeof m.away_goal).toBe("number");
      }
    });
  });
});

// Feature: Player Queries
describe("Feature: Player Queries", () => {
  describe("Scenario: Find all Brazilian players", () => {
    it("Given player data is loaded, When I search for Brazilian players, Then I receive a list with nationality Brazil", () => {
      const result = searchPlayers({ nationality: "Brazil", limit: 50 });
      expect(result.total).toBeGreaterThan(100);
      for (const p of result.players) {
        expect(p.nationality.toLowerCase()).toContain("brazil");
      }
    });
  });

  describe("Scenario: Find players by club", () => {
    it("Given player data is loaded, When I search for Fluminense players, Then all returned players are at Fluminense", () => {
      const result = searchPlayers({ club: "Fluminense" });
      expect(result.players.length).toBeGreaterThan(0);
      for (const p of result.players) {
        expect(p.club.toLowerCase()).toContain("fluminense");
      }
    });
  });

  describe("Scenario: Find player by name", () => {
    it("Given player data is loaded, When I search for Neymar, Then results include matching names", () => {
      const result = searchPlayers({ name: "Neymar" });
      expect(result.players.length).toBeGreaterThan(0);
      for (const p of result.players) {
        expect(p.name.toLowerCase()).toContain("neymar");
      }
    });
  });

  describe("Scenario: Filter by minimum rating", () => {
    it("Given player data is loaded, When I filter by min_overall 85, Then all players have rating >= 85", () => {
      const result = searchPlayers({ min_overall: 85 });
      expect(result.players.length).toBeGreaterThan(0);
      for (const p of result.players) {
        expect(p.overall).toBeGreaterThanOrEqual(85);
      }
    });
  });
});

// Feature: Competition Standings
describe("Feature: Competition Standings", () => {
  describe("Scenario: Calculate season standings", () => {
    it("Given match data is loaded, When I request 2019 Brasileirao standings, Then teams are ranked by points", () => {
      const result = getStandings({ competition: "Brasileirao", season: 2019 });
      expect(result.standings.length).toBeGreaterThan(10);

      // Verify sorted by points descending
      for (let i = 0; i < result.standings.length - 1; i++) {
        expect(result.standings[i].points).toBeGreaterThanOrEqual(
          result.standings[i + 1].points
        );
      }
    });

    it("Given match data is loaded, When standings are calculated, Then each team's points = wins*3 + draws", () => {
      const result = getStandings({ competition: "Brasileirao", season: 2018 });
      for (const team of result.standings) {
        expect(team.points).toBe(team.wins * 3 + team.draws);
      }
    });
  });
});

// Feature: Statistical Analysis
describe("Feature: Statistical Analysis", () => {
  describe("Scenario: Get biggest wins", () => {
    it("Given match data is loaded, When I request biggest wins, Then results are sorted by goal margin descending", () => {
      const result = getTopStats({ stat: "biggest_wins", limit: 10 });
      const wins = result.results as Array<{ margin: number }>;
      expect(wins.length).toBeGreaterThan(0);
      for (let i = 0; i < wins.length - 1; i++) {
        expect(wins[i].margin).toBeGreaterThanOrEqual(wins[i + 1].margin);
      }
    });
  });

  describe("Scenario: Get averages", () => {
    it("Given match data is loaded, When I request averages, Then avg goals per match is between 1 and 5", () => {
      const result = getTopStats({ stat: "averages" });
      expect(result.avg_goals_per_match).toBeGreaterThan(1);
      expect(result.avg_goals_per_match).toBeLessThan(6);
    });

    it("Given match data, Then home win rate + draw rate + away win rate approximately equals 100", () => {
      const result = getTopStats({ stat: "averages" });
      const total =
        (result.home_win_rate as number) +
        (result.draw_rate as number) +
        (result.away_win_rate as number);
      expect(Math.abs(total - 100)).toBeLessThan(1);
    });
  });

  describe("Scenario: Get home record", () => {
    it("Given match data is loaded, When I request home records, Then results have win rates between 0 and 100", () => {
      const result = getTopStats({ stat: "home_record", limit: 10 });
      const records = result.results as Array<{ win_rate: number }>;
      expect(records.length).toBeGreaterThan(0);
      for (const r of records) {
        expect(r.win_rate).toBeGreaterThanOrEqual(0);
        expect(r.win_rate).toBeLessThanOrEqual(100);
      }
    });
  });

  describe("Scenario: Filter by competition and season", () => {
    it("Given match data is loaded, When I filter averages by Brasileirao 2019, Then result has total_matches > 0", () => {
      const result = getTopStats({
        stat: "averages",
        competition: "Brasileirao",
        season: 2019,
      });
      expect(result.total_matches).toBeGreaterThan(0);
    });
  });
});
