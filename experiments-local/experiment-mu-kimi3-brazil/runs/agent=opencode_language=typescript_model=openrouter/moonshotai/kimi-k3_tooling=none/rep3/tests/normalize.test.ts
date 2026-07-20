/**
 * Feature: Name and date normalization
 *
 * The datasets use different naming conventions and date formats;
 * the implementation normalizes them for consistent matching.
 */

import { describe, expect, it } from "vitest";
import {
  canonicalTeamKey,
  isBrazilianTeamKey,
  parseDate,
  parseTeamName,
  resolveCompetition,
  resolveTeamQuery,
  teamDisplayName,
  teamNameMatches,
} from "../src/normalize.js";

describe("Feature: Team name normalization", () => {
  it("Scenario: state-suffixed names resolve to one canonical key", () => {
    // Given raw names from different sources
    const variants = ["Palmeiras-SP", "Palmeiras - SP", "Palmeiras"];
    // When they are normalized
    const keys = variants.map(canonicalTeamKey);
    // Then all variants map to the same key
    expect(new Set(keys).size).toBe(1);
    expect(keys[0]).toBe("palmeiras-sp");
  });

  it("Scenario: accents and encoding variants match", () => {
    // Given names with and without accents
    // When normalized
    // Then "São Paulo", "Sao Paulo" and "Sao Paulo-SP" coincide
    expect(canonicalTeamKey("São Paulo")).toBe(canonicalTeamKey("Sao Paulo"));
    expect(canonicalTeamKey("São Paulo - SP")).toBe("sao-paulo-sp");
    expect(canonicalTeamKey("Grêmio")).toBe(canonicalTeamKey("Gremio"));
  });

  it("Scenario: full club names map to the short canonical form", () => {
    expect(canonicalTeamKey("Sport Club Corinthians Paulista")).toBe("corinthians-sp");
    expect(canonicalTeamKey("Clube Atlético Mineiro")).toBe("atletico-mg");
    expect(canonicalTeamKey("Sport Club do Recife")).toBe("sport-pe");
    expect(canonicalTeamKey("América FC (Minas Gerais)")).toBe("america-mg");
  });

  it("Scenario: verbose parenthetical names are stripped", () => {
    // Given the Copa do Brasil's verbose naming
    const raw = "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ";
    // When normalized
    // Then it equals the plain form
    expect(canonicalTeamKey(raw)).toBe(canonicalTeamKey("Boavista - RJ"));
  });

  it("Scenario: same-name clubs from different states stay distinct", () => {
    // Given clubs that share a base name but are different entities
    // Then the state suffix keeps them apart
    expect(canonicalTeamKey("Botafogo - PB")).not.toBe(canonicalTeamKey("Botafogo-RJ"));
    expect(canonicalTeamKey("Botafogo SP")).not.toBe(canonicalTeamKey("Botafogo-RJ"));
    expect(canonicalTeamKey("Flamengo - PI")).not.toBe(canonicalTeamKey("Flamengo"));
    expect(canonicalTeamKey("Guarani - SP")).not.toBe(canonicalTeamKey("Guarani de Juazeiro - CE"));
  });

  it("Scenario: historical and modern spellings of the same club merge", () => {
    // Atlético Paranaense renamed to Athletico Paranaense in 2019
    expect(canonicalTeamKey("Atletico-PR")).toBe("athletico-pr");
    expect(canonicalTeamKey("Atlético Paranaense - PR")).toBe("athletico-pr");
    expect(canonicalTeamKey("Athletico Paranaense")).toBe("athletico-pr");
    expect(canonicalTeamKey("Athletico")).toBe("athletico-pr");
    // Bragantino became Red Bull Bragantino
    expect(canonicalTeamKey("Bragantino - SP")).toBe("red-bull-bragantino-sp");
    expect(canonicalTeamKey("Red Bull Bragantino")).toBe("red-bull-bragantino-sp");
  });

  it("Scenario: Libertadores country suffixes are preserved and normalized", () => {
    expect(canonicalTeamKey("Guaraní (PAR)")).toBe("guarani-par");
    expect(canonicalTeamKey("Guaraní-PAR")).toBe("guarani-par");
    expect(canonicalTeamKey("Nacional (URU)")).toBe("nacional-uru");
    expect(canonicalTeamKey("Libertad")).toBe("libertad-par");
    // And the Paraguayan Guaraní is NOT the Brazilian Guarani
    expect(canonicalTeamKey("Guaraní (PAR)")).not.toBe(canonicalTeamKey("Guarani - SP"));
  });

  it("Scenario: foreign clubs ending in state-like tokens are not mangled", () => {
    // "SC" = Sporting Clube, not Santa Catarina: no state suffix is parsed
    expect(parseTeamName("Portimonense SC").state).toBeNull();
    expect(parseTeamName("SC Braga").state).toBeNull();
    // And the club is not mistaken for a Brazilian one
    expect(isBrazilianTeamKey(canonicalTeamKey("Portimonense SC"))).toBe(false);
    expect(isBrazilianTeamKey(canonicalTeamKey("SC Braga"))).toBe(false);
    expect(isBrazilianTeamKey(canonicalTeamKey("Vitória Guimarães"))).toBe(false);
    // While genuinely Brazilian clubs are detected
    expect(isBrazilianTeamKey(canonicalTeamKey("Flamengo"))).toBe(true);
  });

  it("Scenario: parseTeamName splits base and suffix", () => {
    expect(parseTeamName("Flamengo-RJ")).toEqual({ base: "flamengo", state: "RJ" });
    expect(parseTeamName("Aguia Negra-MS")).toEqual({ base: "aguia negra", state: "MS" });
    expect(parseTeamName("Boca Juniors")).toEqual({ base: "boca juniors", state: null });
  });

  it("Scenario: user queries resolve loosely", () => {
    expect(resolveTeamQuery("sao paulo")).toBe("sao-paulo-sp");
    expect(resolveTeamQuery("SÃO PAULO FC")).toBe("sao-paulo-sp");
    expect(resolveTeamQuery("gremio")).toBe("gremio-rs");
    expect(teamDisplayName(resolveTeamQuery("vasco"))).toBe("Vasco da Gama");
  });

  it("Scenario: teamNameMatches supports substring lookup", () => {
    expect(teamNameMatches("flamengo", "Flamengo-RJ")).toBe(true);
    expect(teamNameMatches("Grêmio", "Gremio-RS")).toBe(true);
    expect(teamNameMatches("corinthians", "Corinthians-SP")).toBe(true);
  });
});

