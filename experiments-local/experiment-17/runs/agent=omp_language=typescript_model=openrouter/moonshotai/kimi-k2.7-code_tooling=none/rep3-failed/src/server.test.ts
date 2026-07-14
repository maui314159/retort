import {
  describe, it, expect, beforeAll, afterAll,
} from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import {
  CallToolResultSchema,
  type JSONRPCMessage,
} from "@modelcontextprotocol/sdk/types.js";
import type { Transport } from "@modelcontextprotocol/sdk/shared/transport.js";
import { SoccerRepository } from "./loaders.js";
import { createServer } from "./server.js";


function firstText(result: unknown): string {
  const content = (result as { content?: Array<{ text?: string }> }).content;
  if (!content || content.length === 0 || typeof content[0].text !== "string") {
    throw new Error("Expected text content");
  }
  return content[0].text;
}

class InMemoryTransport implements Transport {
  other?: InMemoryTransport;
  onmessage?: (message: JSONRPCMessage, extra?: unknown) => void;
  onclose?: () => void;
  onerror?: (error: Error) => void;
  sessionId = "test-session";

  async start(): Promise<void> {}

  async send(message: JSONRPCMessage): Promise<void> {
    this.other?.onmessage?.(message);
  }

  async close(): Promise<void> {
    this.onclose?.();
  }

  setProtocolVersion(): void {}
}

function linkedPair(): [InMemoryTransport, InMemoryTransport] {
  const a = new InMemoryTransport();
  const b = new InMemoryTransport();
  a.other = b;
  b.other = a;
  return [a, b];
}

describe("Feature: MCP Server Tools", () => {
  let client: Client;
  let cleanup: () => Promise<void>;

  beforeAll(async () => {
    const repo = SoccerRepository.load();
    const { server } = createServer({ repository: repo });
    const [clientTransport, serverTransport] = linkedPair();
    client = new Client({ name: "test-client", version: "1.0.0" });

    await Promise.all([server.connect(serverTransport), client.connect(clientTransport)]);

    cleanup = async () => {
      await client.close();
      await server.close();
    };
  });

  afterAll(async () => {
    await cleanup();
  });

  it("Given the server is running, when I list tools, then I should see Brazilian soccer tools", async () => {
    const result = await client.listTools();
    const names = result.tools.map((t) => t.name);
    expect(names).toContain("search_matches");
    expect(names).toContain("get_team_stats");
    expect(names).toContain("search_players");
    expect(names).toContain("get_standings");
    expect(names).toContain("get_head_to_head");
  });

  it("Given the server is running, when I call search_matches for Flamengo vs Fluminense, then I should receive match data", async () => {
    const result = await client.callTool(
      { name: "search_matches", arguments: { team: "Flamengo", opponent: "Fluminense", limit: 5 } },
      CallToolResultSchema,
    );
    expect(result.content).toHaveLength(1);
    const text = result.content[0]!.text;
    const parsed = JSON.parse(text);
    expect(Array.isArray(parsed)).toBe(true);
    expect(parsed.length).toBeGreaterThan(0);
  });

  it("Given the server is running, when I call get_team_stats for Palmeiras in 2023, then I should receive statistics", async () => {
    const result = await client.callTool(
      { name: "get_team_stats", arguments: { team: "Palmeiras", season: 2023 } },
      CallToolResultSchema,
    );
    const text = result.content[0]!.text;
    const stats = JSON.parse(text);
    expect(stats.matches).toBeGreaterThan(0);
    expect(stats.wins + stats.draws + stats.losses).toBe(stats.matches);
  });

  it("Given the server is running, when I call search_players for Brazilian players, then I should receive player records", async () => {
    const result = await client.callTool(
      { name: "search_players", arguments: { nationality: "Brazil", limit: 5 } },
      CallToolResultSchema,
    );
    const players = JSON.parse(firstText(result));
    expect(players.length).toBeGreaterThan(0);
    expect(players[0]).toHaveProperty("overall");
  });

  it("Given the server is running, when I call get_standings for 2019, then I should receive a table", async () => {
    const result = await client.callTool(
      { name: "get_standings", arguments: { season: 2019, competition: "Brasileirão" } },
      CallToolResultSchema,
    );
    const table = JSON.parse(firstText(result));
    expect(table.length).toBeGreaterThan(0);
    expect(table[0]).toHaveProperty("points");
  });
});
