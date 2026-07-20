import { beforeAll, describe, expect, it } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import type { KnowledgeGraph } from "../src/knowledgeGraph.js";
import { getGraph } from "../src/knowledgeGraph.js";
import { createServer } from "../src/server.js";

/**
 * Feature: MCP protocol surface — tools are callable end-to-end over the
 * MCP transport (in-memory pair for tests; stdio in production).
 */
describe("Feature: MCP server tools", () => {
  let client: Client;

  beforeAll(async () => {
    const graph: KnowledgeGraph = await getGraph();
    const server = createServer(graph);
    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
    await server.connect(serverTransport);
    client = new Client({ name: "test-client", version: "1.0.0" });
    await client.connect(clientTransport);
  });

  it("Scenario: Server lists its tools", async () => {
    const { tools } = await client.listTools();
    const names = tools.map((t) => t.name);
    for (const expected of [
      "search_matches",
      "head_to_head",
      "team_statistics",
      "competition_standings",
      "search_players",
      "biggest_wins",
      "goals_statistics",
      "last_match",
      "team_competitions",
      "top_scoring_teams",
      "brazilian_players_by_club",
      "list_competitions",
    ]) {
      expect(names).toContain(expected);
    }
  });

  it("Scenario: search_matches tool returns formatted text", async () => {
    const res = await client.callTool({
      name: "search_matches",
      arguments: { team: "Flamengo", opponent: "Fluminense", limit: 5 },
    });
    const text = (res.content as { type: string; text: string }[])[0].text;
    expect(text).toContain("Flamengo vs Fluminense");
    expect(text).toMatch(/\d{4}-\d{2}-\d{2}/);
  });

  it("Scenario: competition_standings tool computes a table", async () => {
    const res = await client.callTool({
      name: "competition_standings",
      arguments: { season: 2019 },
    });
    const text = (res.content as { type: string; text: string }[])[0].text;
    expect(text).toContain("2019 Brasileirão Série A Standings");
    expect(text).toContain("Champion");
    expect(text).toMatch(/1\. Flamengo-RJ - 90 pts/);
  });

  it("Scenario: search_players tool finds top Brazilians", async () => {
    const res = await client.callTool({
      name: "search_players",
      arguments: { nationality: "Brazil", limit: 3 },
    });
    const text = (res.content as { type: string; text: string }[])[0].text;
    expect(text).toContain("Neymar Jr");
    expect(text).toContain("Overall: 92");
  });

  it("Scenario: team_statistics tool formats a record", async () => {
    const res = await client.callTool({
      name: "team_statistics",
      arguments: { team: "Palmeiras", season: 2023 },
    });
    const text = (res.content as { type: string; text: string }[])[0].text;
    expect(text).toContain("Palmeiras record (2023):");
    expect(text).toMatch(/Matches: \d+/);
    expect(text).toMatch(/Win rate: [\d.]+%/);
  });

  it("Scenario: goals_statistics tool returns averages", async () => {
    const res = await client.callTool({
      name: "goals_statistics",
      arguments: { competition: "Brasileirão" },
    });
    const text = (res.content as { type: string; text: string }[])[0].text;
    expect(text).toMatch(/Average goals per match: 2\.\d+/);
    expect(text).toMatch(/Home win rate: 4\d\.\d%/);
  });

  it("Scenario: head_to_head tool summarizes a rivalry", async () => {
    const res = await client.callTool({
      name: "head_to_head",
      arguments: { team_a: "Palmeiras", team_b: "Santos" },
    });
    const text = (res.content as { type: string; text: string }[])[0].text;
    expect(text).toContain("Head-to-head in dataset");
    expect(text).toMatch(/Palmeiras \d+ wins, Santos \d+ wins, \d+ draws/);
  });

  it("Scenario: unknown team returns a friendly message", async () => {
    const res = await client.callTool({
      name: "search_matches",
      arguments: { team: "Nonexistent FC" },
    });
    const text = (res.content as { type: string; text: string }[])[0].text;
    expect(text).toContain("No matches found");
  });
});