describe("Feature: Date format handling", () => {
  it("Scenario: ISO dates pass through", () => {
    expect(parseDate("2023-09-24")).toBe("2023-09-24");
  });

  it("Scenario: ISO datetimes are truncated to the date", () => {
    expect(parseDate("2012-05-19 18:30:00")).toBe("2012-05-19");
  });

  it("Scenario: Brazilian DD/MM/YYYY is converted", () => {
    expect(parseDate("29/03/2003")).toBe("2003-03-29");
    expect(parseDate("05/12/2018")).toBe("2018-12-05");
  });

  it("Scenario: empty and invalid dates yield null", () => {
    expect(parseDate("")).toBeNull();
    expect(parseDate(null)).toBeNull();
    expect(parseDate("not a date")).toBeNull();
  });
});

describe("Feature: Competition label resolution", () => {
  it("Scenario: common aliases resolve", () => {
    expect(resolveCompetition("Brasileirão")).toBe("Brasileirão Série A");
    expect(resolveCompetition("Serie A")).toBe("Brasileirão Série A");
    expect(resolveCompetition("Serie B")).toBe("Brasileirão Série B");
    expect(resolveCompetition("copa do brasil")).toBe("Copa do Brasil");
    expect(resolveCompetition("Libertadores")).toBe("Copa Libertadores");
    expect(resolveCompetition("Copa Libertadores")).toBe("Copa Libertadores");
  });

  it("Scenario: unknown competitions yield null", () => {
    expect(resolveCompetition("Premier League")).toBeNull();
    expect(resolveCompetition("")).toBeNull();
  });
});
