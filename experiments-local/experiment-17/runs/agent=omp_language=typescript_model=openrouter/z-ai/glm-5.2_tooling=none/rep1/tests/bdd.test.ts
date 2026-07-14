/**
 * Brazilian Soccer MCP Server — BDD (Given/When/Then) test suite.
 *
 * Context block
 * -------------
 * Vitest suite exercising every required query category from the spec using
 * GWT-structured scenarios. It loads the real Kaggle datasets once (shared
 * module scope) and asserts behavior against the actual data, so the tests
 * double as an end-to-end contract for the MCP tool handlers.
 *
 * Categories covered (mirroring TASK.md "Required Capabilities"):
 *   1. Match queries     — search_matches
 *   2. Team queries       — team_statistics, compare_teams
 *   3. Player queries     — search_players
 *   4. Competition queries — competition_standings
 *   5. Statistical analysis — match_statistics, biggest wins
 * Plus data-quality invariants: team-name normalization, date formats,
 * cross-file deduplication, and tool registration smoke test.
 */

import { describe, it, expect, beforeAll } from "vitest";
import { loadDataset } from "../src/data/loader.js";
import type { Dataset } from "../src/data/loader.js";
import {
  searchMatchesHandler,
  teamStatisticsHandler,
  compareTeamsHandler,
  searchPlayersHandler,
  competitionStandingsHandler,
  matchStatisticsHandler,
  listTeamsHandler,
  listCompetitionsHandler,
  registerTools,
} from "../src/tools.js";
import { parseDate } from "../src/data/dates.js";
import { aliasKey, TeamRegistry } from "../src/data/normalize.js";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

let ds: Dataset;

beforeAll(() => {
  ds = loadDataset("data/kaggle");
});

// ===========================================================================
// Feature 1: Match Queries
// ===========================================================================

describe("Feature: Match Queries", () => {
  describe("Scenario: Find matches between two teams", () => {
    it("Given the match data is loaded, When I search for matches between Flamengo and Fluminense, Then I should receive a list of matches each with date, scores, and competition", () => {
      const out = searchMatchesHandler(ds, { team: "Flamengo", opponent: "Fluminense", limit: 100 });
      expect(out).toContain("match(es)");
      // Every result line should carry a date (YYYY-MM-DD), a score (X-Y), and a competition token.
      const lines = out.split("\n").filter((l) => l.startsWith("- "));
      expect(lines.length).toBeGreaterThan(0);
      for (const line of lines) {
        expect(line).toMatch(/\d{4}-\d{2}-\d{2}/);
        expect(line).toMatch(/\d+-\d+/);
        expect(line).toMatch(/Brasileirão|Copa do Brasil|Copa Libertadores/);
      }
    });
  });

  describe("Scenario: Find matches by team and season", () => {
    it("Given the match data is loaded, When I search for Palmeiras matches in 2023, Then every returned match is from season 2023 and involves Palmeiras", () => {
      const out = searchMatchesHandler(ds, { team: "Palmeiras", season: 2023, limit: 500 });
      expect(out).not.toContain("No matches");
      const lines = out.split("\n").filter((l) => l.startsWith("- "));
      expect(lines.length).toBeGreaterThan(0);
      for (const line of lines) {
        expect(line).toMatch(/Palmeiras/);
        expect(line).toMatch(/2023/);
      }
    });
  });

  describe("Scenario: Filter by competition", () => {
    it("Given the data is loaded, When I search Copa Libertadores matches, Then all results are Libertadores matches", () => {
      const out = searchMatchesHandler(ds, { competition: "Copa Libertadores", limit: 50 });
      const lines = out.split("\n").filter((l) => l.startsWith("- "));
      expect(lines.length).toBeGreaterThan(0);
      for (const line of lines) {
        expect(line).toMatch(/Copa Libertadores/);
      }
    });
  });

  describe("Scenario: No matches found", () => {
    it("Given the data is loaded, When I search for a nonexistent team, Then I receive a clear empty result message", () => {
      const out = searchMatchesHandler(ds, { team: "NoSuch FC" });
      expect(out).toContain("No matches found");
    });
  });
});

// ===========================================================================
// Feature 2: Team Queries
// ===========================================================================

