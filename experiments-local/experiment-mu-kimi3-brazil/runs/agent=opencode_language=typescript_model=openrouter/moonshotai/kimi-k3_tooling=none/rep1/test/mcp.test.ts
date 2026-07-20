/**
 * Feature: MCP protocol end-to-end
 *
 * The server must expose its capabilities as MCP tools over a transport,
 * returning properly formatted, helpful responses (including error cases).
 */
import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { getDataset } from "./helpers.js";
import { createServer } from "../src/server.js";

let client: Client;

async function callToolText(name: string, args: Record<string, unknown> = {}): Promise<string> {
  const result = await client.callTool({ name, arguments: args });
  const content = result.content as { type: string; text?: string }[];
  expect(Array.isArray(content)).toBe(true);
  expect(content[0].type).toBe("text");
  return content[0].text!;
}

beforeAll(async () => {
  const { dataset, graph } = getDataset();
  const server = createServer(dataset, graph);
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  client = new Client({ name: "bdd-test-client", version: "1.0.0" });
  await server.connect(serverTransport);
  await client.connect(clientTransport);
});

afterAll(async () => {
  await client.close();
});

describe("Feature: MCP tool surface", () => {
  it("exposes all required tools", async () => {
    const { tools } = await client.listTools();
    const names = tools.map((t) => t.name);
    for (const expected of [
      "dataset_summary",
      "find_matches",
      "head_to_head",
      "team_stats",
      "standings",
      "search_players",
      "brazilian_players_by_club",
      "biggest_wins",
      "competition_stats",
      "graph_neighbors",
    ]) {
      expect(names).toContain(expected);
    }
    // Every tool advertises a description and an object input schema.
    for (const t of tools) {
      expect(t.description?.length).toBeGreaterThan(10);
      expect(t.inputSchema.type).toBe("object");
    }
  });

  it("dataset_summary reports all six files and totals", async () => {
    const text = await callToolText("dataset_summary");
    expect(text).toContain("Brasileirao_Matches.csv: 4180");
    expect(text).toContain("fifa_data.csv: 18207");
    expect(text).toMatch(/Unified matches.*: \d+/);
    expect(text).toContain("Copa Libertadores");
  });

  it("find_matches answers 'Flamengo vs Fluminense' with scores and competitions", async () => {
    const text = await callToolText("find_matches", { team: "Flamengo", opponent: "Fluminense" });
    expect(text).toMatch(/match\(es\) found/);
    expect(text).toMatch(/\d{4}-\d{2}-\d{2}: Flamengo-RJ \d+-\d+ Fluminense-RJ|Fluminense-RJ \d+-\d+ Flamengo-RJ/);
    expect(text).toContain("Brasileirão Série A");
  });

  it("find_matches handles accents and suffixes transparently", async () => {
    const a = await callToolText("find_matches", { team: "São Paulo", season: 2023 });
    const b = await callToolText("find_matches", { team: "Sao Paulo-SP", season: 2023 });
    // Both spellings find the same number of matches.
    const countA = Number(a.match(/(\d+) match/)?.[1]);
    const countB = Number(b.match(/(\d+) match/)?.[1]);
    expect(countA).toBe(countB);
    expect(countA).toBeGreaterThan(0);
  });

  it("head_to_head formats the derby like the spec example", async () => {
    const text = await callToolText("head_to_head", { teamA: "Flamengo", teamB: "Fluminense" });
    expect(text).toContain("Flamengo vs Fluminense:");
    expect(text).toMatch(/Head-to-head in dataset: Flamengo \d+ wins, Fluminense \d+ wins, \d+ draws/);
  });

  it("team_stats formats records like the spec example", async () => {
    const text = await callToolText("team_stats", {
      team: "Corinthians",
      season: 2022,
      venue: "home",
      competition: "Brasileirão Série A",
    });
    expect(text).toContain("Corinthians home record (2022 Brasileirão Série A):");
    expect(text).toContain("- Matches: 19");
    expect(text).toMatch(/- Wins: \d+, Draws: \d+, Losses: \d+/);
    expect(text).toMatch(/- Goals For: \d+, Goals Against: \d+/);
    expect(text).toMatch(/- Win rate: \d+\.\d%/);
  });

  it("standings reproduces the 2019 Brasileirão (Flamengo champion)", async () => {
    const text = await callToolText("standings", { season: 2019 });
    expect(text).toContain("2019 Brasileirão Série A Standings (calculated from matches):");
    expect(text).toContain("1. Flamengo - 90 pts (28W, 6D, 4L");
    expect(text).toContain("Champion");
    expect(text).toContain("2. Santos - 74 pts");
  });

  it("search_players finds top Brazilians and club squads", async () => {
    const text = await callToolText("search_players", { nationality: "Brazil", limit: 3 });
    expect(text).toContain("Neymar Jr - Overall: 92");
    const squad = await callToolText("search_players", { team: "Grêmio", limit: 5 });
    expect(squad).toMatch(/5 player\(s\) found/);
  });

  it("biggest_wins and competition_stats return aggregated answers", async () => {
    const wins = await callToolText("biggest_wins", { limit: 3 });
    expect(wins).toContain("Biggest victories in all competitions (provided data):");
    expect(wins).toContain("São Paulo-SP 9-1 4 de Julho-PI");
    const stats = await callToolText("competition_stats", { competition: "Brasileirão" });
    expect(stats).toMatch(/Average goals per match: 2\.\d{2}/);
    expect(stats).toMatch(/Home win rate: \d+\.\d%/);
  });

  it("graph_neighbors explores the knowledge graph around a team", async () => {
    const text = await callToolText("graph_neighbors", { entity: "Flamengo", edgeType: "WON", limit: 5 });
    expect(text).toContain('team "Flamengo (RJ)"');
    expect(text).toMatch(/--WON-->| relationship\(s\) of type WON/);
  });

  it("returns helpful errors for unknown teams and competitions", async () => {
    const badTeam = await client.callTool({ name: "find_matches", arguments: { team: "Wolverhampton" } });
    expect(badTeam.isError).toBe(true);
    expect((badTeam.content as { text: string }[])[0].text).toContain("Team not found");
    const badComp = await client.callTool({ name: "find_matches", arguments: { competition: "MLS" } });
    expect(badComp.isError).toBe(true);
    expect((badComp.content as { text: string }[])[0].text).toContain("Unknown competition");
    const ambiguous = await client.callTool({ name: "team_stats", arguments: { team: "Atletico" } });
    expect((ambiguous.content as { text: string }[])[0].text).toContain("ambiguous");
  });
});
