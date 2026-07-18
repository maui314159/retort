/**
 * brazilian-soccer-mcp — CSV parsing helpers.
 *
 * Context: We use `csv-parse` (synchronous) rather than a naive split-on-comma,
 * because the Brazilian Cup dataset legitimately contains commas inside quoted
 * team names and all datasets carry quoted headers. We also strip the UTF-8
 * BOM that fifa_data.csv ships with, and we treat the first row as a header.
 */

import { parse } from "csv-parse/sync";
import { readFileSync } from "node:fs";

/** Read a CSV file and return an array of row records keyed by header name. */
export function readCsv(path: string): Record<string, string>[] {
  let buf = readFileSync(path);
  // Strip UTF-8 BOM (fifa_data.csv ships with one).
  if (buf.length >= 3 && buf[0] === 0xef && buf[1] === 0xbb && buf[2] === 0xbf) {
    buf = buf.subarray(3);
  }
  const text = buf.toString("utf-8");
  const records = parse(text, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    bom: false, // we stripped it ourselves
    relax_quotes: true,
    relax_column_count: true,
  }) as Record<string, string>[];
  return records;
}

/** Case-insensitive lookup of a field from a record, tolerating header renames. */
export function field(
  row: Record<string, string>,
  ...names: string[]
): string | undefined {
  for (const n of names) {
    for (const k of Object.keys(row)) {
      if (k.trim().toLowerCase() === n.toLowerCase()) {
        return row[k];
      }
    }
  }
  return undefined;
}
