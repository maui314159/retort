/**
 * BDD Feature: MCP Tools
 * -----------------------------------------------------------------------------
 * Exercises the MCP tool layer in `src/tools.ts` by registering tools on a
 * stub server that captures the registered handlers, then invoking them with
 * sample arguments and asserting the returned text content. This verifies the
 * wiring from tools → query engine → formatters without requiring a live MCP
 * transport.
 */

import { describe, it, expect } from "vitest";
import { dataset } from "./helpers.js";
import { registerTools } from "../src/tools.js";

/** Minimal stub of McpServer that captures registerTool calls. */
type Handler = (args: Record<string, unknown>) => { content: { type: string; text: string }[] };
interface Captured { name: string; description?: string; handler: Handler }

function stubServer(): { tools: Map<string, Captured>; stub: unknown } {
  const tools = new Map<string, Captured>();
  const stub = {
    registerTool(name: string, config: { description?: string }, cb: Handler) {
      tools.set(name, { name, description: config.description, handler: cb });
    },
  };
  return { tools, stub };
}

function callTool(tools: Map<string, Captured>, name: string, args: Record<string, unknown> = {}): string {
  const t = tools.get(name);
  if (!t) throw new Error(`tool not registered: ${name}`);
  const res = t.handler(args);
  return res.content.map((c) => c.text).join("\n");
}

describe("Feature: MCP Tools", () => {
  const ds = dataset();
  const captured = stubServer();
  registerTools(captured.stub as never, ds);

  it("registers all required capability tools", () => {
    const names = [...captured.tools.keys()];
    for (const expected of [
      "search_matches", "team_stats", "head_to_head", "standings",
      "match_statistics", "biggest_wins", "last_match", "search_players",
      "top_players", "brazilian_players_at_brazilian_clubs", "list_competitions",
    ]) {
      expect(names).toContain(expected);
    }
  });

  describe("Scenario: search_matches returns formatted text", () => {
    it("returns matches for a team in a season", () => {
      const out = callTool(captured.tools, "search_matches", { team: "Flamengo", competition: "brasileirao", season: 2019, limit: 3 });
      expect(out).toContain("Matches");
      expect(out).toContain("Flamengo");
    });
  });

  describe("Scenario: team_stats returns a record block", () => {
    it("returns wins/draws/losses/goals", () => {
      const out = callTool(captured.tools, "team_stats", { team: "Flamengo", competition: "brasileirao", season: 2019 });
      expect(out).toContain("Wins: 28");
      expect(out).toContain("Losses: 4");
      expect(out).toContain("Win rate:");
    });
  });

  describe("Scenario: standings returns a ranked table with a champion", () => {
    it("crowns Flamengo for 2019", () => {
      const out = callTool(captured.tools, "standings", { competition: "brasileirao", season: 2019 });
      expect(out).toContain("Flamengo-RJ");
      expect(out).toContain("Champion: Flamengo-RJ (90 pts)");
    });
  });

  describe("Scenario: list_competitions enumerates loaded datasets", () => {
    it("lists all sources and the player count", () => {
      const out = callTool(captured.tools, "list_competitions", {});
      expect(out).toContain("Loaded competitions:");
      expect(out).toContain("Brasileirão Serie A");
      expect(out).toContain("Copa Libertadores");
      expect(out).toContain("Players: 18207");
    });
  });

  describe("Scenario: head_to_head returns a summary", () => {
    it("reports wins for both teams and a draw count", () => {
      const out = callTool(captured.tools, "head_to_head", { team1: "Flamengo", team2: "Fluminense", competition: "brasileirao" });
      expect(out).toContain("head-to-head");
      expect(out).toMatch(/wins,/);
    });
  });

  describe("Scenario: search_players returns ranked players", () => {
    it("returns Brazilian players sorted by overall", () => {
      const out = callTool(captured.tools, "search_players", { nationality: "Brazil", limit: 3 });
      expect(out).toContain("Players");
      expect(out).toContain("Nationality: Brazil");
    });
  });
});
