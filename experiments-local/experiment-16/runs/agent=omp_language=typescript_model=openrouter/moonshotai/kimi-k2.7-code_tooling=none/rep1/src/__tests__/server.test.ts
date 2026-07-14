/**
 * Integration tests for the MCP server layer.
 */

import { describe, it, expect, beforeAll } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { loadAllData } from "../loaders.js";
import { SoccerStore } from "../store.js";
import { createSoccerServer } from "../server.js";

describe("MCP server", () => {
  let store: SoccerStore;

  beforeAll(async () => {
    const data = await loadAllData("data/kaggle");
    store = new SoccerStore(data);
  });

  it("exposes tools and answers a match query", async () => {
    const [serverTransport, clientTransport] = InMemoryTransport.createLinkedPair();
    const server = createSoccerServer(store);
    const client = new Client({ name: "test-client", version: "1.0.0" }, { capabilities: {} });

    await server.connect(serverTransport);
    await client.connect(clientTransport);

    const tools = await client.listTools();
    expect(tools.tools.some((t) => t.name === "search_matches")).toBe(true);

    const result = await client.callTool({
      name: "search_matches",
      arguments: { team: "Flamengo", opponent: "Fluminense", limit: 5 },
    });

    const text = (result.content as { type: string; text: string }[])[0].text;
    expect(text).toContain("Flamengo");
    expect(text).toContain("Fluminense");

    await client.close();
    await server.close();
  });

  it("answers a player query", async () => {
    const [serverTransport, clientTransport] = InMemoryTransport.createLinkedPair();
    const server = createSoccerServer(store);
    const client = new Client({ name: "test-client", version: "1.0.0" }, { capabilities: {} });

    await server.connect(serverTransport);
    await client.connect(clientTransport);

    const result = await client.callTool({
      name: "search_players",
      arguments: { nationality: "Brazil", limit: 3 },
    });

    const text = (result.content as { type: string; text: string }[])[0].text;
    expect(text).toContain("Neymar Jr");

    await client.close();
    await server.close();
  });
});
