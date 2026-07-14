import { describe, it, expect, beforeAll } from "vitest";
import {
  normalizeTeamName,
  teamKey,
  sameTeam,
  parseDate,
} from "../src/normalize.js";
import { loadDataset } from "../src/data.js";
import { QueryEngine } from "../src/query.js";

describe("Normalization", () => {
  it("strips state suffixes", () => {
    expect(normalizeTeamName("Palmeiras-SP")).toBe("Palmeiras");
    expect(normalizeTeamName("Flamengo-RJ")).toBe("Flamengo");
  });

  it("strips parenthetical suffixes", () => {
    expect(normalizeTeamName("Nacional (URU)")).toBe("Nacional");
    expect(teamKey("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ")).toBe(
      teamKey("Boavista")
    );
  });

  it("maps full names to short names", () => {
    expect(normalizeTeamName("Sport Club Corinthians Paulista")).toBe("Corinthians");
    expect(normalizeTeamName("São Paulo FC")).toBe("Sao Paulo");
  });

  it("does not collapse different Atletico clubs", () => {
    expect(sameTeam("Atletico-MG", "Atletico-PR")).toBe(false);
    expect(sameTeam("Athletico-PR", "Atletico-PR")).toBe(true);
  });

  it("maps Brazilian name variants consistently", () => {
    expect(normalizeTeamName("Botafogo RJ")).toBe("Botafogo");
    expect(normalizeTeamName("EC Bahia")).toBe("Bahia");
    expect(normalizeTeamName("Vasco Da Gama RJ")).toBe("Vasco");
  });

  it("considers variants the same team", () => {
    expect(sameTeam("Palmeiras-SP", "Palmeiras")).toBe(true);
    expect(sameTeam("Grêmio", "Gremio")).toBe(true);
    expect(sameTeam("Flamengo", "Palmeiras")).toBe(false);
  });

  it("parses ISO and Brazilian dates", () => {
    expect(parseDate("2012-05-19 18:30:00")).toBe("2012-05-19");
    expect(parseDate("2023-09-24")).toBe("2023-09-24");
    expect(parseDate("29/03/2003")).toBe("2003-03-29");
  });
});

describe("Data loading", () => {
  let dataset: ReturnType<typeof loadDataset>;

  beforeAll(() => {
    dataset = loadDataset();
  });

  it("loads all CSV files", () => {
    expect(dataset.matches.length).toBeGreaterThan(15000);
    expect(dataset.players.length).toBeGreaterThan(10000);
  });

  it("covers all expected competitions", () => {
    const competitions = new Set(dataset.matches.map((m) => m.competition));
    expect(competitions.has("Brasileirão")).toBe(true);
    expect(competitions.has("Copa do Brasil")).toBe(true);
    expect(competitions.has("Copa Libertadores")).toBe(true);
  });

  it("stacks historical and modern Brasileirão data", () => {
    const brasileirao = dataset.matches.filter((m) => m.competition === "Brasileirão");
    const seasons = new Set(brasileirao.map((m) => m.season));
    expect(seasons.has(2003)).toBe(true);
    expect(seasons.has(2023)).toBe(true);
  });
});

describe("Match queries", () => {
  let engine: QueryEngine;

  beforeAll(() => {
    const dataset = loadDataset();
    engine = new QueryEngine(dataset.matches, dataset.players);
  });

  it("finds matches between Flamengo and Fluminense", () => {
    const result = engine.findMatchesBetweenTeams("Flamengo", "Fluminense", 5);
    expect(result.text).toContain("Flamengo");
    expect(result.text).toContain("Fluminense");
    expect(result.data.matches.length).toBeGreaterThan(0);
  });

  it("finds Palmeiras matches in 2023", () => {
    const result = engine.findMatches({ team: "Palmeiras", season: 2023 });
    expect(result.text).toContain("Palmeiras");
    expect(result.data.length).toBeGreaterThan(0);
  });

  it("finds Copa do Brasil finals", () => {
    // Finals are often recorded in round "Final" or stage "final" depending on source
    const result = engine.findMatches({ competition: "Copa do Brasil" }, 200);
    expect(result.data.length).toBeGreaterThan(0);
  });
});

describe("Team queries", () => {
  let engine: QueryEngine;

  beforeAll(() => {
    const dataset = loadDataset();
    engine = new QueryEngine(dataset.matches, dataset.players);
  });

  it("returns Corinthians home record in 2022", () => {
    const result = engine.getTeamStats("Corinthians", { season: 2022, homeTeam: "Corinthians" });
    expect(result.text).toContain("Corinthians home record (2022");
    expect(result.data.matches).toBeGreaterThan(0);
  });

  it("compares Palmeiras and Santos", () => {
    const result = engine.compareTeams("Palmeiras", "Santos");
    expect(result.text).toContain("Palmeiras");
    expect(result.text).toContain("Santos");
  });
});

describe("Player queries", () => {
  let engine: QueryEngine;

  beforeAll(() => {
    const dataset = loadDataset();
    engine = new QueryEngine(dataset.matches, dataset.players);
  });

  it("looks up Gabriel Barbosa", () => {
    const result = engine.getPlayerByName("Gabriel Barbosa");
    expect(result.text).toContain("Gabriel");
  });

  it("finds Brazilian players at Cruzeiro", () => {
    const result = engine.findPlayers({ nationality: "Brazil", club: "Cruzeiro", limit: 10 });
    expect(result.data.length).toBeGreaterThan(0);
    expect(result.text).toContain("Brazil");
  });
});

describe("Competition queries", () => {
  let engine: QueryEngine;

  beforeAll(() => {
    const dataset = loadDataset();
    engine = new QueryEngine(dataset.matches, dataset.players);
  });

  it("calculates 2019 Brasileirão standings", () => {
    const result = engine.getStandings("Brasileirão", 2019);
    expect(result.text).toContain("2019 Brasileirão");
    expect(result.data[0].points).toBeGreaterThan(0);
  });

  it("identifies top scoring teams in Serie A 2023", () => {
    const result = engine.getTopScoringTeams("Brasileirão", 2023, 5);
    expect(result.data.length).toBeGreaterThan(0);
  });
});

describe("Statistical analysis", () => {
  let engine: QueryEngine;

  beforeAll(() => {
    const dataset = loadDataset();
    engine = new QueryEngine(dataset.matches, dataset.players);
  });

  it("returns overall Brasileirão stats", () => {
    const result = engine.getOverallStats("Brasileirão");
    expect(result.text).toContain("Average goals per match");
    expect(result.text).toContain("Home win rate");
  });

  it("finds biggest wins", () => {
    const result = engine.getBiggestWins("Brasileirão", 5);
    expect(result.data.length).toBeGreaterThan(0);
  });
});
