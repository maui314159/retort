/**
 * Context
 * -------
 * End-to-end BDD tests for the MCP server (src/server.ts). A real MCP `Client`
 * is connected to the server over an in-memory transport pair, so these
 * exercise the full path: tool registration, Zod input validation, query
 * execution, and both the text and `structuredContent` responses — exactly what
 * an LLM host would see.
 */

import { beforeAll, describe, it, expect } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { loadSoccerData } from "../src/loader.js";
import { createServer } from "../src/server.js";

let client: Client;

beforeAll(async () => {
  const data = loadSoccerData();
  const server = createServer(data);
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  client = new Client({ name: "test-client", version: "1.0.0" });
  await Promise.all([
    server.connect(serverTransport),
    client.connect(clientTransport),
  ]);
});

interface StructuredResult {
  content: { type: string; text?: string }[];
  structuredContent?: Record<string, unknown>;
  isError?: boolean;
}

async function call(name: string, args: Record<string, unknown>): Promise<StructuredResult> {
  return (await client.callTool({ name, arguments: args })) as unknown as StructuredResult;
}

describe("Feature: MCP server tool surface", () => {
  describe("Scenario: tools are advertised", () => {
    it("Given a connected client, When listing tools, Then the soccer tools are present", async () => {
      // Given a connected MCP client
      // When the tool list is requested
      const { tools } = await client.listTools();
      const names = tools.map((t) => t.name);
      // Then the core capabilities are exposed
      expect(names).toEqual(
        expect.arrayContaining([
          "search_matches",
          "head_to_head",
          "team_record",
          "league_standings",
          "search_players",
          "club_squads",
          "competition_stats",
          "biggest_wins",
          "dataset_overview",
        ])
      );
    });
  });

  describe("Scenario: search matches between two clubs", () => {
    it("Given the server, When calling search_matches, Then formatted text and structured data return", async () => {
      // When I call search_matches for the Fla-Flu derby
      const res = await call("search_matches", { team: "Flamengo", opponent: "Fluminense", limit: 5 });
      // Then I get human-readable text mentioning both clubs
      expect(res.content[0].text).toMatch(/Flamengo/);
      expect(res.content[0].text).toMatch(/Fluminense/);
      // And a structured payload with a total and the match rows
      const structured = res.structuredContent as { total: number; matches: unknown[] };
      expect(structured.total).toBeGreaterThan(0);
      expect(structured.matches.length).toBeLessThanOrEqual(5);
    });
  });

  describe("Scenario: league standings via the server", () => {
    it("Given 2019, When calling league_standings, Then Flamengo lead the table", async () => {
      // When I request the 2019 Série A standings
      const res = await call("league_standings", {
        competition: "Brasileirão Série A",
        season: 2019,
      });
      // Then the rendered table names Flamengo as champion
      expect(res.content[0].text).toMatch(/Champion/);
      const structured = res.structuredContent as { standings: { team: string; points: number }[] };
      expect(structured.standings[0].team).toMatch(/Flamengo/);
      expect(structured.standings[0].points).toBe(90);
    });
  });

  describe("Scenario: player search via the server", () => {
    it("Given a name query, When calling search_players, Then Neymar is returned", async () => {
      const res = await call("search_players", { name: "Neymar", limit: 3 });
      const structured = res.structuredContent as { players: { name: string; overall: number }[] };
      expect(structured.players[0].name).toMatch(/Neymar/);
      expect(structured.players[0].overall).toBe(92);
    });
  });

  describe("Scenario: invalid input is rejected by schema validation", () => {
    it("Given a bad competition enum, When calling league_standings, Then the call errors", async () => {
      // Then the SDK reports a validation error rather than running the handler
      const res = await call("league_standings", {
        competition: "Premier League",
        season: 2019,
      });
      expect(res.isError).toBe(true);
      expect(res.content[0].text).toMatch(/validation error/i);
    });
  });

  describe("Scenario: dataset overview", () => {
    it("Given the server, When calling dataset_overview, Then counts and seasons are reported", async () => {
      const res = await call("dataset_overview", {});
      const structured = res.structuredContent as {
        matchCount: number;
        playerCount: number;
        competitions: { competition: string; seasons: number[] }[];
      };
      expect(structured.matchCount).toBeGreaterThan(10_000);
      expect(structured.playerCount).toBe(18_207);
      expect(structured.competitions.length).toBeGreaterThan(0);
    });
  });
});
