/**
 * Context
 * -------
 * End-to-end MCP test: a real Client talks to the real server over a linked
 * in-memory transport pair. Verifies the tools are advertised and that each
 * returns spec-shaped text content for representative questions. This exercises
 * the JSON-RPC tool layer, not just the underlying graph.
 */

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { beforeAll, describe, expect, it } from "vitest";

import { createServer } from "../src/server.js";
import { SoccerGraph } from "../src/service.js";

let client: Client;

/** Call a tool and return its concatenated text content. */
async function callText(name: string, args: Record<string, unknown>): Promise<string> {
  const result = (await client.callTool({ name, arguments: args })) as {
    content: { type: string; text?: string }[];
  };
  return result.content
    .filter((c) => c.type === "text")
    .map((c) => c.text ?? "")
    .join("\n");
}

beforeAll(async () => {
  const graph = SoccerGraph.load();
  const server = createServer(graph);
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  client = new Client({ name: "test-client", version: "1.0.0" });
  await Promise.all([server.connect(serverTransport), client.connect(clientTransport)]);
});

describe("Feature: MCP tool surface", () => {
  it("Scenario: the server advertises all capability tools", async () => {
    const { tools } = await client.listTools();
    const names = new Set(tools.map((t) => t.name));
    for (const expected of [
      "find_matches",
      "team_record",
      "head_to_head",
      "find_players",
      "standings",
      "competition_stats",
      "biggest_wins",
    ]) {
      expect(names).toContain(expected);
    }
  });
});

describe("Feature: Answering sample questions over MCP", () => {
  it("Scenario: 'Show me all Flamengo vs Fluminense matches' includes a head-to-head summary", async () => {
    const out = await callText("find_matches", { team: "Flamengo", opponent: "Fluminense" });
    expect(out).toMatch(/Flamengo .* Fluminense|Fluminense .* Flamengo/);
    expect(out).toContain("Head-to-head");
    expect(out).toMatch(/Flamengo \d+ wins/);
  });

  it("Scenario: 'Who won the 2019 Brasileirão?' ranks Flamengo as champion", async () => {
    const out = await callText("standings", { competition: "Serie A", season: 2019 });
    expect(out).toContain("1. Flamengo-RJ - 90 pts");
    expect(out).toContain("Champion");
  });

  it("Scenario: 'Find Brazilian players' returns Neymar at the top", async () => {
    const out = await callText("find_players", { nationality: "Brazil", limit: 5 });
    expect(out).toMatch(/827 total/);
    expect(out).toContain("1. Neymar Jr");
  });

  it("Scenario: 'Average goals per match in the Brasileirão' returns a stat block", async () => {
    const out = await callText("competition_stats", { competition: "Brasileirão", season: 2019 });
    expect(out).toContain("Average goals per match:");
    expect(out).toContain("Matches: 380");
  });

  it("Scenario: 'Flamengo 2019 record' reports the title-winning numbers", async () => {
    const out = await callText("team_record", { team: "Flamengo", competition: "Serie A", season: 2019 });
    expect(out).toContain("Wins: 28, Draws: 6, Losses: 4");
    expect(out).toContain("Win rate: 73.7%");
  });

  it("Scenario: an unknown competition yields a helpful error message", async () => {
    const out = await callText("standings", { competition: "Premier League", season: 2019 });
    expect(out).toMatch(/Unknown competition/);
  });

  it("Scenario: 'Biggest wins' lists large-margin victories", async () => {
    const out = await callText("biggest_wins", { limit: 5 });
    expect(out).toContain("Biggest wins");
    expect(out.split("\n").filter((l) => l.startsWith("- ")).length).toBe(5);
  });
});
