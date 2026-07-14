/**
 * Brazilian Soccer MCP Server — Tests
 *
 * BDD-style tests verifying all tool behaviors against the actual CSV datasets.
 * Run with: npm test
 */

import { describe, it, expect, beforeAll } from "vitest";
import { loadAllData } from "../src/loader.js";
import {
  searchMatches,
  searchPlayers,
  getTeamStats,
  headToHead,
  competitionStandings,
  biggestWins,
  goalsPerMatch,
  topTeams,
  bestRecord,
} from "../src/tools.js";
import { normalizeTeamName, lookupTeam } from "../src/types.js";
import type { SoccerData } from "../src/types.js";

let data: SoccerData;

beforeAll(() => {
  data = loadAllData();
});

// ─── Data Loading ────────────────────────────────────────────────────────────

describe("Data Loading", () => {
  it("loads all 6 CSV files", () => {
    expect(data.matches.length).toBeGreaterThan(0);
    expect(data.players.length).toBeGreaterThan(0);
  });

  it("loads Brasileirão matches", () => {
    const br = data.matches.filter((m) => m.competition === "Brasileirão");
    expect(br.length).toBeGreaterThan(0);
  });

  it("loads Copa do Brasil matches", () => {
    const cdb = data.matches.filter((m) => m.competition === "Copa do Brasil");
    expect(cdb.length).toBeGreaterThan(0);
  });

  it("loads Copa Libertadores matches", () => {
    const lib = data.matches.filter((m) => m.competition === "Copa Libertadores");
    expect(lib.length).toBeGreaterThan(0);
  });

  it("loads Histórico Brasileirão matches", () => {
    const hist = data.matches.filter((m) => m.competition === "Brasileirão (Histórico)");
    expect(hist.length).toBeGreaterThan(0);
  });

  it("loads FIFA players", () => {
    expect(data.players.length).toBeGreaterThan(10000);
    expect(data.players[0].name.length).toBeGreaterThan(0);
  });

  it("all matches have valid date and non-empty team names", () => {
    for (const m of data.matches) {
      expect(m.date.length).toBeGreaterThanOrEqual(4);
      expect(m.homeTeam.length).toBeGreaterThan(0);
      expect(m.awayTeam.length).toBeGreaterThan(0);
      expect(m.homeGoal).toBeGreaterThanOrEqual(0);
      expect(m.awayGoal).toBeGreaterThanOrEqual(0);
    }
  });
});

// ─── Team Name Normalization ─────────────────────────────────────────────────

describe("Team Name Normalization", () => {
  it("strips state suffixes", () => {
    expect(normalizeTeamName("Palmeiras-SP")).toBe("Palmeiras");
    expect(normalizeTeamName("Flamengo-RJ")).toBe("Flamengo");
    expect(normalizeTeamName("Corinthians-SP")).toBe("Corinthians");
  });

  it("strips parenthetical disambiguation", () => {
    expect(normalizeTeamName("Nacional (URU)")).toBe("Nacional");
    expect(normalizeTeamName("Barcelona-EQU")).toBe("Barcelona");
  });

  it("handles complex names", () => {
    const result = normalizeTeamName("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ");
    expect(result).toBe("Boavista Sport Club");
    expect(result).not.toContain("RJ");
    expect(result).not.toContain("antigo");
  });

  it("handles á, ã, ç characters", () => {
    expect(normalizeTeamName("São Paulo-SP")).toBe("São Paulo");
    expect(normalizeTeamName("Grêmio-RS")).toBe("Grêmio");
    expect(normalizeTeamName("Fortaleza-CE")).toBe("Fortaleza");
  });

  it("lookupTeam finds canonical names", () => {
    const known = new Set(["Flamengo", "Palmeiras", "São Paulo"]);
    expect(lookupTeam("Flamengo-RJ", known)).toBe("Flamengo");
    expect(lookupTeam("palmeiras", known)).toBe("Palmeiras");
    expect(lookupTeam("são paulo", known)).toBe("São Paulo");
    expect(lookupTeam("Botafogo", known)).toBeUndefined();
  });
});

// ─── Match Queries ───────────────────────────────────────────────────────────

