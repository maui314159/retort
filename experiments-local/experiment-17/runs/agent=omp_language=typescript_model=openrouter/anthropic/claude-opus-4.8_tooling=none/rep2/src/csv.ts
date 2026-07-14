/**
 * Context
 * -------
 * Minimal RFC-4180-ish CSV reader with zero dependencies.
 *
 * The datasets mix quoted and unquoted fields, embedded commas inside quotes,
 * a UTF-8 BOM on fifa_data.csv, and `\r\n` line endings. A hand-rolled parser
 * keeps the dependency surface tiny and handles every quirk we actually see.
 *
 * `parseCsv` returns an array of row objects keyed by the header names. Values
 * are raw strings; typed coercion happens in the loader.
 */

/** Parse CSV text into header-keyed row records. */
export function parseCsv(text: string): Record<string, string>[] {
  const rows = parseRows(text);
  if (rows.length === 0) return [];

  const header = rows[0]!.map((h) => h.trim());
  const out: Record<string, string>[] = [];

  for (let i = 1; i < rows.length; i++) {
    const cells = rows[i]!;
    // Skip fully blank trailing lines.
    if (cells.length === 1 && cells[0] === "") continue;
    const record: Record<string, string> = {};
    for (let c = 0; c < header.length; c++) {
      record[header[c]!] = cells[c] ?? "";
    }
    out.push(record);
  }
  return out;
}

/** Tokenize CSV text into rows of raw cell strings. */
function parseRows(text: string): string[][] {
  // Strip BOM if present.
  const src = text.charCodeAt(0) === 0xfeff ? text.slice(1) : text;

  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let inQuotes = false;

  for (let i = 0; i < src.length; i++) {
    const ch = src[i]!;

    if (inQuotes) {
      if (ch === '"') {
        if (src[i + 1] === '"') {
          field += '"';
          i++; // escaped quote
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
      row = [];
      field = "";
    } else if (ch === "\r") {
      // swallow; the \n (or EOF) finalizes the row
    } else {
      field += ch;
    }
  }

  // Flush trailing field/row if the file lacks a final newline.
  if (field.length > 0 || row.length > 0) {
    row.push(field);
    rows.push(row);
  }
  return rows;
}
