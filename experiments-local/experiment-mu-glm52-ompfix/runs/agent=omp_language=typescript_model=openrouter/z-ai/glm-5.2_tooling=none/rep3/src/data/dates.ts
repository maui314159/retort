/**
 * Brazilian Soccer MCP Server — Date Parsing
 * -----------------------------------------------------------------------------
 * Context block:
 *   Datasets use three date representations:
 *     • ISO with time:        "2012-05-19 18:30:00"
 *     • ISO date-only:        "2023-09-24"
 *     • Brazilian DD/MM/YYYY: "29/03/2003"
 *   All values are assumed to be in a Brazilian context (UTC-3 implied but we
 *   do not perform timezone conversion; we preserve wall-clock strings and
 *   also expose a sortable ISO `YYYY-MM-DD` date).
 *
 *   `parseDate` returns an ISO `YYYY-MM-DD` string or null. `parseDatetime`
 *   returns the full ISO-ish `YYYY-MM-DDTHH:MM:SS` form (or the date-only form
 *   when no time is present), or null. A `Date` is returned by `toDate` for
 *   range comparisons only; we prefer string comparison on the normalized
 *   `YYYY-MM-DD` form where possible since it is monotonic and timezone-free.
 */

/** Parse a date/datetime cell into an ISO `YYYY-MM-DD` string, or null. */
export function parseDate(raw: string | null | undefined): string | null {
  const dt = parseDatetime(raw);
  if (dt) return dt.slice(0, 10);
  return null;
}

/** Parse a date/datetime cell into `YYYY-MM-DD[THH:MM:SS]`, or null. */
export function parseDatetime(raw: string | null | undefined): string | null {
  if (raw == null) return null;
  const s = String(raw).trim();
  if (!s || s.toLowerCase() === "na") return null;

  // ISO with optional time: 2012-05-19 18:30:00  /  2012-05-19  /  2023-09-24T20:00:00
  let m = s.match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?$/);
  if (m) {
    const [, y, mo, d, hh, mm, ss] = m;
    if (hh) return `${y}-${mo}-${d}T${hh}:${mm}:${ss ?? "00"}`;
    return `${y}-${mo}-${d}`;
  }

  // Brazilian: 29/03/2003  or  29/03/2003 15:00
  m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})(?:[ T](\d{1,2}):(\d{2}))?$/);
  if (m) {
    const [, d, mo, y, hh, mm] = m;
    const dd = d.padStart(2, "0");
    const mmo = mo.padStart(2, "0");
    if (hh) return `${y}-${mmo}-${dd}T${hh.padStart(2, "0")}:${mm}:00`;
    return `${y}-${mmo}-${dd}`;
  }

  return null;
}

/** Convert a parsed ISO string to a JS Date for range math, or null. */
export function toDate(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const d = new Date(iso.length > 10 ? iso : iso + "T00:00:00");
  return Number.isNaN(d.getTime()) ? null : d;
}

/** Inclusive range check on ISO date strings (monotonic). */
export function inDateRange(
  iso: string | null,
  from?: string | null,
  to?: string | null,
): boolean {
  if (!iso) return false;
  if (from && iso < from) return false;
  if (to && iso > to) return false;
  return true;
}
