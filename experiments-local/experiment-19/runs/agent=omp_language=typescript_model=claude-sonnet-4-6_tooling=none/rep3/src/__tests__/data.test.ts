import { describe, it, expect, beforeAll } from "vitest";
import {
  loadMatches,
  loadPlayers,
  normalizeTeam,
  teamMatchesQuery,
  matchesCompetition,
} from "../data.js";

// Load data once for the whole suite (heavy files)
beforeAll(() => {
  loadMatches();
  loadPlayers();
});

// ---------------------------------------------------------------------------
// normalizeTeam
// ---------------------------------------------------------------------------

describe("normalizeTeam", () => {
  it("strips state suffix with dash", () => {
    expect(normalizeTeam("Flamengo-RJ")).toBe("flamengo");
    expect(normalizeTeam("Palmeiras-SP")).toBe("palmeiras");
    expect(normalizeTeam("Atletico-MG")).toBe("atletico");
  });

  it("strips state suffix with space-dash-space", () => {
    expect(normalizeTeam("Grêmio - RS")).toBe("gremio");
    expect(normalizeTeam("São Paulo - SP")).toBe("sao paulo");
    expect(normalizeTeam("Flamengo - RJ")).toBe("flamengo");
  });

  it("removes Portuguese accents", () => {
    expect(normalizeTeam("Grêmio")).toBe("gremio");
    expect(normalizeTeam("Atlético Mineiro")).toBe("atletico mineiro");
    expect(normalizeTeam("Náutico")).toBe("nautico");
  });

  it("lowercases everything", () => {
    expect(normalizeTeam("CORINTHIANS")).toBe("corinthians");
  });

  it("handles names without suffixes", () => {
    expect(normalizeTeam("Flamengo")).toBe("flamengo");
    expect(normalizeTeam("Corinthians")).toBe("corinthians");
  });
});

// ---------------------------------------------------------------------------
// teamMatchesQuery
// ---------------------------------------------------------------------------

