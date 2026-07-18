/**
 * brazilian-soccer-mcp — BDD tests for normalisation
 *
 * Context block
 * ============
 * See src/types.ts for the top-level project context block.
 *
 * Behaviour-driven scenarios (Given/When/Then) covering the team-name and
 * date normalisation rules that let the query engine match across datasets
 * with inconsistent naming conventions.
 */

import { describe, it, expect } from "vitest";
import {
  normalizeTeam,
  normalizeDate,
  parseScore,
  parseSeason,
  teamsMatch,
  teamKey,
} from "../src/normalize.js";

describe("Feature: Team name normalisation", () => {
  it("Scenario: strips a state suffix like Palmeiras-SP", () => {
    // Given a team name with a state suffix
    // When normalised
    // Then the suffix is removed but the name is preserved
    expect(normalizeTeam("Palmeiras-SP")).toBe("Palmeiras");
  });

  it("Scenario: strips a spaced dash state like América - MG", () => {
    expect(normalizeTeam("América - MG")).toBe("América");
  });

  it("Scenario: strips a parenthetical disambiguator", () => {
    expect(normalizeTeam("Nacional (URU)")).toBe("Nacional");
  });

  it("Scenario: preserves accented characters (São Paulo, Grêmio, Avaí)", () => {
    expect(normalizeTeam("São Paulo-SP")).toBe("São Paulo");
    expect(normalizeTeam("Grêmio-RS")).toBe("Grêmio");
    expect(normalizeTeam("Avaí-SC")).toBe("Avaí");
  });

  it("Scenario: trims and collapses internal whitespace", () => {
    expect(normalizeTeam("  Sport   Club   Corinthians  ")).toBe(
      "Sport Club Corinthians",
    );
  });

  it("Scenario: tolerates null/empty input", () => {
    expect(normalizeTeam(null)).toBe("");
    expect(normalizeTeam("")).toBe("");
  });
});

describe("Feature: Tolerant team matching", () => {
  it("Scenario: matches identical names", () => {
    expect(teamsMatch("Flamengo", "Flamengo")).toBe(true);
  });

  it("Scenario: matches case-insensitively", () => {
    expect(teamsMatch("flamengo", "FLAMENGO")).toBe(true);
  });

  it("Scenario: matches ignoring accents", () => {
    expect(teamsMatch("São Paulo", "Sao Paulo")).toBe(true);
  });

  it("Scenario: matches a short canonical name inside a longer full name", () => {
    expect(teamsMatch("São Paulo", "São Paulo FC")).toBe(true);
  });

  it("Scenario: does not match very short names against arbitrary strings", () => {
    expect(teamsMatch("SP", "Sport Club Corinthians Paulista")).toBe(false);
  });
});

describe("Feature: Date normalisation", () => {
  it("Scenario: ISO date passes through", () => {
    expect(normalizeDate("2023-09-24")).toBe("2023-09-24");
  });

  it("Scenario: ISO datetime is reduced to its date", () => {
    expect(normalizeDate("2012-05-19 18:30:00")).toBe("2012-05-19");
  });

  it("Scenario: Brazilian DD/MM/YYYY is reordered to ISO", () => {
    expect(normalizeDate("29/03/2003")).toBe("2003-03-29");
  });

  it("Scenario: unparseable input yields null", () => {
    expect(normalizeDate("not a date")).toBeNull();
    expect(normalizeDate(null)).toBeNull();
  });
});

describe("Feature: Score and season parsing", () => {
  it("Scenario: numeric scores parse", () => {
    expect(parseScore("2")).toBe(2);
    expect(parseScore(2)).toBe(2);
  });

  it("Scenario: blank or non-numeric scores yield null", () => {
    expect(parseScore("")).toBeNull();
    expect(parseScore(null)).toBeNull();
    expect(parseScore("N/A")).toBeNull();
  });

  it("Scenario: season year parses from a 4-digit string", () => {
    expect(parseSeason("2023")).toBe(2023);
    expect(parseSeason("2012-05-19 18:30:00")).toBe(2012);
  });

  it("Scenario: season key folds accents for tolerant comparison", () => {
    expect(teamKey("São Paulo")).toBe("sao paulo");
  });
});