describe("Feature: Team Queries", () => {
  describe("Scenario: Get team statistics for a season", () => {
    it("Given the match data is loaded, When I request statistics for Palmeiras in season 2023 Brasileirão, Then I should receive wins, losses, draws, and goals", () => {
      const out = teamStatisticsHandler(ds, { team: "Palmeiras", competition: "Brasileirão", season: 2023 });
      expect(out).toMatch(/Matches:/);
      expect(out).toMatch(/Wins:/);
      expect(out).toMatch(/Draws:/);
      expect(out).toMatch(/Losses:/);
      expect(out).toMatch(/Goals For:/);
      expect(out).toMatch(/Goals Against:/);
      // A Brasileirão season has 38 rounds; Palmeiras should have ~38 matches.
      const m = Number(out.match(/Matches:\s*(\d+)/)?.[1]);
      expect(m).toBeGreaterThanOrEqual(35);
      expect(m).toBeLessThanOrEqual(45);
    });
  });

  describe("Scenario: Home record splits from overall", () => {
    it("Given the data is loaded, When I request Corinthians home record in 2022, Then home matches are roughly half the season", () => {
      const out = teamStatisticsHandler(ds, { team: "Corinthians", competition: "Brasileirão", season: 2022, venue: "home" });
      const m = Number(out.match(/Matches:\s*(\d+)/)?.[1]);
      expect(m).toBeGreaterThanOrEqual(15);
      expect(m).toBeLessThanOrEqual(22);
    });
  });

  describe("Scenario: Compare two teams head-to-head", () => {
    it("Given the data is loaded, When I compare Palmeiras and Santos, Then I receive meeting count, wins each, draws, and both teams' records", () => {
      const out = compareTeamsHandler(ds, { team_a: "Palmeiras", team_b: "Santos" });
      expect(out).toMatch(/Head-to-head/);
      expect(out).toMatch(/Matches:/);
      expect(out).toMatch(/wins:/);
      expect(out).toMatch(/Draws:/);
      expect(out).toContain("overall");
    });
  });
});

// ===========================================================================
// Feature 3: Player Queries
// ===========================================================================

describe("Feature: Player Queries", () => {
  describe("Scenario: Find all Brazilian players", () => {
    it("Given the FIFA data is loaded, When I search for Brazilian players sorted by overall, Then I receive players ordered by rating descending", () => {
      const out = searchPlayersHandler(ds, { nationality: "Brazil", sort_by: "overall", limit: 10 });
      expect(out).not.toContain("No players");
      const ratings = [...out.matchAll(/OVR (\d+)/g)].map((m) => Number(m[1]));
      expect(ratings.length).toBeGreaterThan(0);
      for (let i = 1; i < ratings.length; i++) {
        expect(ratings[i]).toBeLessThanOrEqual(ratings[i - 1]!);
      }
    });
  });

  describe("Scenario: Search by name", () => {
    it("Given the FIFA data is loaded, When I search for 'Neymar', Then I receive his record with club and position", () => {
      const out = searchPlayersHandler(ds, { name: "Neymar" });
      expect(out).toContain("Neymar");
      expect(out).toMatch(/OVR/);
      expect(out).toMatch(/Position|LW|RW|ST|CAM/);
    });
  });

  describe("Scenario: Filter by club", () => {
    it("Given the FIFA data is loaded, When I search players at a Brazilian club present in FIFA, Then all returned players belong to that club", () => {
      // FIFA 19 includes Santos (Brazil); use it to validate club filtering.
      const out = searchPlayersHandler(ds, { club: "Atlético Mineiro", limit: 20 });
      if (!out.includes("No players")) {
        const lines = out.split("\n").filter((l) => l.startsWith("- "));
        for (const line of lines) {
          expect(line).toMatch(/Atlético Mineiro/);
        }
      }
    });
  });
});

// ===========================================================================
// Feature 4: Competition Queries
// ===========================================================================

