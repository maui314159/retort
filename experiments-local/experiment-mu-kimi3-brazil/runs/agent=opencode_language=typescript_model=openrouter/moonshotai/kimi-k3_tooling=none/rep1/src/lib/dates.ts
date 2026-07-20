/**
 * Date parsing for the multiple formats used across the datasets:
 *  - ISO date:            "2023-09-24"
 *  - ISO with time:       "2012-05-19 18:30:00"
 *  - Brazilian DD/MM/YYYY: "29/03/2003"
 */

export interface ParsedDateTime {
  /** ISO date YYYY-MM-DD. */
  date: string;
  /** HH:MM when present in the source, else null. */
  time: string | null;
}

function pad(n: number): string {
  return n < 10 ? `0${n}` : String(n);
}

/** Parse a date/datetime string into ISO parts; returns null when unparseable. */
export function parseDateTime(raw: string | null | undefined): ParsedDateTime | null {
  if (!raw) return null;
  const s = raw.trim();
  if (s.length === 0) return null;

  // Brazilian format: DD/MM/YYYY (optionally followed by a time).
  let m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})(?:\s+(\d{1,2}):(\d{2})(?::\d{2})?)?$/);
  if (m) {
    const [, dd, mm, yyyy, hh, mi] = m;
    return {
      date: `${yyyy}-${pad(Number(mm))}-${pad(Number(dd))}`,
      time: hh ? `${pad(Number(hh))}:${mi}` : null,
    };
  }

  // ISO format: YYYY-MM-DD optionally followed by HH:MM[:SS].
  m = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})(?:[T ](\d{1,2}):(\d{2})(?::\d{2})?)?$/);
  if (m) {
    const [, yyyy, mm, dd, hh, mi] = m;
    return {
      date: `${yyyy}-${pad(Number(mm))}-${pad(Number(dd))}`,
      time: hh ? `${pad(Number(hh))}:${mi}` : null,
    };
  }

  return null;
}

/** Extract the 4-digit year from any supported date string. */
export function parseYear(raw: string | null | undefined): number | null {
  const p = parseDateTime(raw);
  return p ? Number(p.date.slice(0, 4)) : null;
}
