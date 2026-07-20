/**
 * Feature: Text, date and team-name normalization
 *
 * The datasets use different naming conventions and date formats;
 * the implementation must normalize them for consistent matching.
 */
import { describe, it, expect } from "vitest";
import { normalizeText, splitTeamSuffix } from "../src/lib/text.js";
import { parseDateTime, parseYear } from "../src/lib/dates.js";
import { TeamRegistry } from "../src/lib/teams.js";

describe("Feature: Text normalization", () => {
  it("strips accents and cedillas (São Paulo, Grêmio, Avaí)", () => {
    expect(normalizeText("São Paulo")).toBe("sao paulo");
    expect(normalizeText("Grêmio")).toBe("gremio");
    expect(normalizeText("Avaí")).toBe("avai");
    expect(normalizeText("Ceará")).toBe("ceara");
  });

  it("normalizes case and collapses whitespace", () => {
    expect(normalizeText("  FLAMENGO ")).toBe("flamengo");
    expect(normalizeText("Ponte   Preta")).toBe("ponte preta");
  });
});

describe("Feature: Team suffix splitting", () => {
  it('splits dashed state suffixes: "Palmeiras-SP"', () => {
    expect(splitTeamSuffix("Palmeiras-SP")).toEqual({ base: "Palmeiras", uf: "SP" });
  });

  it('splits spaced suffixes: "América - MG"', () => {
    expect(splitTeamSuffix("América - MG")).toEqual({ base: "América", uf: "MG" });
  });

  it('splits country suffixes: "Barcelona-EQU", "Nacional (URU)"', () => {
    expect(splitTeamSuffix("Barcelona-EQU")).toEqual({ base: "Barcelona", uf: "EQU" });
    expect(splitTeamSuffix("Nacional (URU)")).toEqual({ base: "Nacional", uf: "URU" });
  });

  it("leaves suffix-less names intact", () => {
    expect(splitTeamSuffix("Boca Juniors")).toEqual({ base: "Boca Juniors", uf: null });
  });
});

describe("Feature: Date parsing", () => {
  it('parses ISO dates: "2023-09-24"', () => {
    expect(parseDateTime("2023-09-24")).toEqual({ date: "2023-09-24", time: null });
  });

  it('parses ISO datetimes: "2012-05-19 18:30:00"', () => {
    expect(parseDateTime("2012-05-19 18:30:00")).toEqual({ date: "2012-05-19", time: "18:30" });
  });

  it('parses Brazilian dates: "29/03/2003"', () => {
    expect(parseDateTime("29/03/2003")).toEqual({ date: "2003-03-29", time: null });
  });

  it("rejects garbage and empty input", () => {
    expect(parseDateTime("not a date")).toBeNull();
    expect(parseDateTime("")).toBeNull();
    expect(parseDateTime(null)).toBeNull();
  });

  it("extracts years from any supported format", () => {
    expect(parseYear("29/03/2003")).toBe(2003);
    expect(parseYear("2023-09-24")).toBe(2023);
  });
});

describe("Feature: Team name variations", () => {
  it("unifies state-suffixed and bare spellings of the same club", () => {
    const reg = new TeamRegistry();
    const a = reg.register("Palmeiras-SP", "SP");
    const b = reg.register("Palmeiras");
    expect(b.key).toBe(a.key);
    expect(reg.size).toBe(1);
  });

  it("unifies cross-dataset variants (Vasco / Vasco da Gama RJ)", () => {
    const reg = new TeamRegistry();
    const a = reg.register("Vasco-RJ", "RJ");
    const b = reg.register("Vasco Da Gama RJ");
    const c = reg.register("Vasco da Gama - RJ");
    expect(b.key).toBe(a.key);
    expect(c.key).toBe(a.key);
  });

  it("unifies Atletico-PR and Athletico-PR (club respelling)", () => {
    const reg = new TeamRegistry();
    const a = reg.register("Athletico-PR", "PR");
    const b = reg.register("Atletico-PR", "PR");
    expect(b.key).toBe(a.key);
  });

  it("keeps genuinely different clubs with the same base separate", () => {
    const reg = new TeamRegistry();
    const mg = reg.register("Atletico-MG", "MG");
    const go = reg.register("Atletico-GO", "GO");
    expect(mg.key).not.toBe(go.key);
    const res = reg.resolve("atletico");
    expect(res.team).toBeNull();
    expect(res.ambiguous.length).toBeGreaterThanOrEqual(2);
  });

  it("resolves aliases and accents in free-text queries", () => {
    const reg = new TeamRegistry();
    reg.register("Sao Paulo-SP", "SP");
    reg.register("Gremio-RS", "RS");
    expect(reg.resolve("São Paulo").team?.key).toBe("sao paulo-sp");
    expect(reg.resolve("sao paulo fc").team?.key).toBe("sao paulo-sp");
    expect(reg.resolve("Grêmio").team?.key).toBe("gremio-rs");
  });
});
