/**
 * Context
 * -------
 * RFC-4180-ish streaming CSV parser used by the data loader. The Kaggle
 * datasets quote fields containing commas (e.g. "Boavista Sport Club (antigo
 * Esporte Clube Barreira) - RJ"), embed a UTF-8 BOM in `fifa_data.csv`, and
 * mix CRLF / LF line endings. A bespoke parser keeps the project dependency-free
 * for ingestion and gives us exact control over those quirks.
 *
 * Exports
 * -------
 * - parseCsv(text): parse a full CSV document into an array of row objects keyed
 *   by trimmed header names. Handles quoted fields, escaped quotes (""),
 *   embedded newlines, BOM stripping and CRLF normalization.
 */

/** Parse a CSV document into an array of records keyed by header name. */
export function parseCsv(text: string): Record<string, string>[] {
  const rows = parseRows(text);
  if (rows.length === 0) return [];

  const headers = rows[0].map((h) => h.trim());
  const records: Record<string, string>[] = [];

  for (let i = 1; i < rows.length; i++) {
    const row = rows[i];
    // Skip blank trailing lines produced by a final newline.
    if (row.length === 1 && row[0] === "") continue;
    const record: Record<string, string> = {};
    for (let c = 0; c < headers.length; c++) {
      record[headers[c]] = (row[c] ?? "").trim();
    }
    records.push(record);
  }
  return records;
}

/** Tokenize CSV text into rows of raw (untrimmed) cell strings. */
export function parseRows(text: string): string[][] {
  // Strip UTF-8 BOM if present.
  if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);

  const rows: string[][] = [];
  let field = "";
  let row: string[] = [];
  let inQuotes = false;

  for (let i = 0; i < text.length; i++) {
    const ch = text[i];

    if (inQuotes) {
      if (ch === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i++; // consume escaped quote
        } else {
          inQuotes = false;
        }
      } else {
        field += ch;
      }
      continue;
    }

    if (ch === '"') {
      inQuotes = true;
    } else if (ch === ",") {
      row.push(field);
      field = "";
    } else if (ch === "\n") {
      row.push(field);
      rows.push(row);
      field = "";
      row = [];
    } else if (ch === "\r") {
      // swallow; the following \n (if any) closes the row
    } else {
      field += ch;
    }
  }

  // Flush the final field/row when the file does not end in a newline.
  if (field !== "" || row.length > 0) {
    row.push(field);
    rows.push(row);
  }

  return rows;
}
