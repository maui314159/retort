/**
 * Feature: Data normalization
 *   The datasets use different naming conventions and date formats;
 *   the implementation normalizes them for consistent matching.
 */
import { describe, it, expect } from "vitest";
import {
  canonicalTeamKey,
  displayTeamName,
  foldAccents,
  parseDate,
  teamMatches,
} from "../src/normalize.js";

describe("Feature: Team name normalization", () => {
  it("Scenario: state suffixes are stripped regardless of spacing", () => {
    // Given names with state suffixes in different formats
    // When normalized
    // Then they produce the same canonical key
    expect(canonicalTeamKey("Palmeiras-SP")).toBe(canonicalTeamKey("Palmeiras"));
    expect(canonicalTeamKey("Palmeiras - SP")).toBe(canonicalTeamKey("Palmeiras"));
    expect(canonicalTeamKey("Flamengo-RJ")).toBe(canonicalTeamKey("flamengo"));
    expect(canonicalTeamKey("América - MG")).toBe(canonicalTeamKey("América-MG"));
  });

  it("Scenario: accented names match their unaccented forms", () => {
    // Given Brazilian Portuguese special characters (São Paulo, Grêmio, Avaí)
    expect(teamMatches("São Paulo - SP", "Sao Paulo")).toBe(true);
    expect(teamMatches("Grêmio - RS", "Gremio")).toBe(true);
    expect(teamMatches("Avaí - SC", "Avai")).toBe(true);
  });

  it("Scenario: historical name changes are aliased", () => {
    // Given Atlético-PR (old) and Athletico-PR / Athletico Paranaense (new)
    expect(canonicalTeamKey("Atlético - PR")).toBe(canonicalTeamKey("Athletico-PR"));
    expect(canonicalTeamKey("Atlético Paranaense - PR")).toBe(
      canonicalTeamKey("Athletico Paranaense - PR"),
    );
  });

  it("Scenario: foreign club country tags are stripped", () => {
    expect(canonicalTeamKey("Nacional (URU)")).toBe(canonicalTeamKey("Nacional"));
    expect(canonicalTeamKey("Barcelona-EQU")).toBe("barcelona");
  });

  it("Scenario: long legal names still match short queries", () => {
    // Given a full legal name from Copa do Brasil
    expect(teamMatches("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "Boavista")).toBe(true);
  });

  it("Scenario: display names drop suffixes but keep accents", () => {
    expect(displayTeamName("Palmeiras-SP")).toBe("Palmeiras");
    expect(displayTeamName("São Paulo - SP")).toBe("São Paulo");
    expect(displayTeamName("Grêmio - RS")).toBe("Grêmio");
  });

  it("Scenario: distinct teams stay distinct", () => {
    expect(teamMatches("Palmeiras-SP", "Corinthians")).toBe(false);
    expect(teamMatches("Santos", "São Paulo")).toBe(false);
  });
});

describe("Feature: Date format handling", () => {
  it("Scenario: ISO dates pass through", () => {
    expect(parseDate("2023-09-24")).toBe("2023-09-24");
  });

  it("Scenario: ISO datetimes are truncated to the date", () => {
    expect(parseDate("2012-05-19 18:30:00")).toBe("2012-05-19");
  });

  it("Scenario: Brazilian DD/MM/YYYY dates are converted", () => {
    expect(parseDate("29/03/2003")).toBe("2003-03-29");
  });

  it("Scenario: junk dates return null instead of throwing", () => {
    expect(parseDate("")).toBeNull();
    expect(parseDate(null)).toBeNull();
    expect(parseDate("not a date")).toBeNull();
  });
});

describe("Feature: UTF-8 handling", () => {
  it("Scenario: foldAccents removes diacritics", () => {
    expect(foldAccents("São Paulo")).toBe("Sao Paulo");
    expect(foldAccents("Grêmio Foot-Ball Porto Alegrense")).toBe(
      "Gremio Foot-Ball Porto Alegrense",
    );
    expect(foldAccents("Fortaleza Esporte Clube")).toBe("Fortaleza Esporte Clube");
  });
});
