/**
 * Feature: MCP protocol surface
 *
 * The server exposes the query engine as MCP tools and resources over the
 * Model Context Protocol. Tested end-to-end over an in-memory transport.
 */

import { beforeAll, describe, expect, it } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { givenDataLoaded } from "./helpers.js";
import { createServer } from "../src/server.js";

let client: Client;

beforeAll(async () => {
  const ctx = givenDataLoaded();
  const server = createServer(ctx);
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  client = new Client({ name: "test-client", version: "1.0.0" });
  await Promise.all([
    server.connect(serverTransport),
    client.connect(clientTransport),
  ]);
});

function parseJson(result: Awaited<ReturnType<Client["callTool"]>>): unknown {
  const text = (result.content as { type: string; text: string }[])[0].text;
  return JSON.parse(text);
}

describe("Feature: MCP server tools", () => {
  it("Scenario: The server lists all expected tools", async () => {
    // When the client lists tools
    const { tools } = await client.listTools();
    const names = tools.map((t) => t.name);
    // Then all query categories are covered
    for (const expected of [
      "dataset_overview",
      "find_matches",
      "head_to_head",
      "team_record",
      "team_competitions",
      "league_standings",
      "cup_finals",
      "search_players",
      "top_players",
      "players_by_club_summary",
      "competition_stats",
      "biggest_wins",
      "best_home_records",
      "best_away_records",
      "top_scoring_teams",
    ]) {
      expect(names).toContain(expected);
    }
    // And every tool has a description and schema
    for (const t of tools) {
      expect(t.description).toBeTruthy();
      expect(t.inputSchema).toBeTruthy();
    }
  });

  it("Scenario: dataset_overview returns the loaded data summary", async () => {
    const result = await client.callTool({ name: "dataset_overview", arguments: {} });
    const ov = parseJson(result) as { uniqueMatches: number; players: number };
    expect(ov.uniqueMatches).toBeGreaterThan(16000);
    expect(ov.players).toBe(18207);
  });

  it("Scenario: find_matches answers 'Flamengo vs Fluminense'", async () => {
    const result = await client.callTool({
      name: "find_matches",
      arguments: { team: "Flamengo", opponent: "Fluminense" },
    });
    const data = parseJson(result) as { count: number; matches: { home: string; away: string; date: string; competition: string }[] };
    expect(data.count).toBeGreaterThan(10);
    for (const m of data.matches) {
      expect(m.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(m.competition).toBeTruthy();
    }
  });

  it("Scenario: league_standings answers 'Who won the 2019 Brasileirão?'", async () => {
    const result = await client.callTool({
      name: "league_standings",
      arguments: { season: 2019 },
    });
    const table = parseJson(result) as { team: string; points: number; note?: string }[];
    expect(table[0].team).toBe("Flamengo");
    expect(table[0].points).toBe(90);
    expect(table[0].note).toContain("Champion");
  });

  it("Scenario: head_to_head answers 'Compare Palmeiras and Santos'", async () => {
    const result = await client.callTool({
      name: "head_to_head",
      arguments: { teamA: "Palmeiras", teamB: "Santos" },
    });
    const data = parseJson(result) as { total: number; winsA: number; winsB: number; draws: number };
    expect(data.total).toBeGreaterThan(20);
    expect(data.winsA + data.winsB + data.draws).toBeGreaterThan(0);
  });

  it("Scenario: search_players answers 'Who is Neymar?'", async () => {
    const result = await client.callTool({
      name: "search_players",
      arguments: { name: "Neymar" },
    });
    const data = parseJson(result) as { players: { name: string; overall: number; club: string }[] };
    const neymar = data.players.find((p) => p.name === "Neymar Jr");
    expect(neymar).toBeDefined();
    expect(neymar!.overall).toBe(92);
  });

  it("Scenario: top_players answers 'Who are the top Brazilian players?'", async () => {
    const result = await client.callTool({
      name: "top_players",
      arguments: { nationality: "Brazil", limit: 5 },
    });
    const data = parseJson(result) as { players: { name: string; overall: number }[] };
    expect(data.players[0].name).toBe("Neymar Jr");
    expect(data.players.length).toBe(5);
  });

  it("Scenario: team_record answers 'Corinthians home record in 2022'", async () => {
    const result = await client.callTool({
      name: "team_record",
      arguments: { team: "Corinthians", season: 2022, competition: "Brasileirão", venue: "home" },
    });
    const rec = parseJson(result) as { matches: number; wins: number; draws: number; losses: number };
    expect(rec.matches).toBe(19);
    expect(rec.wins + rec.draws + rec.losses).toBe(19);
  });

  it("Scenario: competition_stats answers 'average goals per match'", async () => {
    const result = await client.callTool({
      name: "competition_stats",
      arguments: { competition: "Brasileirão Série A" },
    });
    const stats = parseJson(result) as { averageGoalsPerMatch: number; homeWinRate: number };
    expect(stats.averageGoalsPerMatch).toBeGreaterThan(2);
    expect(stats.homeWinRate).toBeGreaterThan(40);
  });

  it("Scenario: an unknown season returns a friendly error", async () => {
    const result = await client.callTool({
      name: "league_standings",
      arguments: { season: 1950 },
    });
    expect(result.isError).toBe(true);
  });

  it("Scenario: the overview resource is readable", async () => {
    const { resources } = await client.listResources();
    expect(resources.map((r) => r.uri)).toContain("soccer://overview");
    const content = await client.readResource({ uri: "soccer://overview" });
    const parsed = JSON.parse(content.contents[0].text as string) as { players: number };
    expect(parsed.players).toBe(18207);
  });
});
