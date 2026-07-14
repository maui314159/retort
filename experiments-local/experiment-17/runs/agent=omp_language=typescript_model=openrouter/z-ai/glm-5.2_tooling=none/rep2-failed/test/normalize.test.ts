/**
 * brazilian-soccer-mcp / test/normalize.test.ts
 *
 * BDD tests for normalization helpers (team names, dates, seasons).
 *
 * Context block: verifies the cross-dataset matching contract — that the same
 * club spelled differently across files collapses to one key, and that ISO and
 * Brazilian date formats both normalize to `YYYY-MM-DD`.
 */

import { describe, it, expect } from "vitest";
import {
  parseDate,
  parseSeason,
  positionGroupOf,
  teamDisplay,
  teamKey,
  toInt,
} from "../src/normalize.js";

describe("Feature: Team name normalization", () => {
  it("Scenario: strip state suffix and lowercase", () => {
    expect(teamKey("Palmeiras-SP")).toBe("palmeiras");
    expect(teamKey("Flamengo - RJ")).toBe("flamengo");
    expect(teamKey("Botafogo-RJ")).toBe("botafogo");
  });

  it("Scenario: strip parentheticals", () => {
    expect(teamKey("Nacional (URU)")).toBe("nacional");
    expect(teamKey("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ")).toBe(
      "boavista sport club",
    );
  });

  it("Scenario: strip diacritics so accented and unaccented match", () => {
    expect(teamKey("São Paulo")).toBe("sao paulo");
    expect(teamKey("Sao Paulo")).toBe("sao paulo");
    expect(teamKey("Grêmio")).toBe("gremio");
    expect(teamKey("Gremio")).toBe("gremio");
  });

  it("Scenario: display name keeps accents and casing", () => {
    expect(teamDisplay("Palmeiras-SP")).toBe("Palmeiras");
    expect(teamDisplay("São Paulo")).toBe("São Paulo");
    expect(teamDisplay("Nacional (URU)")).toBe("Nacional");
  });
});

describe("Feature: Date parsing", () => {
  it("Scenario: ISO date with time", () => {
    expect(parseDate("2012-05-19 18:30:00")).toBe("2012-05-19");
  });

  it("Scenario: ISO date only", () => {
    expect(parseDate("2023-09-24")).toBe("2023-09-24");
  });

  it("Scenario: Brazilian DD/MM/YYYY", () => {
    expect(parseDate("29/03/2003")).toBe("2003-03-29");
  });

  it("Scenario: unparseable returns null", () => {
    expect(parseDate("")).toBe(null);
    expect(parseDate(null)).toBe(null);
    expect(parseDate("not a date")).toBe(null);
  });
});

describe("Feature: Season and number parsing", () => {
  it("Scenario: numeric season string", () => {
    expect(parseSeason("2023")).toBe(2023);
    expect(parseSeason(2019)).toBe(2019);
  });

  it("Scenario: out-of-range season is null", () => {
    expect(parseSeason("99")).toBe(null);
  });

  it("Scenario: integer parse with blanks", () => {
    expect(toInt("3")).toBe(3);
    expect(toInt("")).toBe(null);
    expect(toInt(null)).toBe(null);
  });
});

describe("Feature: Position grouping", () => {
  it("Scenario: maps codes to groups", () => {
    expect(positionGroupOf("ST")).toBe("forward");
    expect(positionGroupOf("GK")).toBe("goalkeeper");
    expect(positionGroupOf("CDM")).toBe("midfielder");
    expect(positionGroupOf("CB")).toBe("defender");
  });
});
