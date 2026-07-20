import { describe, expect, it } from "vitest";
import {
  normalizeTeamName,
  parseDate,
  parseScore,
  stripAccents,
  competitionMatches,
} from "../src/normalize.js";
import { canonicalTeamKey, cleanTeamName } from "../src/teams.js";

describe("Feature: Name and date normalization", () => {
  it("Scenario: Team name variations resolve to the same club", () => {
    // Given the naming conventions used across the datasets
    // When names are normalized
    // Then variants of one club share a canonical key
    expect(canonicalTeamKey("Palmeiras-SP")).toBe("palmeiras");
    expect(canonicalTeamKey("Palmeiras")).toBe("palmeiras");
    expect(canonicalTeamKey("Flamengo-RJ")).toBe("flamengo");
    expect(canonicalTeamKey("Flamengo")).toBe("flamengo");
    expect(canonicalTeamKey("Grêmio")).toBe("gremio");
    expect(canonicalTeamKey("Gremio-RS")).toBe("gremio");
    expect(canonicalTeamKey("Vasco da Gama-RJ")).toBe("vasco da gama");
    expect(canonicalTeamKey("Vasco")).toBe("vasco da gama");
    expect(canonicalTeamKey("Atletico-PR")).toBe("athletico paranaense");
    expect(canonicalTeamKey("Athletico Paranaense")).toBe("athletico paranaense");
    expect(canonicalTeamKey("Sport-PE")).toBe("sport recife");
    expect(canonicalTeamKey("Sport Recife")).toBe("sport recife");
    expect(canonicalTeamKey("Sport Club Corinthians Paulista")).toBe("corinthians");
  });

  it("Scenario: Distinct clubs are not merged", () => {
    expect(canonicalTeamKey("Botafogo-RJ")).not.toBe(canonicalTeamKey("Botafogo-PB"));
    expect(canonicalTeamKey("Botafogo-RJ")).not.toBe(canonicalTeamKey("Botafogo SP"));
    expect(canonicalTeamKey("Portuguesa-SP")).not.toBe(canonicalTeamKey("Portuguesa RJ"));
    expect(canonicalTeamKey("Atletico-MG")).toBe("atletico mineiro");
    expect(canonicalTeamKey("Atletico-GO")).toBe("atletico goianiense");
    expect(canonicalTeamKey("Atletico-MG")).not.toBe(canonicalTeamKey("Atletico-GO"));
    expect(canonicalTeamKey("Santa Cruz-PE")).not.toBe(canonicalTeamKey("Santa Cruz RN"));
  });

  it("Scenario: Accents and cedillas are handled (UTF-8)", () => {
    expect(stripAccents("São Paulo")).toBe("Sao Paulo");
    expect(stripAccents("Grêmio")).toBe("Gremio");
    expect(stripAccents("Avaí")).toBe("Avai");
    expect(canonicalTeamKey("São Paulo-SP")).toBe("sao paulo");
    expect(canonicalTeamKey("Cuiabá - MT")).toBe("cuiaba");
  });

  it("Scenario: Multiple date formats parse to ISO", () => {
    expect(parseDate("2023-09-24")).toBe("2023-09-24");
    expect(parseDate("2012-05-19 18:30:00")).toBe("2012-05-19");
    expect(parseDate("29/03/2003")).toBe("2003-03-29");
    expect(parseDate("")).toBeNull();
    expect(parseDate(null)).toBeNull();
  });

  it("Scenario: Scores tolerate float formatting", () => {
    expect(parseScore("1.0")).toBe(1);
    expect(parseScore("3")).toBe(3);
    expect(parseScore("")).toBeNull();
  });

  it("Scenario: Competition aliases match only the right competition", () => {
    expect(competitionMatches("Brasileirão", "Brasileirão Série A")).toBe(true);
    expect(competitionMatches("Serie A", "Brasileirão Série A")).toBe(true);
    expect(competitionMatches("Brasileirão Série A", "Brasileirão Série B")).toBe(false);
    expect(competitionMatches("Copa do Brasil", "Copa do Brasil")).toBe(true);
    expect(competitionMatches("Libertadores", "Copa Libertadores")).toBe(true);
  });

  it("Scenario: cleanTeamName keeps state tokens and flattens punctuation", () => {
    expect(cleanTeamName("América - MG")).toBe("america mg");
    expect(cleanTeamName("A.B.C. - RN")).toBe("abc rn");
    expect(cleanTeamName("Guaraní (PAR)")).toBe("guarani par");
  });

  it("Scenario: normalizeTeamName still provides plain keys", () => {
    expect(normalizeTeamName("Palmeiras-SP")).toBe("palmeiras");
    expect(normalizeTeamName("")).toBe("");
  });
});
