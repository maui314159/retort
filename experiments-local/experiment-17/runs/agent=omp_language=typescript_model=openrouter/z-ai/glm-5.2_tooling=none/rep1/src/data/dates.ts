/**
 * Brazilian Soccer MCP Server — Date parsing across source formats.
 *
 * Context block
 * -------------
 * The datasets store dates in three formats:
 *   - ISO with time:   "2012-05-19 18:30:00"  (Brasileirão, Copa do Brasil, Libertadores)
 *   - ISO date only:   "2023-09-24"            (BR-Football-Dataset)
 *   - Brazilian date:  "29/03/2003"            (novo_campeonato_brasileiro, DD/MM/YYYY)
 *
 * `parseDate` accepts any of these and returns a Date at UTC midnight (date
 * semantics) so that date-range comparisons are timezone-stable. Returns null
 * for empty or unparseable input rather than throwing — loaders must tolerate
 * dirty rows.
 */

const ISO_DATETIME = /^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?$/;
const BR_DATE = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/;

/** Parse a date string from any supported source format. Returns null if unparseable. */
export function parseDate(raw: string | null | undefined): Date | null {
  if (raw === null || raw === undefined) return null;
  const s = String(raw).trim();
  if (s.length === 0) return null;

  const iso = s.match(ISO_DATETIME);
  if (iso) {
    const y = iso[1]!;
    const mo = iso[2]!;
    const d = iso[3]!;
    const h = iso[4] ?? "0";
    const mi = iso[5] ?? "0";
    const se = iso[6] ?? "0";
    return new Date(Date.UTC(+y, +mo - 1, +d, +h, +mi, +se));
  }

  const br = s.match(BR_DATE);
  if (br) {
    const [, d, mo, y] = br;
    return new Date(Date.UTC(+y!, +mo! - 1, +d!));
  }

  const fallback = new Date(s);
  return Number.isNaN(fallback.getTime()) ? null : fallback;
}

/** ISO yyyy-mm-dd representation of a date (or the raw input when null). */
export function toISODate(d: Date | null, fallbackRaw?: string): string {
  if (!d) return fallbackRaw ?? "unknown";
  return d.toISOString().slice(0, 10);
}