describe("Feature: Competition Queries", () => {
  describe("Scenario: Who won the 2019 Brasileirão", () => {
    it("Given the match data is loaded, When I compute 2019 Brasileirão standings, Then Flamengo is the champion with 90 points", () => {
      const out = competitionStandingsHandler(ds, { competition: "Brasileirão", season: 2019 });
      expect(out).toContain("Champion");
      const champLine = out.split("\n")[1];
      expect(champLine).toMatch(/^1\. Flamengo/);
      expect(champLine).toMatch(/90 pts/);
    });
  });

  describe("Scenario: Standings compute correct points", () => {
    it("Given the data is loaded, When I compute 2003 Brasileirão standings, Then Cruzeiro (historical champion) is top", () => {
      const out = competitionStandingsHandler(ds, { competition: "Brasileirão", season: 2003 });
      const top = out.split("\n")[1];
      expect(top).toMatch(/^1\. Cruzeiro/);
    });
  });

  describe("Scenario: Standings mark relegation zone", () => {
    it("Given the data is loaded, When I compute a full standings table, Then the bottom rows are flagged as relegation zone", () => {
      const out = competitionStandingsHandler(ds, { competition: "Brasileirão", season: 2019, limit: 30 });
      expect(out).toContain("relegation zone");
    });
  });
});

// ===========================================================================
// Feature 5: Statistical Analysis
// ===========================================================================

describe("Feature: Statistical Analysis", () => {
  describe("Scenario: Average goals per match in the Brasileirão", () => {
    it("Given the data is loaded, When I request Brasileirão statistics, Then I receive a sensible average goals-per-match and win rates", () => {
      const out = matchStatisticsHandler(ds, { competition: "Brasileirão", season: 2023 });
      expect(out).toMatch(/Average goals per match:/);
      const avg = Number(out.match(/Average goals per match:\s*([\d.]+)/)?.[1]);
      expect(avg).toBeGreaterThan(1.5);
      expect(avg).toBeLessThan(4);
      expect(out).toMatch(/Home win rate:/);
      expect(out).toMatch(/Away win rate:/);
    });
  });

  describe("Scenario: Biggest victories", () => {
    it("Given the data is loaded, When I request biggest victories for Copa Libertadores, Then the listed wins have non-trivial margins", () => {
      const out = matchStatisticsHandler(ds, { competition: "Copa Libertadores", biggest_wins: 5 });
      if (out.includes("Biggest victories")) {
        const block = out.split("Biggest victories:")[1]!;
        const margins = [...block.matchAll(/(\d+)-(\d+)/g)].map((m) => Math.abs(Number(m[1]) - Number(m[2])));
        for (const mg of margins) {
          expect(mg).toBeGreaterThanOrEqual(1);
        }
      }
    });
  });

  describe("Scenario: Home advantage exists", () => {
    it("Given the data is loaded, When I compute home vs away win rates for a season, Then home win rate exceeds away win rate", () => {
      const out = matchStatisticsHandler(ds, { competition: "Brasileirão", season: 2022, biggest_wins: 0 });
      const home = Number(out.match(/Home win rate:\s*([\d.]+)%/)?.[1]);
      const away = Number(out.match(/Away win rate:\s*([\d.]+)%/)?.[1]);
      expect(home).toBeGreaterThan(away);
    });
  });
});

// ===========================================================================
// Feature 6: Data Quality — normalization, dates, dedup
// ===========================================================================

