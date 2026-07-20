/**
 * Feature: MCP protocol end-to-end
 *   The server speaks the Model Context Protocol: tools are listed
 *   and callable, and answers come back as formatted text.
 */
import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { createServer } from "../src/server.js";
import { getDataset } from "./helpers.js";

let client: Client;

async function callTool(name: string, args: Record<string, unknown> = {}): Promise<string> {
  const result = await client.callTool({ name, arguments: args });
  const content = result.content as { type: string; text?: string }[];
  expect(Array.isArray(content)).toBe(true);
  expect(content[0].type).toBe("text");
  return content[0].text ?? "";
}

beforeAll(async () => {
  const ds = await getDataset();
  const server = createServer(ds);
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  await server.connect(serverTransport);
  client = new Client({ name: "test-client", version: "0.0.1" });
  await client.connect(clientTransport);
});

afterAll(async () => {
  await client.close();
});

describe("Feature: MCP server end-to-end", () => {
  it("Scenario: The server lists its tools", async () => {
    // When a client asks for the tool list
    const { tools } = await client.listTools();
    const names = tools.map((t) => t.name);
    // Then the five capability categories are represented
    expect(names).toEqual(
      expect.arrayContaining([
        "search_matches",
        "head_to_head",
        "last_meeting",
        "team_statistics",
        "team_competitions",
        "top_scoring_teams",
        "search_players",
        "player_details",
        "players_per_club",
        "competition_standings",
        "competition_finals",
        "competition_seasons",
        "competition_stats",
        "biggest_wins",
        "best_venue_records",
        "dataset_summary",
      ]),
    );
    // And every tool carries a description and schema
    for (const t of tools) {
      expect(t.description).toBeTruthy();
      expect(t.inputSchema).toBeTruthy();
    }
  });

  it("Scenario: 'Show me all Flamengo vs Fluminense matches'", async () => {
    const out = await callTool("search_matches", {
      team: "Flamengo",
      opponent: "Fluminense",
      limit: 10,
    });
    expect(out).toContain("Flamengo vs Fluminense");
    expect(out).toMatch(/\d{4}-\d{2}-\d{2}: .+ \d+-\d+ .+/);
  });

  it("Scenario: 'What was the score when Flamengo last played Corinthians?'", async () => {
    const out = await callTool("last_meeting", {
      team_a: "Flamengo",
      team_b: "Corinthians",
    });
    expect(out).toContain("Last meeting:");
    expect(out).toMatch(/\d+-\d+/);
  });

  it("Scenario: 'What is Corinthians' home record in 2022?'", async () => {
    const out = await callTool("team_statistics", {
      team: "Corinthians",
      season: 2022,
      competition: "Brasileirão",
    });
    expect(out).toContain("Corinthians record");
    expect(out).toMatch(/Home: \d+ matches/);
    expect(out).toMatch(/Win rate \d+\.\d%/);
  });

  it("Scenario: 'Who won the 2019 Brasileirão?'", async () => {
    const out = await callTool("competition_standings", {
      competition: "Brasileirão Série A",
      season: 2019,
    });
    expect(out).toContain("1. Flamengo - 90 pts (28W, 6D, 4L)");
    expect(out).toContain("Champion");
    expect(out).toContain("relegation zone");
  });

  it("Scenario: 'Who is Neymar Jr?'", async () => {
    const out = await callTool("player_details", { name: "Neymar Jr" });
    expect(out).toContain("Neymar Jr");
    expect(out).toContain("Paris Saint-Germain");
    expect(out).toMatch(/Overall: 92/);
  });

  it("Scenario: player_details is graceful when the player is absent", async () => {
    // Gabriel Barbosa is not in this FIFA edition
    const out = await callTool("player_details", { name: "Gabriel Barbosa" });
    expect(out).toContain("No player named like");
  });

  it("Scenario: 'Who are the highest-rated players at Santos?'", async () => {
    const out = await callTool("search_players", { club: "Santos", limit: 5 });
    expect(out).toContain("Players found");
    expect(out).toContain("Santos");
  });

  it("Scenario: 'Find all Copa do Brasil finals'", async () => {
    const out = await callTool("competition_finals", { competition: "Copa do Brasil" });
    expect(out).toContain("Copa do Brasil finals");
    expect(out).toMatch(/\d{4}-\d{2}-\d{2}/);
  });

  it("Scenario: 'Show me the biggest wins in the dataset'", async () => {
    const out = await callTool("biggest_wins", { limit: 5 });
    expect(out).toContain("Biggest victories");
    expect(out).toMatch(/1\. \d{4}-\d{2}-\d{2}: .+ \d+-\d+ .+/);
  });

  it("Scenario: 'What's the average goals per match in the Brasileirão?'", async () => {
    const out = await callTool("competition_stats", { competition: "Brasileirão" });
    expect(out).toMatch(/Average goals per match: \d\.\d\d/);
    expect(out).toMatch(/Home win rate: \d+\.\d%/);
  });

  it("Scenario: 'Which team has the best away record?'", async () => {
    const out = await callTool("best_venue_records", { venue: "away" });
    expect(out).toContain("Best away records");
  });

  it("Scenario: 'Compare Palmeiras and Santos head-to-head'", async () => {
    const out = await callTool("head_to_head", { team_a: "Palmeiras", team_b: "Santos" });
    expect(out).toContain("head-to-head");
    expect(out).toMatch(/Palmeiras \d+ wins, Santos \d+ wins, \d+ draws/);
  });

  it("Scenario: 'What competitions has Palmeiras played in?'", async () => {
    const out = await callTool("team_competitions", { team: "Palmeiras" });
    expect(out).toContain("Brasileirão Série A");
    expect(out).toContain("Copa Libertadores");
  });

  it("Scenario: 'Which team scored the most goals in Serie A 2023?'", async () => {
    const out = await callTool("top_scoring_teams", {
      competition: "Serie A",
      season: 2023,
    });
    expect(out).toContain("Top scoring teams");
    expect(out).toMatch(/1\. .+ — \d+ goals/);
  });

  it("Scenario: 'How many Brazilian players are at each club?'", async () => {
    const out = await callTool("players_per_club", { nationality: "Brazil" });
    expect(out).toContain("Players per club");
    expect(out).toMatch(/avg rating: \d+/);
  });

  it("Scenario: Dataset summary reports full coverage", async () => {
    const out = await callTool("dataset_summary");
    expect(out).toContain("fifa_data.csv");
    expect(out).toMatch(/Totals: \d+ matches, \d+ players/);
  });

  it("Scenario: Invalid arguments return a protocol error, not a crash", async () => {
    const result = await client.callTool({
      name: "search_matches",
      arguments: { from_date: "18/07/2026" },
    });
    // Then the server flags the error and explains the expected format
    expect(result.isError).toBe(true);
    const content = result.content as { type: string; text?: string }[];
    expect(content[0].text).toContain("YYYY-MM-DD");
  });
});
