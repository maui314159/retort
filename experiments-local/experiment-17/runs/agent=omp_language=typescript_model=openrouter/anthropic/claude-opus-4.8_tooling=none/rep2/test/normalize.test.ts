/**
 * Context
 * -------
 * BDD (Given/When/Then) coverage for the normalization primitives: team-name
 * parsing/matching and multi-format date parsing. These guard the trickiest
 * data-quality rules in the spec (state-suffix variants, accents, DD/MM/YYYY).
 */

import { describe, expect, it } from "vitest";

import { foldText, looseMatches, parseDate, parseTeam, teamMatches } from "../src/normalize.js";

describe("Feature: Team name normalization", () => {
  it("Scenario: a hyphenated state suffix is split from the base name", () => {
    // Given a team written with a glued state suffix
    // When parsed
    const t = parseTeam("Palmeiras-SP");
    // Then base and suffix are separated
    expect(t.displayBase).toBe("Palmeiras");
    expect(t.suffix).toBe("sp");
    expect(t.baseKey).toBe("palmeiras");
  });

  it("Scenario: a spaced-dash state suffix is split", () => {
    const t = parseTeam("América - MG");
    expect(t.baseKey).toBe("america");
    expect(t.suffix).toBe("mg");
  });

  it("Scenario: a parenthesized country code is treated as a suffix", () => {
    const t = parseTeam("Nacional (URU)");
    expect(t.baseKey).toBe("nacional");
    expect(t.suffix).toBe("uru");
  });

  it("Scenario: a real word is not amputated as a suffix", () => {
    // "Vasco da Gama-RJ" → base must keep "Gama"
    const t = parseTeam("Vasco da Gama-RJ");
    expect(t.baseKey).toBe("vasco da gama");
    expect(t.suffix).toBe("rj");
  });

  it("Scenario: accents and case are folded for comparison", () => {
    expect(foldText("São Paulo")).toBe("sao paulo");
    expect(foldText("Grêmio")).toBe("gremio");
  });
});

describe("Feature: Team identity matching", () => {
  it("Scenario: a bare query matches the same team with a suffix", () => {
    // Given the unaccented bare name and the suffixed accented form
    // Then they are recognized as the same team
    expect(teamMatches("Sao Paulo", "São Paulo-SP")).toBe(true);
    expect(teamMatches("Flamengo", "Flamengo-RJ")).toBe(true);
  });

  it("Scenario: same base but different state stays distinct when query is suffixed", () => {
    // Atlético-MG must never collapse into Atlético-GO
    expect(teamMatches("Atletico-MG", "Atletico-GO")).toBe(false);
    expect(teamMatches("Atletico-MG", "Atletico-MG")).toBe(true);
  });

  it("Scenario: a partial token does not match", () => {
    expect(teamMatches("Paulo", "São Paulo-SP")).toBe(false);
  });

  it("Scenario: loose matching is accent-insensitive substring", () => {
    expect(looseMatches("flamengo", "Clube de Regatas do Flamengo")).toBe(true);
    expect(looseMatches("gremio", "Grêmio")).toBe(true);
  });
});

describe("Feature: Date parsing", () => {
  it("Scenario: ISO date with time is parsed", () => {
    const d = parseDate("2012-05-19 18:30:00");
    expect(d?.iso).toBe("2012-05-19");
    expect(d?.year).toBe(2012);
  });

  it("Scenario: Brazilian DD/MM/YYYY is parsed", () => {
    const d = parseDate("29/03/2003");
    expect(d?.iso).toBe("2003-03-29");
    expect(d?.year).toBe(2003);
  });

  it("Scenario: blank or unrecognized input yields undefined", () => {
    expect(parseDate("")).toBeUndefined();
    expect(parseDate("not a date")).toBeUndefined();
  });

  it("Scenario: epoch ordering matches calendar ordering", () => {
    const earlier = parseDate("2003-01-01")!;
    const later = parseDate("2019-12-31")!;
    expect(later.epoch).toBeGreaterThan(earlier.epoch);
  });
});
