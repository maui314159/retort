/**
 * BDD Feature: Team Name Normalization & Date Parsing
 * -----------------------------------------------------------------------------
 * Unit-tests the pure normalization/parsing helpers that implement the spec's
 * "Data Quality Notes": team-name variations, accented characters, multiple
 * date formats, and the Atletico-family disambiguation that prevents merging
 * distinct clubs.
 */

import { describe, it, expect } from "vitest";
import { normalizeTeamName, teamKey, teamMatches, sameTeam } from "../src/data/teams.js";
import { parseDate, parseDatetime, inDateRange } from "../src/data/dates.js";

describe("Feature: Team Name Normalization", () => {
  describe("Scenario: Strip state suffix while preserving identity", () => {
    it("keeps the -UF suffix on the canonical name", () => {
      expect(normalizeTeamName("Flamengo-RJ")).toBe("Flamengo-RJ");
      expect(normalizeTeamName("Palmeiras-SP")).toBe("Palmeiras-SP");
    });

    it("appends the state from the state column when the raw name lacks one", () => {
      expect(normalizeTeamName("Flamengo", "RJ")).toBe("Flamengo-RJ");
      expect(normalizeTeamName("Corinthians", "SP")).toBe("Corinthians-SP");
    });

    it("handles the ' - UF' spaced suffix form (Cup dataset)", () => {
      expect(normalizeTeamName("América - MG")).toBe("América-MG");
    });
  });

  describe("Scenario: Disambiguate clubs sharing a base name", () => {
    it("Atletico-MG, Atletico-GO and Atletico-PR are three distinct clubs", () => {
      const mg = normalizeTeamName("Atletico-MG");
      const go = normalizeTeamName("Atletico-GO");
      const pr = normalizeTeamName("Atletico-PR");
      const prH = normalizeTeamName("Athletico-PR");
      expect(mg).not.toBe(go);
      expect(mg).not.toBe(pr);
      expect(go).not.toBe(pr);
      expect(teamKey(mg)).not.toBe(teamKey(go));
      expect(teamKey(mg)).not.toBe(teamKey(pr));
      // Modern "Atletico-PR" and historical "Athletico-PR" unify to the same club.
      expect(pr).toBe("Athletico-PR");
      expect(prH).toBe("Athletico-PR");
      expect(teamKey(pr)).toBe(teamKey(prH));
    });
  });

  describe("Scenario: Strip country parens (Libertadores)", () => {
    it("removes a trailing (COUNTRY) annotation", () => {
      expect(normalizeTeamName("Nacional (URU)")).toBe("Nacional");
      expect(normalizeTeamName("Barcelona-EQU")).toBe("Barcelona-EQU");
    });
  });

  describe("Scenario: Expand long-form club names", () => {
    it("maps full names to their short form", () => {
      expect(normalizeTeamName("Sport Club Corinthians Paulista")).toBe("Corinthians");
      expect(normalizeTeamName("Clube de Regatas do Flamengo", "RJ")).toBe("Flamengo-RJ");
    });
  });

  describe("Scenario: Tolerant matching for queries", () => {
    it("'Flamengo' matches the stored 'Flamengo-RJ'", () => {
      expect(teamMatches("Flamengo", "Flamengo-RJ")).toBe(true);
      expect(sameTeam("Flamengo-RJ", "Flamengo-RJ")).toBe(true);
    });
    it("'Atletico-MG' matches only Atlético-MG, not the other Atleticos", () => {
      expect(teamMatches("Atletico-MG", "Atlético-MG")).toBe(true);
      expect(teamMatches("Atletico-MG", "Atlético-GO")).toBe(false);
      expect(teamMatches("Atletico-MG", "Athletico-PR")).toBe(false);
    });
    it("accents are folded for comparison", () => {
      expect(teamMatches("São Paulo", "Sao Paulo-SP")).toBe(true);
      expect(teamMatches("Gremio", "Grêmio-RS")).toBe(true);
    });
  });
});

describe("Feature: Date Parsing", () => {
  describe("Scenario: Handle multiple date formats", () => {
    it("parses ISO with time", () => {
      expect(parseDatetime("2012-05-19 18:30:00")).toBe("2012-05-19T18:30:00");
      expect(parseDate("2012-05-19 18:30:00")).toBe("2012-05-19");
    });
    it("parses ISO date-only", () => {
      expect(parseDate("2023-09-24")).toBe("2023-09-24");
      expect(parseDatetime("2023-09-24")).toBe("2023-09-24");
    });
    it("parses Brazilian DD/MM/YYYY", () => {
      expect(parseDate("29/03/2003")).toBe("2003-03-29");
      expect(parseDatetime("29/03/2003 15:00")).toBe("2003-03-29T15:00:00");
    });
    it("returns null for NA / empty / unparseable", () => {
      expect(parseDate("NA")).toBeNull();
      expect(parseDate("")).toBeNull();
      expect(parseDatetime("not a date")).toBeNull();
    });
  });

  describe("Scenario: Inclusive date-range check", () => {
    it("accepts dates within [from, to] inclusive", () => {
      expect(inDateRange("2019-06-15", "2019-06-01", "2019-06-30")).toBe(true);
      expect(inDateRange("2019-06-01", "2019-06-01", "2019-06-30")).toBe(true);
      expect(inDateRange("2019-06-30", "2019-06-01", "2019-06-30")).toBe(true);
      expect(inDateRange("2019-05-31", "2019-06-01", "2019-06-30")).toBe(false);
      expect(inDateRange("2019-07-01", "2019-06-01", "2019-06-30")).toBe(false);
      expect(inDateRange(null, "2019-06-01", "2019-06-30")).toBe(false);
    });
  });
});
