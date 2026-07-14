/**
 * Context
 * -------
 * Unit tests for the normalization layer. These pin the team-name canonicalization
 * rules that everything else depends on: state suffixes are KEPT as tokens (so
 * different-state clubs stay distinct) while diacritics, country qualifiers and
 * club noise words are folded away. Also covers tolerant goal and multi-format
 * date parsing.
 */

import { describe, it, expect } from "vitest";
import {
  normalizeTeam,
  normalizeText,
  parseGoals,
  parseDate,
  stripDiacritics,
} from "../src/normalize.js";

describe("stripDiacritics", () => {
  it("removes Portuguese accents and cedilla", () => {
    expect(stripDiacritics("São Paulo")).toBe("Sao Paulo");
    expect(stripDiacritics("Grêmio")).toBe("Gremio");
    expect(stripDiacritics("Avaí")).toBe("Avai");
  });
});

describe("normalizeTeam", () => {
  it("folds accents and lowercases", () => {
    expect(normalizeTeam("São Paulo")).toBe("sao paulo");
    expect(normalizeTeam("Grêmio")).toBe("gremio");
  });

  it("keeps the state token so same-named clubs stay distinct", () => {
    expect(normalizeTeam("Atletico-MG")).toBe("atletico mg");
    expect(normalizeTeam("Atletico-GO")).toBe("atletico go");
    expect(normalizeTeam("Athletico-PR")).toBe("athletico pr");
    expect(normalizeTeam("Atletico-MG")).not.toBe(normalizeTeam("Atletico-GO"));
  });

  it("strips country qualifiers in parentheses", () => {
    expect(normalizeTeam("Nacional (URU)")).toBe("nacional");
  });

  it("removes club noise words", () => {
    expect(normalizeTeam("Sport Club do Recife")).toBe("recife");
    expect(normalizeTeam("São Paulo FC")).toBe("sao paulo");
  });

  it("handles long official names with embedded qualifiers", () => {
    expect(
      normalizeTeam("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"),
    ).toContain("boavista");
  });
});

describe("normalizeText", () => {
  it("folds accents and collapses whitespace", () => {
    expect(normalizeText("  Neymar   Jr ")).toBe("neymar jr");
    expect(normalizeText("Grêmio")).toBe("gremio");
  });
});

describe("parseGoals", () => {
  it("parses plain and float-encoded integers", () => {
    expect(parseGoals("2")).toBe(2);
    expect(parseGoals("2.0")).toBe(2);
    expect(parseGoals("0")).toBe(0);
  });

  it("returns null for missing / NA values", () => {
    expect(parseGoals("")).toBeNull();
    expect(parseGoals("NA")).toBeNull();
    expect(parseGoals(undefined)).toBeNull();
  });
});

describe("parseDate", () => {
  it("parses ISO date and datetime", () => {
    expect(parseDate("2023-09-24").iso).toBe("2023-09-24");
    expect(parseDate("2012-05-19 18:30:00").iso).toBe("2012-05-19");
  });

  it("parses Brazilian DD/MM/YYYY", () => {
    expect(parseDate("29/03/2003").iso).toBe("2003-03-29");
    expect(parseDate("1/5/2019").iso).toBe("2019-05-01");
  });

  it("returns null iso for unparseable input but keeps raw", () => {
    const d = parseDate("not a date");
    expect(d.iso).toBeNull();
    expect(d.raw).toBe("not a date");
  });
});