describe("teamMatchesQuery", () => {
  it("matches identical normalized names", () => {
    expect(teamMatchesQuery("Flamengo-RJ", "Flamengo")).toBe(true);
    expect(teamMatchesQuery("Flamengo - RJ", "Flamengo")).toBe(true);
    expect(teamMatchesQuery("Flamengo", "Flamengo")).toBe(true);
  });

  it("matches partial normalized name", () => {
    expect(teamMatchesQuery("Atletico-MG", "Atletico Mineiro")).toBe(true);
    expect(teamMatchesQuery("Atletico Mineiro", "Atletico")).toBe(true);
  });

  it("does not match unrelated teams", () => {
    expect(teamMatchesQuery("Flamengo-RJ", "Palmeiras")).toBe(false);
    expect(teamMatchesQuery("Corinthians", "Santos")).toBe(false);
  });

  it("empty query matches everything", () => {
    expect(teamMatchesQuery("Any Team", "")).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// loadMatches
// ---------------------------------------------------------------------------

describe("loadMatches", () => {
  it("loads more than 15 000 matches total", () => {
    expect(loadMatches().length).toBeGreaterThan(15_000);
  });

  it("has records from all 5 competitions", () => {
    const comps = new Set(loadMatches().map((m) => m.competition));
    expect(comps.has("brasileirao")).toBe(true);
    expect(comps.has("copa_brasil")).toBe(true);
    expect(comps.has("libertadores")).toBe(true);
    expect(comps.has("extended")).toBe(true);
    expect(comps.has("historical")).toBe(true);
  });

  it("brasileirao matches have season >= 2012", () => {
    const br = loadMatches().filter((m) => m.competition === "brasileirao");
    expect(br.every((m) => m.season >= 2012)).toBe(true);
  });

  it("historical matches have season 2003-2019", () => {
    const hist = loadMatches().filter((m) => m.competition === "historical");
    expect(hist.every((m) => m.season >= 2003 && m.season <= 2019)).toBe(true);
  });

  it("all match dates are in YYYY-MM-DD format", () => {
    const dateRe = /^\d{4}-\d{2}-\d{2}$/;
    const bad = loadMatches().filter((m) => !dateRe.test(m.date)).slice(0, 3);
    expect(bad).toHaveLength(0);
  });

  it("goals are non-negative integers", () => {
    const bad = loadMatches().filter(
      (m) =>
        m.homeGoals < 0 || m.awayGoals < 0 ||
        !Number.isInteger(m.homeGoals) || !Number.isInteger(m.awayGoals)
    );
    expect(bad).toHaveLength(0);
  });

  it("Flamengo appears as home or away team in Brasileirão", () => {
    const flamengo = loadMatches().filter(
      (m) =>
        m.competition === "brasileirao" &&
        (teamMatchesQuery(m.homeTeam, "Flamengo") ||
          teamMatchesQuery(m.awayTeam, "Flamengo"))
    );
    expect(flamengo.length).toBeGreaterThan(50);
  });
});

// ---------------------------------------------------------------------------
// loadPlayers
// ---------------------------------------------------------------------------

describe("loadPlayers", () => {
  it("loads more than 15 000 players", () => {
    expect(loadPlayers().length).toBeGreaterThan(15_000);
  });

  it("all players have a positive overall rating", () => {
    expect(loadPlayers().every((p) => p.overall > 0 && p.overall <= 99)).toBe(true);
  });

  it("Neymar Jr is in the dataset with correct attributes", () => {
    const neymar = loadPlayers().find((p) => p.name === "Neymar Jr");
    expect(neymar).toBeDefined();
    expect(neymar!.nationality).toBe("Brazil");
    expect(neymar!.overall).toBeGreaterThanOrEqual(90);
  });

  it("Casemiro is in the dataset as Brazilian", () => {
    const casemiro = loadPlayers().find((p) => p.name === "Casemiro");
    expect(casemiro).toBeDefined();
    expect(casemiro!.nationality).toBe("Brazil");
  });

  it("has Brazilian players at Brazilian clubs (Santos and Internacional are in the dataset)", () => {
    const atBrazilianClub = loadPlayers().filter(
      (p) =>
        p.nationality === "Brazil" &&
        (p.club === "Santos" || p.club === "Internacional" || p.club === "Cruzeiro" || p.club === "Botafogo")
    );
    expect(atBrazilianClub.length).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------
// matchesCompetition
// ---------------------------------------------------------------------------

describe("matchesCompetition", () => {
  const br = loadMatches().find((m) => m.competition === "brasileirao")!;
  const copa = loadMatches().find((m) => m.competition === "copa_brasil")!;
  const lib = loadMatches().find((m) => m.competition === "libertadores")!;
  const hist = loadMatches().find((m) => m.competition === "historical")!;

  it("'all' matches any competition", () => {
    expect(matchesCompetition(br, "all")).toBe(true);
    expect(matchesCompetition(copa, "all")).toBe(true);
    expect(matchesCompetition(lib, "all")).toBe(true);
  });

  it("'brasileirao' matches brasileirao and historical", () => {
    expect(matchesCompetition(br, "brasileirao")).toBe(true);
    expect(matchesCompetition(hist, "brasileirao")).toBe(true);
    expect(matchesCompetition(copa, "brasileirao")).toBe(false);
  });

  it("'copa_brasil' matches copa_brasil only", () => {
    expect(matchesCompetition(copa, "copa_brasil")).toBe(true);
    expect(matchesCompetition(br, "copa_brasil")).toBe(false);
    expect(matchesCompetition(lib, "copa_brasil")).toBe(false);
  });

  it("'libertadores' matches libertadores only", () => {
    expect(matchesCompetition(lib, "libertadores")).toBe(true);
    expect(matchesCompetition(copa, "libertadores")).toBe(false);
  });
});