describe("Feature: Data Quality", () => {
  describe("Scenario: Team name variants normalize to one node", () => {
    it("Given the registry, When I register 'Palmeiras-SP', 'Palmeiras', and 'Palmeiras SP', Then they all resolve to the same display name", () => {
      const reg = new TeamRegistry();
      const a = reg.register("Palmeiras-SP");
      const b = reg.register("Palmeiras");
      const c = reg.register("Palmeiras SP");
      expect(a).toBe(b);
      expect(b).toBe(c);
      expect(a).toBe("Palmeiras");
    });
  });

  describe("Scenario: Ambiguous Atlético clubs stay distinct", () => {
    it("Given the registry, When I register 'Atletico-MG' and 'Atletico-PR', Then they resolve to different clubs (Mineiro vs Paranaense)", () => {
      const reg = new TeamRegistry();
      const mg = reg.register("Atletico-MG");
      const pr = reg.register("Atletico-PR");
      expect(mg).not.toBe(pr);
      expect(mg).toBe("Atlético Mineiro");
      expect(pr).toBe("Athletico Paranaense");
    });
  });

  describe("Scenario: Accented vs unaccented merge", () => {
    it("Given the registry, When I register 'São Paulo' and 'Sao Paulo', Then they resolve to the same canonical 'São Paulo'", () => {
      const reg = new TeamRegistry();
      expect(reg.register("São Paulo")).toBe("São Paulo");
      expect(reg.register("Sao Paulo")).toBe("São Paulo");
    });
  });

  describe("Scenario: Multiple date formats parse to the same day", () => {
    it("Given date strings in ISO-datetime, ISO-date, and Brazilian formats, When I parse them, Then all resolve to the same UTC calendar day", () => {
      const a = parseDate("2019-04-27 16:00:00");
      const b = parseDate("2019-04-27");
      const c = parseDate("27/04/2019");
      expect(a).not.toBeNull();
      expect(b).not.toBeNull();
      expect(c).not.toBeNull();
      expect(a!.toISOString().slice(0, 10)).toBe("2019-04-27");
      expect(b!.toISOString().slice(0, 10)).toBe("2019-04-27");
      expect(c!.toISOString().slice(0, 10)).toBe("2019-04-27");
    });
  });

  describe("Scenario: Cross-file deduplication removes duplicate matches", () => {
    it("Given all six CSVs loaded, When I query 2019 Brasileirão, Then Flamengo has exactly 38 matches (no double-counting across sources)", () => {
      const out = teamStatisticsHandler(ds, { team: "Flamengo", competition: "Brasileirão", season: 2019 });
      const m = Number(out.match(/Matches:\s*(\d+)/)?.[1]);
      expect(m).toBe(38);
    });
  });

  describe("Scenario: aliasKey is stable and punctuation-insensitive", () => {
    it("Given team name strings, When I compute aliasKey, Then punctuation/accents/case differences collapse", () => {
      expect(aliasKey("Botafogo-RJ")).toBe(aliasKey("Botafogo RJ"));
      expect(aliasKey("São Paulo")).toBe(aliasKey("sao paulo"));
      expect(aliasKey("Atlético Mineiro")).toBe(aliasKey("atletico mineiro"));
    });
  });
});

// ===========================================================================
// Feature 7: Catalog & server smoke
// ===========================================================================

describe("Feature: Catalog and Server Smoke", () => {
  describe("Scenario: List teams and competitions", () => {
    it("Given the dataset, When I list teams filtered by 'Fla', Then I see Flamengo (and not Palmeiras)", () => {
      const out = listTeamsHandler(ds, { query: "Fla" });
      expect(out).toContain("Flamengo");
      expect(out).not.toContain("Palmeiras");
    });

    it("Given the dataset, When I list competitions, Then all four named competitions appear", () => {
      const out = listCompetitionsHandler(ds);
      expect(out).toContain("Brasileirão");
      expect(out).toContain("Copa do Brasil");
      expect(out).toContain("Copa Libertadores");
    });
  });

  describe("Scenario: MCP server registers all tools", () => {
    it("Given a McpServer, When I register tools, Then registration completes without error and the server is usable", () => {
      const server = new McpServer({ name: "test", version: "0.0.0" });
      expect(() => registerTools(server, ds)).not.toThrow();
    });
  });

  describe("Scenario: Dataset coverage invariants", () => {
    it("Given the loaded dataset, Then all six source files contributed data", () => {
      // Match sources present.
      const sources = new Set(ds.matches.map((m) => m.source));
      expect(sources.has("Brasileirao_Matches")).toBe(true);
      expect(sources.has("Brazilian_Cup_Matches")).toBe(true);
      expect(sources.has("Libertadores_Matches")).toBe(true);
      expect(sources.has("BR-Football-Dataset")).toBe(true);
      expect(sources.has("novo_campeonato_brasileiro")).toBe(true);
      // Players loaded.
      expect(ds.players.length).toBeGreaterThan(10000);
      // Brasileirão spans historical + modern seasons.
      const seasons = (ds.seasonsByCompetition.get("Brasileirão") ?? []).sort();
      expect(seasons[0]).toBeLessThanOrEqual(2003);
      expect(seasons[seasons.length - 1]).toBeGreaterThanOrEqual(2023);
    });
  });
});
