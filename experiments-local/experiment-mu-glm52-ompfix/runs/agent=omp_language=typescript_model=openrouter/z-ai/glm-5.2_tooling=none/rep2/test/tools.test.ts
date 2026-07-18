/**
 * Brazilian Soccer MCP Server — MCP tool dispatch tests
 * ----------------------------------------------------
 * Context block:
 *   Verifies the tool layer's input-schema handling and result serialisation
 *   by invoking the internal `handleTool` dispatcher directly (no stdio), so
 *   tests stay fast and deterministic.
 */

import { describe, expect, it } from "vitest";
import { buildDataset } from "./fixtures.js";
import { toolDefinitions } from "../src/tools.js";

// Re-implement handleTool via the exported factory to avoid importing the
// stdio entrypoint (which calls main()).
import { createDispatcher } from "../src/tools.js";

describe("MCP tool layer", () => {
  const ds = buildDataset();
  const dispatch = createDispatcher(ds);

  it("exposes all nine required tools", () => {
    const names = toolDefinitions().map((t) => t.name);
    expect(names).toContain("search_matches");
    expect(names).toContain("team_statistics");
    expect(names).toContain("head_to_head");
    expect(names).toContain("search_players");
    expect(names).toContain("competition_standings");
    expect(names).toContain("goal_statistics");
    expect(names).toContain("best_record");
    expect(names).toContain("top_scoring_teams");
    expect(names).toContain("resolve_team");
    expect(names.length).toBe(9);
  });

  it("search_matches returns JSON-serialisable results", () => {
    const result = dispatch("search_matches", { team: "Flamengo", season: 2023 });
    expect(Array.isArray(result)).toBe(true);
    expect((result as unknown[]).length).toBe(3);
    // Round-trip through JSON to prove serialisability.
    expect(() => JSON.stringify(result)).not.toThrow();
  });

  it("team_statistics returns a stats object", () => {
    const result = dispatch("team_statistics", { team: "Palmeiras", season: 2023 }) as Record<string, unknown>;
    expect(result.matches).toBe(3);
    expect(result.wins).toBe(1);
  });

  it("head_to_head returns an h2h object", () => {
    const result = dispatch("head_to_head", { teamA: "Flamengo", teamB: "Fluminense" }) as Record<string, unknown>;
    expect(result.matches).toBe(2);
  });

  it("search_players returns sorted players", () => {
    const result = dispatch("search_players", { nationality: "Brazil", sortBy: "overall", limit: 2 }) as Array<{ name: string }>;
    expect(result.length).toBe(2);
    expect(result[0].name).toBe("Neymar Jr");
  });

  it("competition_standings returns a sorted table", () => {
    const result = dispatch("competition_standings", { competition: "Brasileirão", season: 2023 }) as Array<{ position: number }>;
    expect(result.map((r) => r.position)).toEqual([1, 2, 3, 4, 5]);
  });

  it("resolve_team normalises a name", () => {
    const result = dispatch("resolve_team", { name: "Flamengo-RJ" }) as Record<string, unknown>;
    expect(result.canonicalKey).toBe("flamengo");
  });

  it("returns an error object for an unknown tool", () => {
    const result = dispatch("nope", {}) as Record<string, unknown>;
    expect(result.error).toContain("Unknown tool");
  });
});
