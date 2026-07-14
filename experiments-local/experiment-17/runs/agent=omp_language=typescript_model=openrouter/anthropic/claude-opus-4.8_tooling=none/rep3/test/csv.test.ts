/**
 * Context
 * -------
 * BDD tests for the CSV parser (src/csv.ts). The Kaggle files mix quoted and
 * unquoted fields, embedded commas, doubled quotes, a UTF-8 BOM, and CRLF line
 * endings; these scenarios pin that behavior.
 */

import { describe, it, expect } from "vitest";
import { parseCsv } from "../src/csv.js";

describe("Feature: CSV parsing", () => {
  describe("Scenario: quoted fields containing commas", () => {
    it("Given a quoted field with a comma, When parsed, Then it is one cell", () => {
      // Given a row whose first field is a quoted name containing a comma
      const text = 'a,b\n"Boavista, RJ",2';
      // When parsed
      const rows = parseCsv(text);
      // Then the comma stays inside the single field
      expect(rows[0].a).toBe("Boavista, RJ");
      expect(rows[0].b).toBe("2");
    });
  });

  describe("Scenario: a leading UTF-8 BOM on the header", () => {
    it("Given a BOM-prefixed header, When parsed, Then the key is clean", () => {
      // Given a file that starts with a BOM (as fifa_data.csv does)
      const text = "\uFEFFName,Age\nMessi,31";
      // When parsed
      const rows = parseCsv(text);
      // Then the first header is not polluted by the BOM
      expect(rows[0].Name).toBe("Messi");
      expect(Object.keys(rows[0])[0]).toBe("Name");
    });
  });

  describe("Scenario: doubled quotes and CRLF endings", () => {
    it("Given escaped quotes and CRLF, When parsed, Then both are handled", () => {
      // Given a quoted field with an escaped quote and Windows line endings
      const text = 'x\r\n"say ""hi"""\r\n';
      // When parsed
      const rows = parseCsv(text);
      // Then the doubled quote collapses and the trailing CRLF is ignored
      expect(rows).toHaveLength(1);
      expect(rows[0].x).toBe('say "hi"');
    });
  });
});
