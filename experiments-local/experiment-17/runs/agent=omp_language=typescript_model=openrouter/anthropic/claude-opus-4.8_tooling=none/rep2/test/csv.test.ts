/**
 * Context
 * -------
 * Unit coverage for the zero-dependency CSV reader: quoted fields with embedded
 * commas, escaped quotes, BOM stripping, and CRLF handling — all quirks present
 * in the real datasets.
 */

import { describe, expect, it } from "vitest";

import { parseCsv } from "../src/csv.js";

describe("Feature: CSV parsing", () => {
  it("Scenario: quoted fields with embedded commas are preserved", () => {
    const rows = parseCsv('a,b\n"hello, world","x"\n');
    expect(rows).toHaveLength(1);
    expect(rows[0]).toEqual({ a: "hello, world", b: "x" });
  });

  it("Scenario: escaped double-quotes inside a field", () => {
    const rows = parseCsv('a\n"she said ""hi"""\n');
    expect(rows[0]?.a).toBe('she said "hi"');
  });

  it("Scenario: a UTF-8 BOM on the header is stripped", () => {
    const rows = parseCsv("\uFEFFid,name\n1,Messi\n");
    expect(rows[0]).toEqual({ id: "1", name: "Messi" });
  });

  it("Scenario: CRLF line endings are handled", () => {
    const rows = parseCsv("a,b\r\n1,2\r\n3,4\r\n");
    expect(rows).toHaveLength(2);
    expect(rows[1]).toEqual({ a: "3", b: "4" });
  });

  it("Scenario: a final row without a trailing newline is still read", () => {
    const rows = parseCsv("a,b\n1,2");
    expect(rows).toHaveLength(1);
    expect(rows[0]).toEqual({ a: "1", b: "2" });
  });
});
