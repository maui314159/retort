/**
 * Context
 * -------
 * End-to-end BDD scenarios that drive the MCP server through a real client over
 * an in-memory transport pair. This proves the wired surface works: tools are
 * listed, accept validated arguments, and return both formatted text and the
 * structured payload. It is the closest test to how an LLM client actually uses
 * the server.
 */

import { describe, it, expect, beforeAll } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { buildServer } from "../src/server.js";
import { getStore } from "./fixture.js";

let client: Client;

beforeAll(async () => {
  const store = await getStore();
  const server = buildServer(store);
  const [clientTransport, serverTransport] =
    InMemoryTransport.createLinkedPair();
  await server.connect(serverTransport);
  client = new Client({ name: "test-client", version: "1.0.0" });
  await client.connect(clientTransport);
});

/** Extract the first text block from a tool result. */
function firstText(result: { content: Array<{ type: string; text?: string }> }): string {
  const block = result.content.find((c) => c.type === "text");
  return block?.text ?? "";
}

describe("Feature: MCP server surface", () => {
  it("Scenario: lists all expected tools", async () => {
    const { tools } = await client.listTools();
    const names = tools.map((t) => t.name).sort();
    expect(names).toEqual(
      [
        "biggest_wins",
        "competition_stats",
        "head_to_head",
        "list_competitions",
        "search_matches",
        "search_players",
        "standings",
        "team_stats",
      ].sort(),
    );
  });

  it("Scenario: search_matches returns formatted text and structured data", async () => {
    const res = await client.callTool({
      name: "search_matches",
      arguments: { team: "Flamengo", opponent: "Fluminense", limit: 5 },
    });
    const text = firstText(res as { content: Array<{ type: string; text?: string }> });
    expect(text).toContain("Flamengo");
    expect(text).toContain("Fluminense");
    const structured = res.structuredContent as
      | { data?: { count?: number; matches?: unknown[] } }
      | undefined;
    expect(structured?.data?.count).toBeGreaterThan(0);
    expect(Array.isArray(structured?.data?.matches)).toBe(true);
  });

  it("Scenario: standings tool reports the 2019 champion", async () => {
    const res = await client.callTool({
      name: "standings",
      arguments: { competition: "Brasileirão", season: 2019, limit: 3 },
    });
    const text = firstText(res as { content: Array<{ type: string; text?: string }> });
    expect(text).toContain("Flamengo");
    expect(text).toContain("Champion");
  });

  it("Scenario: search_players filters by nationality", async () => {
    const res = await client.callTool({
      name: "search_players",
      arguments: { nationality: "Brazil", limit: 3 },
    });
    const structured = res.structuredContent as
      | { data?: { count?: number } }
      | undefined;
    expect(structured?.data?.count).toBeGreaterThan(500);
  });

  it("Scenario: invalid arguments are reported as a tool error", async () => {
    const res = await client.callTool({
      name: "standings",
      arguments: { competition: "Not A Competition", season: 2019 },
    });
    // The SDK surfaces schema-validation failures as an isError result whose
    // text explains the problem, rather than throwing.
    expect(res.isError).toBe(true);
    const text = firstText(res as { content: Array<{ type: string; text?: string }> });
    expect(text).toContain("validation");
  });

  it("Scenario: list_competitions enumerates the loaded competitions", async () => {
    const res = await client.callTool({
      name: "list_competitions",
      arguments: {},
    });
    const text = firstText(res as { content: Array<{ type: string; text?: string }> });
    expect(text).toContain("Brasileirão");
    expect(text).toContain("Libertadores");
  });
});
