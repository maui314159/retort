/**
 * Brazilian Soccer MCP Server — loader & normaliser integration tests
 * ------------------------------------------------------------------
 * Context block:
 *   Verifies that the real Kaggle CSV files load correctly and that team-name
 *   normalisation produces consistent canonical keys across files. These tests
 *   guard the data-quality requirements in the spec (team name variations,
 *   date formats, UTF-8 encoding).
 */

import { describe, expect, it } from "vitest";
import { resolve } from "node:path";
import { loadAll } from "../src/loader.js";
import { canonicalTeamKey, deaccent, teamKey } from "../src/normalizer.js";
import { parseDate, parseNum } from "../src/dates.js";

const dataDir = resolve(process.cwd(), "data", "kaggle");

describe("Normalisation helpers", () => {
  it("keys keep state suffix; canonicalTeamKey collapses variants", () => {
    // teamKey preserves the suffix so disambiguation is possible...
    expect(teamKey("Palmeiras-SP")).toBe("palmeiras_sp");
    expect(teamKey("Flamengo - RJ")).toBe("flamengo_rj");
    expect(teamKey("São Paulo")).toBe("sao_paulo");
    // ...and canonicalTeamKey collapses suffixed forms onto a bare key.
    expect(canonicalTeamKey("Palmeiras-SP")).toBe("palmeiras");
    expect(canonicalTeamKey("Flamengo - RJ")).toBe("flamengo");
    expect(canonicalTeamKey("Flamengo")).toBe("flamengo");
  });

  it("deaccent removes diacritics", () => {
    expect(deaccent("São Paulo Grêmio Avaí")).toBe("sao paulo gremio avai");
  });

  it("collapses Athletico/Atletico variants via aliases", () => {
    expect(canonicalTeamKey("Atletico-PR")).toBe("athletico_pr");
    expect(canonicalTeamKey("Athletico-PR")).toBe("athletico_pr");
  });
});

describe("Date parsing", () => {
  it("parses ISO with time", () => {
    const d = parseDate("2012-05-19 18:30:00");
    expect(d).not.toBeNull();
    expect(d!.getUTCFullYear()).toBe(2012);
  });

  it("parses Brazilian DD/MM/YYYY", () => {
    const d = parseDate("29/03/2003");
    expect(d).not.toBeNull();
    expect(d!.getUTCMonth()).toBe(2);
    expect(d!.getUTCDate()).toBe(29);
  });

  it("parses ISO date only", () => {
    const d = parseDate("2023-09-24");
    expect(d).not.toBeNull();
    expect(d!.getUTCFullYear()).toBe(2023);
  });

  it("returns null for NA/invalid", () => {
    expect(parseDate("NA")).toBeNull();
    expect(parseDate("")).toBeNull();
  });
});

describe("Number parsing", () => {
  it("returns null for NA", () => {
    expect(parseNum("NA")).toBeNull();
    expect(parseNum("-")).toBeNull();
  });
  it("parses numbers", () => {
    expect(parseNum("3")).toBe(3);
    expect(parseNum("1.5")).toBe(1.5);
  });
});

describe("Real data loading", () => {
  const ds = loadAll(dataDir);

  it("loads matches from all five match files", () => {
    expect(ds.matches.length).toBeGreaterThan(20000);
    const sources = new Set(ds.matches.map((m) => m.source));
    expect(sources.size).toBe(5);
  });

  it("loads FIFA players", () => {
    expect(ds.players.length).toBeGreaterThan(10000);
  });

  it("normalises Flamengo consistently across files", () => {
    const flamengoMatches = ds.matches.filter(
      (m) => m.homeTeam === "flamengo" || m.awayTeam === "flamengo",
    );
    expect(flamengoMatches.length).toBeGreaterThan(100);
  });

  it("all matches have a non-empty home and away team key", () => {
    const bad = ds.matches.filter((m) => !m.homeTeam || !m.awayTeam);
    expect(bad.length).toBe(0);
  });
});
