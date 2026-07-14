/**
 * Date parsing utilities.
 *
 * Source files mix three date conventions:
 *   - ISO-like: "2023-09-24" or "2012-05-19 18:30:00"
 *   - Brazilian: "29/03/2003"
 *
 * This module normalizes all of them to an ISO date string
 * (YYYY-MM-DD) and a comparable numeric timestamp.
 */

const BRAZILIAN_RE = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/;
const ISO_RE = /^(\d{4})-(\d{1,2})-(\d{1,2})/;

/**
 * Parse a raw date string and return an ISO date (YYYY-MM-DD).
 * Returns undefined when the input cannot be parsed.
 */
export function parseDate(raw: string): string | undefined {
  if (!raw || typeof raw !== "string") return undefined;

  const trimmed = raw.trim();
  if (!trimmed) return undefined;

  let year: number | undefined;
  let month: number | undefined;
  let day: number | undefined;

  const brazilian = BRAZILIAN_RE.exec(trimmed);
  if (brazilian) {
    day = Number(brazilian[1]);
    month = Number(brazilian[2]);
    year = Number(brazilian[3]);
  } else {
    const iso = ISO_RE.exec(trimmed);
    if (iso) {
      year = Number(iso[1]);
      month = Number(iso[2]);
      day = Number(iso[3]);
    }
  }

  if (
    year === undefined ||
    month === undefined ||
    day === undefined ||
    Number.isNaN(year) ||
    Number.isNaN(month) ||
    Number.isNaN(day)
  ) {
    return undefined;
  }

  const date = new Date(year, month - 1, day);
  // Guard against invalid dates like 31/02/2020.
  if (
    date.getFullYear() !== year ||
    date.getMonth() !== month - 1 ||
    date.getDate() !== day
  ) {
    return undefined;
  }

  return `${String(year)}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

/**
 * Convert a parsed ISO date string to a UTC timestamp comparable
 * with standard operators.
 */
export function toTimestamp(isoDate: string): number {
  const [year, month, day] = isoDate.split("-").map(Number);
  return Date.UTC(year, month - 1, day);
}

/**
 * Compare an ISO date against an inclusive date range.
 */
export function inRange(date: string, start?: string, end?: string): boolean {
  const ts = toTimestamp(date);
  if (start !== undefined && ts < toTimestamp(start)) return false;
  if (end !== undefined && ts > toTimestamp(end)) return false;
  return true;
}