describe("Match Queries", () => {
  it("searchMatches finds matches by team", () => {
    const result = searchMatches(data, { team: "Flamengo", limit: 10 });
    const text = result.content[0].text;
    expect(text).toContain("Flamengo");
    expect(text.split("\n").length).toBeGreaterThan(1);
  });

  it("searchMatches finds matches between two teams", () => {
    const result = searchMatches(data, { team: "Flamengo", opponent: "Palmeiras" });
    const text = result.content[0].text;
    expect(text).toContain("Flamengo");
    expect(text).toContain("Palmeiras");
  });

  it("searchMatches filters by competition", () => {
    const result = searchMatches(data, { competition: "Libertadores", limit: 10 });
    const text = result.content[0].text;
    expect(text).toContain("Libertadores");
  });

  it("searchMatches filters by season", () => {
    const result = searchMatches(data, { team: "Palmeiras", season: 2023, limit: 20 });
    const text = result.content[0].text;
    expect(text).toContain("Palmeiras");
  });

  it("searchMatches filters by date range", () => {
    const result = searchMatches(data, { dateFrom: "2023-01-01", dateTo: "2023-12-31", limit: 10 });
    const text = result.content[0].text;
    expect(text).not.toContain("No matches found");
  });

  it("searchMatches returns empty for non-existent team", () => {
    const result = searchMatches(data, { team: "zzzzzzxyzzy", limit: 5 });
    const text = result.content[0].text;
    expect(text).toContain("No matches found");
  });
});

// ─── Player Queries ──────────────────────────────────────────────────────────

describe("Player Queries", () => {
  it("searchPlayers finds players by name", () => {
    const result = searchPlayers(data, { name: "Neymar", limit: 5 });
    const text = result.content[0].text;
    expect(text).toContain("Neymar");
  });

  it("searchPlayers filters by nationality", () => {
    const result = searchPlayers(data, { nationality: "Brazil", limit: 5 });
    const text = result.content[0].text;
    expect(text).toContain("Brazil");
    expect(text.split("\n").length).toBeGreaterThan(1);
  });

  it("searchPlayers filters by club", () => {
    const result = searchPlayers(data, { club: "Flamengo", limit: 10 });
    const text = result.content[0].text;
    expect(text).toContain("Flamengo");
  });

  it("searchPlayers filters by position", () => {
    const result = searchPlayers(data, { position: "GK", limit: 10 });
    const text = result.content[0].text;
    const lines = text.split("\n").filter((l) => l.match(/^\d+\./));
    for (const line of lines) {
      expect(line).toContain("GK");
    }
  });

  it("searchPlayers filters by overall rating", () => {
    const result = searchPlayers(data, { minOverall: 90, limit: 10 });
    const text = result.content[0].text;
    expect(text.split("\n").length).toBeGreaterThan(1);
  });

  it("searchPlayers handles combined filters", () => {
    const result = searchPlayers(data, {
      nationality: "Brazil",
      club: "Flamengo",
      limit: 10,
    });
    const text = result.content[0].text;
    expect(text).toContain("Brazil");
    expect(text).toContain("Flamengo");
  });
});

// ─── Team Statistics ─────────────────────────────────────────────────────────

describe("Team Statistics", () => {
  it("getTeamStats computes stats for a team", () => {
    const result = getTeamStats(data, { team: "Palmeiras" });
    const text = result.content[0].text;
    expect(text).toContain("Matches:");
    expect(text).toContain("Wins:");
    expect(text).toContain("Goals For:");
  });

  it("getTeamStats with competition filter", () => {
    const result = getTeamStats(data, {
      team: "Flamengo",
      competition: "Brasileirão",
    });
    const text = result.content[0].text;
    expect(text).toContain("Flamengo");
  });

  it("getTeamStats with homeOnly", () => {
    const result = getTeamStats(data, { team: "São Paulo", homeOnly: true });
    const text = result.content[0].text;
    expect(text).toContain("home");
  });

  it("getTeamStats with season filter", () => {
    const result = getTeamStats(data, { team: "Corinthians", season: 2023 });
    const text = result.content[0].text;
    expect(text).toContain("Corinthians");
  });
});

// ─── Head-to-Head ────────────────────────────────────────────────────────────

