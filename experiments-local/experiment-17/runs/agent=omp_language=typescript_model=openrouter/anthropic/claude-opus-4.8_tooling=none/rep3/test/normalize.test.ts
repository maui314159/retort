/**
 * Context
 * -------
 * BDD (Given/When/Then) tests for the name/date normalization layer
 * (src/normalize.ts). These guard the rules that everything else depends on:
 * distinct clubs sharing a base name must stay distinct, cross-spelling lookups
 * must still match, and the three dataset date formats must unify to ISO.
 */

import { describe, it, expect } from "vitest";
import {
  cleanDisplayName,
  normalizeTeamKey,
  parseDate,
  stripAccents,
  teamMatches,
} from "../src/normalize.js";

describe("Feature: team name normalization", () => {
  describe("Scenario: accented Portuguese names are folded for matching", () => {
    it("Given an accented name, When normalized, Then accents are removed", () => {
      // Given a club written with Portuguese diacritics
      const name = "São Paulo";
      // When the matching key is built
      const key = normalizeTeamKey(name);
      // Then it is accent-folded and lowercased
      expect(key).toBe("sao paulo");
      expect(stripAccents("Grêmio")).toBe("Gremio");
    });
  });

  describe("Scenario: clubs sharing a base name stay distinct", () => {
    it("Given Atletico-MG and Atletico-PR, When keyed, Then keys differ", () => {
      // Given two distinct clubs that share the base word "Atletico"
      const mg = normalizeTeamKey("Atlético-MG");
      const pr = normalizeTeamKey("Athletico-PR");
      // When their keys are compared
      // Then the state suffix keeps them apart
      expect(mg).toBe("atletico mg");
      expect(pr).toBe("athletico pr");
      expect(mg).not.toBe(pr);
    });
  });

  describe("Scenario: cross-spelling lookups still match", () => {
    it("Given 'Flamengo', When compared to 'Flamengo-RJ', Then it matches", () => {
      // Given the suffixed dataset spelling and a bare user query
      // When fuzzy matching runs
      // Then they are recognized as the same club
      expect(teamMatches("Flamengo-RJ", "Flamengo")).toBe(true);
      expect(teamMatches("Palmeiras-SP", "palmeiras")).toBe(true);
    });

    it("Given 'Santos', When compared to 'Santo André', Then it does NOT match", () => {
      // Given a substring that is not a whole-token match
      // When fuzzy matching runs
      // Then the partial overlap is rejected
      expect(teamMatches("Santo André", "Santos")).toBe(false);
    });

    it("Given an empty club name, When matched, Then it returns false (no hang)", () => {
      // Regression: empty needle must not infinite-loop.
      expect(teamMatches("", "Flamengo")).toBe(false);
      expect(teamMatches("Flamengo", "")).toBe(false);
    });
  });

  describe("Scenario: display names keep their identifying suffix", () => {
    it("Given a suffixed name, When cleaned for display, Then suffix is kept", () => {
      // Given a name with a state suffix
      // When cleaned for display
      // Then only whitespace is normalized; the suffix remains
      expect(cleanDisplayName("  Flamengo-RJ ")).toBe("Flamengo-RJ");
    });
  });
});

describe("Feature: date parsing", () => {
  describe("Scenario: the three dataset date formats unify to ISO", () => {
    it("Given an ISO datetime, When parsed, Then the date part is returned", () => {
      expect(parseDate("2012-05-19 18:30:00")).toBe("2012-05-19");
    });
    it("Given an ISO date, When parsed, Then it is returned unchanged", () => {
      expect(parseDate("2023-09-24")).toBe("2023-09-24");
    });
    it("Given a Brazilian DD/MM/YYYY date, When parsed, Then it becomes ISO", () => {
      expect(parseDate("29/03/2003")).toBe("2003-03-29");
    });
    it("Given an unparseable or empty value, When parsed, Then undefined", () => {
      expect(parseDate("")).toBeUndefined();
      expect(parseDate(undefined)).toBeUndefined();
      expect(parseDate("not a date")).toBeUndefined();
    });
  });
});
