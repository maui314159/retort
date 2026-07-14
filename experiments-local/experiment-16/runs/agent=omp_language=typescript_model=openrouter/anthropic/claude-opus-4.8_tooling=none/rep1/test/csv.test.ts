/**
 * Context
 * -------
 * Unit tests for the CSV parser, exercising the specific quirks present in the
 * Kaggle datasets: quoted fields containing commas, escaped double-quotes, a
 * leading UTF-8 BOM, and CRLF line endings.
 */

import { describe, it, expect } from "vitest";
import { parseCsv } from "../src/csv.js";

describe("parseCsv", () => {
  it("parses simple rows into keyed records", () => {
    const rows = parseCsv("a,b,c\n1,2,3\n4,5,6");
    expect(rows).toEqual([
      { a: "1", b: "2", c: "3" },
      { a: "4", b: "5", c: "6" },
    ]);
  });

  it("handles quoted fields containing commas", () => {
    const rows = parseCsv('name,team\n"Boavista, RJ","América - MG"');
    expect(rows[0].name).toBe("Boavista, RJ");
    expect(rows[0].team).toBe("América - MG");
  });

  it("handles escaped double-quotes", () => {
    const rows = parseCsv('q\n"He said ""hi"""');
    expect(rows[0].q).toBe('He said "hi"');
  });

  it("strips a leading UTF-8 BOM from the first header", () => {
    const rows = parseCsv("\uFEFFid,name\n1,Messi");
    expect(rows[0]).toHaveProperty("id", "1");
    expect(Object.keys(rows[0])).toContain("id");
  });

  it("normalizes CRLF line endings", () => {
    const rows = parseCsv("a,b\r\n1,2\r\n3,4\r\n");
    expect(rows).toEqual([
      { a: "1", b: "2" },
      { a: "3", b: "4" },
    ]);
  });

  it("ignores a trailing blank line", () => {
    const rows = parseCsv("a\n1\n");
    expect(rows).toHaveLength(1);
  });
});