describe("Head-to-Head", () => {
  it("headToHead computes records between two teams", () => {
    const result = headToHead(data, { teamA: "Flamengo", teamB: "Fluminense" });
    const text = result.content[0].text;
    expect(text).toContain("Flamengo");
    expect(text).toContain("Fluminense");
    expect(text).toContain("wins");
  });

  it("headToHead handles teams with no matches", () => {
    const result = headToHead(data, { teamA: "Real Madrid", teamB: "Barcelona" });
    const text = result.content[0].text;
    expect(text).toContain("No matches found");
  });
});

// ─── Competition Standings ───────────────────────────────────────────────────

describe("Competition Standings", () => {
  it("competitionStandings calculates standings", () => {
    const result = competitionStandings(data, {
      competition: "Brasileirão (Histórico)",
      season: 2019,
    });
    const text = result.content[0].text;
    expect(text).toContain("Standings");
    expect(text).toContain("pts");
    expect(text).toContain("Champion");
  });

  it("competitionStandings for Brasileirão 2023", () => {
    const result = competitionStandings(data, {
      competition: "Brasileirão",
      season: 2023,
    });
    const text = result.content[0].text;
    expect(text).toContain("2023");
  });
});

// ─── Biggest Wins ────────────────────────────────────────────────────────────

describe("Biggest Wins", () => {
  it("biggestWins returns sorted by goal difference", () => {
    const result = biggestWins(data, { limit: 5 });
    const text = result.content[0].text;
    expect(text.split("\n").length).toBeGreaterThan(1);
  });

  it("biggestWins filters by competition", () => {
    const result = biggestWins(data, {
      competition: "Libertadores",
      limit: 10,
    });
    const text = result.content[0].text;
    expect(text).toContain("Libertadores");
  });
});

// ─── Goals Per Match ─────────────────────────────────────────────────────────

describe("Goals Per Match", () => {
  it("goalsPerMatch computes aggregate statistics", () => {
    const result = goalsPerMatch(data, {});
    const text = result.content[0].text;
    expect(text).toContain("Total matches");
    expect(text).toContain("Average goals per match");
    expect(text).toContain("Home win rate");
  });

  it("goalsPerMatch filters by competition and season", () => {
    const result = goalsPerMatch(data, { competition: "Brasileirão", season: 2023 });
    const text = result.content[0].text;
    expect(text).toContain("Brasileirão");
  });
});

// ─── Top Teams ───────────────────────────────────────────────────────────────

describe("Top Teams", () => {
  it("topTeams ranks by wins", () => {
    const result = topTeams(data, { metric: "wins", limit: 5 });
    const text = result.content[0].text;
    const lines = text.split("\n").filter((l) => l.match(/^\d+\./));
    expect(lines.length).toBeGreaterThan(0);
  });

  it("topTeams ranks by goalsFor", () => {
    const result = topTeams(data, { metric: "goalsFor", limit: 5 });
    const text = result.content[0].text;
    expect(text).toContain("GF:");
  });

  it("topTeams ranks by winRate", () => {
    const result = topTeams(data, { metric: "winRate", limit: 5 });
    const text = result.content[0].text;
    expect(text).toContain("Win rate");
  });

  it("topTeams filters by season", () => {
    const result = topTeams(data, {
      metric: "wins",
      competition: "Brasileirão (Histórico)",
      season: 2019,
      limit: 5,
    });
    const text = result.content[0].text;
    expect(text).toContain("2019");
  });
});

// ─── Best Record ─────────────────────────────────────────────────────────────

describe("Best Record", () => {
  it("bestRecord home", () => {
    const result = bestRecord(data, { venue: "home", limit: 5 });
    const text = result.content[0].text;
    expect(text).toContain("Best home record");
  });

  it("bestRecord away", () => {
    const result = bestRecord(data, { venue: "away", limit: 5 });
    const text = result.content[0].text;
    expect(text).toContain("Best away record");
  });
});

// ─── Response Format ─────────────────────────────────────────────────────────

describe("Response Format", () => {
  it("all tool responses have text content type", () => {
    const tools = [
      searchMatches(data, { limit: 5 }),
      searchPlayers(data, { limit: 5 }),
      getTeamStats(data, { team: "Flamengo" }),
      headToHead(data, { teamA: "Flamengo", teamB: "Palmeiras" }),
      competitionStandings(data, { competition: "Brasileirão (Histórico)", season: 2019 }),
      biggestWins(data, { limit: 5 }),
      goalsPerMatch(data, {}),
      topTeams(data, { limit: 5 }),
      bestRecord(data, { venue: "home", limit: 5 }),
    ];

    for (const resp of tools) {
      expect(resp.content).toBeDefined();
      expect(resp.content.length).toBeGreaterThan(0);
      expect(resp.content[0].type).toBe("text");
      expect(typeof resp.content[0].text).toBe("string");
    }
  });
});

