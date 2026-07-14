/**
 * Context
 * -------
 * Minimal, dependency-free RFC 4180 CSV parser for the Brazilian Soccer MCP
 * server. The provided Kaggle files mix quoting styles (some columns quoted,
 * some not), contain UTF-8 Portuguese text, a leading BOM (fifa_data.csv), and
 * embedded commas inside quoted fields. A streaming character-level parser is
 * used rather than a naive `split(",")` so those cases are handled correctly.
 *
 * Exports `parseCsv` -> array of row objects keyed by the header names.
 */

/** Parse CSV text into a list of objects keyed by the (trimmed) header row. */
export function parseCsv(text: string): Record<string, string>[] {
  const rows = parseRows(text);
  if (rows.length === 0) return [];

  const header = rows[0].map((h) => stripBom(h).trim());
  const out: Record<string, string>[] = [];

  for (let i = 1; i < rows.length; i++) {
    const cells = rows[i];
    // Skip fully empty trailing lines.
    if (cells.length === 1 && cells[0] === "") continue;
    const record: Record<string, string> = {};
    for (let c = 0; c < header.length; c++) {
      record[header[c]] = (cells[c] ?? "").trim();
    }
    out.push(record);
  }
  return out;
}

/** Parse raw CSV text into a 2D array of string cells. */
function parseRows(text: string): string[][] {
  const rows: string[][] = [];
  let field = "";
  let row: string[] = [];
  let inQuotes = false;
  let i = 0;
  const n = text.length;

  const pushField = () => {
    row.push(field);
    field = "";
  };
  const pushRow = () => {
    pushField();
    rows.push(row);
    row = [];
  };

  while (i < n) {
    const ch = text[i];

    if (inQuotes) {
      if (ch === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i += 2;
          continue;
        }
        inQuotes = false;
        i++;
        continue;
      }
      field += ch;
      i++;
      continue;
    }

    if (ch === '"') {
      inQuotes = true;
      i++;
      continue;
    }
    if (ch === ",") {
      pushField();
      i++;
      continue;
    }
    if (ch === "\r") {
      // Handle CRLF and lone CR.
      if (text[i + 1] === "\n") i++;
      pushRow();
      i++;
      continue;
    }
    if (ch === "\n") {
      pushRow();
      i++;
      continue;
    }
    field += ch;
    i++;
  }

  // Flush trailing field/row if the file did not end with a newline.
  if (field.length > 0 || row.length > 0) pushRow();

  return rows;
}

function stripBom(s: string): string {
  return s.charCodeAt(0) === 0xfeff ? s.slice(1) : s;
}
