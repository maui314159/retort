/**
 * Brazilian Soccer MCP Server — date parsing & helpers
 * ----------------------------------------------------
 * Context block:
 *   The datasets use three date shapes:
 *     - ISO with time: "2012-05-19 18:30:00" (Brasileirão, Copa, Libertadores)
 *     - ISO date only: "2023-09-24" (BR-Football)
 *     - Brazilian: "29/03/2003" (histórico, DD/MM/YYYY)
 *   `parseDate` returns a UTC-midnight Date for the match day, or null.
 */

export function parseDate(raw: string | null | undefined): Date | null {
  if (raw === null || raw === undefined) return null;
  const s = String(raw).trim();
  if (!s || s === "NA" || s === "N/A") return null;

  // Brazilian DD/MM/YYYY
  let m = s.match(/^(\d{2})\/(\d{2})\/(\d{4})(?:\s+(\d{2}):(\d{2})(?::(\d{2}))?)?$/);
  if (m) {
    const [, d, mo, y] = m;
    const date = new Date(Date.UTC(+y, +mo - 1, +d));
    return isNaN(date.getTime()) ? null : date;
  }

  // ISO YYYY-MM-DD with optional time
  m = s.match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?$/);
  if (m) {
    const [, y, mo, d] = m;
    const date = new Date(Date.UTC(+y, +mo - 1, +d));
    return isNaN(date.getTime()) ? null : date;
  }

  return null;
}

/** Format a Date as YYYY-MM-DD (UTC), or return the fallback raw string. */
export function formatDate(date: Date | null, fallback: string): string {
  if (!date) return fallback;
  const y = date.getUTCFullYear();
  const mo = String(date.getUTCMonth() + 1).padStart(2, "0");
  const d = String(date.getUTCDate()).padStart(2, "0");
  return `${y}-${mo}-${d}`;
}

/** Parse a numeric value that may be "NA", "-", "" — returns null when invalid. */
export function parseNum(v: unknown): number | null {
  if (v === null || v === undefined) return null;
  const s = String(v).trim();
  if (s === "" || s === "NA" || s === "N/A" || s === "-") return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}