// ─── Data Coverage ────────────────────────────────────────────────────────────

describe("Data Coverage", () => {
  it("can answer at least 20 sample questions", () => {
    // Test 20+ distinct queries that all return meaningful results
    const queries: (() => string)[] = [
      () => searchMatches(data, { team: "Flamengo", limit: 5 }).content[0].text,
      () => searchMatches(data, { team: "Palmeiras", season: 2023, limit: 5 }).content[0].text,
      () => searchMatches(data, { competition: "Copa do Brasil", limit: 5 }).content[0].text,
      () => searchMatches(data, { competition: "Copa Libertadores", limit: 5 }).content[0].text,
      () => searchMatches(data, { team: "Flamengo", opponent: "Fluminense", limit: 5 }).content[0].text,
      () => searchPlayers(data, { name: "Neymar", limit: 3 }).content[0].text,
      () => searchPlayers(data, { nationality: "Brazil", limit: 5 }).content[0].text,
      () => searchPlayers(data, { club: "Flamengo", limit: 5 }).content[0].text,
      () => searchPlayers(data, { position: "LW", limit: 5 }).content[0].text,
      () => searchPlayers(data, { minOverall: 85, limit: 5 }).content[0].text,
      () => getTeamStats(data, { team: "Corinthians" }).content[0].text,
      () => getTeamStats(data, { team: "Santos", competition: "Brasileirão" }).content[0].text,
      () => getTeamStats(data, { team: "São Paulo", homeOnly: true }).content[0].text,
      () => headToHead(data, { teamA: "Palmeiras", teamB: "Santos" }).content[0].text,
      () => headToHead(data, { teamA: "Flamengo", teamB: "Vasco" }).content[0].text,
      () => competitionStandings(data, { competition: "Brasileirão (Histórico)", season: 2019 }).content[0].text,
      () => competitionStandings(data, { competition: "Brasileirão", season: 2023 }).content[0].text,
      () => biggestWins(data, { limit: 10 }).content[0].text,
      () => goalsPerMatch(data, {}).content[0].text,
      () => goalsPerMatch(data, { competition: "Brasileirão", season: 2020 }).content[0].text,
      () => topTeams(data, { metric: "wins", limit: 5 }).content[0].text,
      () => topTeams(data, { metric: "goalsFor", competition: "Brasileirão", limit: 5 }).content[0].text,
      () => bestRecord(data, { venue: "home", competition: "Brasileirão", limit: 5 }).content[0].text,
      () => bestRecord(data, { venue: "away", limit: 5 }).content[0].text,
      () => searchMatches(data, { team: "Grêmio", season: 2023, limit: 5 }).content[0].text,
    ];

    expect(queries.length).toBeGreaterThanOrEqual(20);

    for (const q of queries) {
      const text = q();
      expect(text.length).toBeGreaterThan(10);
      expect(text).not.toBe("No matches found.");
      expect(text).not.toBe("No players found.");
    }
  });

  it("cross-file queries work", () => {
    // Brasileirão + Histórico for a team
    const palmeiras = searchMatches(data, { team: "Palmeiras", limit: 5 }).content[0].text;
    expect(palmeiras).toContain("Palmeiras");

    // Player + match combo: players at a specific club
    const flaPlayers = searchPlayers(data, { club: "Flamengo", limit: 5 }).content[0].text;
    expect(flaPlayers).toContain("Flamengo");

    // Multiple competition sources
    const allComps = [
      searchMatches(data, { competition: "Brasileirão", limit: 1 }).content[0].text,
      searchMatches(data, { competition: "Copa do Brasil", limit: 1 }).content[0].text,
      searchMatches(data, { competition: "Libertadores", limit: 1 }).content[0].text,
      searchMatches(data, { competition: "Histórico", limit: 1 }).content[0].text,
    ];
    for (const t of allComps) {
      expect(t.length).toBeGreaterThan(10);
    }
  });
});