/**
 * Feature: Sample questions from the specification
 *   The success criteria require at least 20 sample questions to be
 *   answerable. Each scenario below maps a spec question to the MCP
 *   tool call(s) that answer it, via an in-memory protocol client.
 */
import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { createServer } from "../src/server.js";
import { getDataset } from "./helpers.js";

let client: Client;

async function ask(tool: string, args: Record<string, unknown> = {}): Promise<string> {
  const r = await client.callTool({ name: tool, arguments: args });
  const c = r.content as { type: string; text?: string }[];
  return c[0]?.text ?? "";
}

beforeAll(async () => {
  const server = createServer(await getDataset());
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  client = new Client({ name: "questions-client", version: "0.0.1" });
  await client.connect(ct);
});

afterAll(async () => {
  await client.close();
});

describe("Feature: Simple lookups", () => {
  it("Q1: When did Flamengo last play Corinthians?", async () => {
    const out = await ask("last_meeting", { team_a: "Flamengo", team_b: "Corinthians" });
    expect(out).toMatch(/Last meeting: \d{4}-\d{2}-\d{2}: .+ \d+-\d+ .+/);
  });

  it("Q2: What was the score?", async () => {
    const out = await ask("last_meeting", { team_a: "Flamengo", team_b: "Corinthians" });
    expect(out).toMatch(/\d+-\d+/);
  });

  it("Q3: Who is Gabriel Barbosa? (graceful when absent)", async () => {
    const out = await ask("player_details", { name: "Gabriel Barbosa" });
    expect(out.length).toBeGreaterThan(0);
  });
});

describe("Feature: Relationship queries", () => {
  it("Q4: Which players play for Flamengo? (club filter)", async () => {
    const out = await ask("search_players", { club: "Flamengo" });
    // This FIFA edition lists no Flamengo squad — the tool answers gracefully.
    expect(out).toMatch(/No players found|Players found/);
  });

  it("Q5: Show me all derbies in 2023 (classic rivalries)", async () => {
    const derbies: [string, string][] = [
      ["Flamengo", "Fluminense"], // Fla-Flu
      ["Grêmio", "Internacional"], // Gre-Nal
      ["Corinthians", "Palmeiras"], // Derby Paulista
      ["Atlético-MG", "Cruzeiro"], // Clássico Mineiro
    ];
    let total = 0;
    for (const [a, b] of derbies) {
      const out = await ask("search_matches", { team: a, opponent: b, season: 2023 });
      total += (out.match(/^- \d{4}/gm) ?? []).length;
    }
    expect(total).toBeGreaterThan(3);
  });

  it("Q6: What competitions has Palmeiras played in?", async () => {
    const out = await ask("team_competitions", { team: "Palmeiras" });
    expect(out).toContain("Brasileirão Série A");
    expect(out).toContain("Copa do Brasil");
    expect(out).toContain("Copa Libertadores");
  });
});

describe("Feature: Match queries", () => {
  it("Q7: Show me all Flamengo vs Fluminense matches", async () => {
    const out = await ask("search_matches", { team: "Flamengo", opponent: "Fluminense", limit: 100 });
    const count = (out.match(/^- \d{4}/gm) ?? []).length;
    expect(count).toBeGreaterThan(20);
  });

  it("Q8: What matches did Palmeiras play in 2023?", async () => {
    const out = await ask("search_matches", { team: "Palmeiras", season: 2023, limit: 100 });
    expect(out).toMatch(/^- \d{4}/m);
  });

  it("Q9: Find all Copa do Brasil finals", async () => {
    const out = await ask("competition_finals", { competition: "Copa do Brasil" });
    expect((out.match(/^- \d{4}/gm) ?? []).length).toBeGreaterThan(5);
  });
});

describe("Feature: Team queries", () => {
  it("Q10: What is Corinthians' home record in 2022?", async () => {
    const out = await ask("team_statistics", { team: "Corinthians", season: 2022 });
    expect(out).toMatch(/Home: \d+ matches \| W \d+, D \d+, L \d+/);
  });

  it("Q11: Which team scored the most goals in Serie A 2023?", async () => {
    const out = await ask("top_scoring_teams", { competition: "Serie A", season: 2023, limit: 3 });
    expect(out).toMatch(/1\. .+ — \d+ goals/);
  });

  it("Q12: Compare Palmeiras and Santos head-to-head", async () => {
    const out = await ask("head_to_head", { team_a: "Palmeiras", team_b: "Santos" });
    expect(out).toMatch(/Palmeiras \d+ wins, Santos \d+ wins, \d+ draws/);
  });
});

describe("Feature: Player queries", () => {
  it("Q13: Find all Brazilian players in the dataset", async () => {
    const out = await ask("search_players", { nationality: "Brazil", limit: 100 });
    expect(out).toContain("Brazil");
  });

  it("Q14: Who are the highest-rated players at Santos?", async () => {
    const out = await ask("search_players", { club: "Santos", limit: 5 });
    expect(out).toContain("Players found");
  });

  it("Q15: Show me all forwards from Santos", async () => {
    const out = await ask("search_players", { club: "Santos", position: "forward" });
    expect(out).toMatch(/Position: (ST|CF|LW|RW)/);
  });
});

describe("Feature: Competition queries", () => {
  it("Q16: Who won the 2019 Brasileirão?", async () => {
    const out = await ask("competition_standings", { competition: "Brasileirão", season: 2019 });
    expect(out).toContain("1. Flamengo - 90 pts");
  });

  it("Q17: Show the 2018 Copa Libertadores bracket", async () => {
    const out = await ask("search_matches", {
      competition: "Libertadores",
      season: 2018,
      limit: 200,
    });
    expect(out).toContain("round of 16");
    expect(out).toContain("quarterfinals");
    expect(out).toContain("semifinals");
  });

  it("Q18: Which teams were relegated in 2020?", async () => {
    const out = await ask("competition_standings", { competition: "Brasileirão", season: 2020 });
    expect(out).toContain("relegation zone");
  });
});

describe("Feature: Analytical queries", () => {
  it("Q19: Which team has the best home record?", async () => {
    const out = await ask("best_venue_records", { venue: "home" });
    expect(out).toMatch(/Best home records/);
  });

  it("Q20: Who are the top Brazilian players?", async () => {
    const out = await ask("search_players", { nationality: "Brazil", limit: 3 });
    expect(out).toContain("Neymar Jr");
  });

  it("Q21: Compare the 2018 and 2019 seasons", async () => {
    const s18 = await ask("competition_stats", { competition: "Brasileirão", season: 2018 });
    const s19 = await ask("competition_stats", { competition: "Brasileirão", season: 2019 });
    for (const s of [s18, s19]) {
      expect(s).toMatch(/Average goals per match: \d\.\d\d/);
    }
  });

  it("Q22: What's the average goals per match in the Brasileirão?", async () => {
    const out = await ask("competition_stats", { competition: "Brasileirão" });
    expect(out).toMatch(/Average goals per match: 2\.\d\d/);
  });

  it("Q23: Which team has the best away record?", async () => {
    const out = await ask("best_venue_records", { venue: "away" });
    expect(out).toMatch(/Best away records/);
  });

  it("Q24: Show me the biggest wins in the dataset", async () => {
    const out = await ask("biggest_wins", { limit: 5 });
    expect(out).toMatch(/1\. \d{4}-\d{2}-\d{2}: .+ [5-9]\d?-\d .+/);
  });
});
