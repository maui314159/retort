/**
 * brazilian-soccer-mcp — normalisation helpers
 *
 * Context block
 * ============
 * See src/types.ts for the top-level project context block.
 *
 * This module centralises every "messy input → canonical form" rule so the
 * query engine can match across datasets that use different conventions:
 *   • Team names appear with state suffixes ("Palmeiras-SP"), parenthetical
 *     disambiguators ("Nacional (URU)"), and trailing " - UF" fragments
 *     ("América - MG"). We strip these to a bare, accent-preserving base.
 *   • Dates appear as ISO ("2023-09-24"), ISO+time ("2012-05-19 18:30:00"),
 *     or Brazilian DD/MM/YYYY ("29/03/2003"). We normalise to ISO date and,
 *     when time is present, a full ISO-ish datetime string.
 *   • Goal columns are sometimes numeric, sometimes quoted strings; parse
 *     defensively (null when blank or non-numeric).
 *
 * Normalisation is idempotent and total — it never throws on malformed
 * input; it returns null / the original string instead so a single bad
 * row never aborts loading 10k matches.
 */

const STATE_SUFFIX_RE = /[-–]\s*[A-Z]{2}$/; // "Palmeiras-SP", "América - MG"
const PAREN_RE = /\s*\([^)]*\)\s*$/; // "Nacional (URU)"
const TRAILING_DASH_STATE_RE = /\s+-\s+[A-Z]{2}$/; // "América - MG" (spaces around dash)

/**
 * Canonical team name.
 *
 * Strategy, applied in order: trim, drop parenthetical disambiguators,
 * drop trailing "-UF" / " - UF" state suffixes, collapse internal
 * whitespace. Accents (São Paulo, Grêmio, Avaí) are intentionally
 * preserved for fidelity; matching uses a separate accent-folded key.
 */
export function normalizeTeam(raw: string | null | undefined): string {
  if (!raw) return "";
  let t = raw.trim();
  // Remove parentheticals first so "Nacional (URU)" → "Nacional".
  t = t.replace(PAREN_RE, "");
  // "América - MG" with surrounding spaces.
  t = t.replace(TRAILING_DASH_STATE_RE, "");
  // "Palmeiras-SP" with no spaces.
  t = t.replace(STATE_SUFFIX_RE, "");
  t = t.replace(/\s+/g, " ").trim();
  return t;
}

/**
 * Accent-folded, lowercased key for tolerant team matching.
 * "São Paulo" → "sao paulo"; used only for equality / containment tests,
 * never displayed.
 */
export function teamKey(name: string): string {
  return name
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9 ]/g, "")
    .trim();
}

/**
 * True when two team names refer to the same team under tolerant matching:
 * accent- and case-insensitive, and a substring either way (so "São Paulo"
 * matches "São Paulo FC" and the full historical names). The substring rule
 * is deliberately bidirectional but requires the shorter key to be at least
 * 3 chars to avoid "SP" matching everything.
 */
export function teamsMatch(a: string, b: string): boolean {
  const ka = teamKey(a);
  const kb = teamKey(b);
  if (!ka || !kb) return false;
  if (ka === kb) return true;
  const [shorter, longer] = ka.length <= kb.length ? [ka, kb] : [kb, ka];
  if (shorter.length < 3) return false;
  return longer.includes(shorter);
}

/** Parse a date string into a `YYYY-MM-DD` string, or null if unparseable. */
export function normalizeDate(raw: string | null | undefined): string | null {
  if (!raw) return null;
  const s = String(raw).trim();
  if (!s) return null;

  // ISO with optional time: "2023-09-24" or "2012-05-19 18:30:00".
  const isoMatch = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (isoMatch) {
    return `${isoMatch[1]}-${isoMatch[2]}-${isoMatch[3]}`;
  }

  // Brazilian DD/MM/YYYY (possibly with spaces or time).
  const brMatch = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (brMatch) {
    const [, d, m, y] = brMatch;
    return `${y}-${m.padStart(2, "0")}-${d.padStart(2, "0")}`;
  }

  return null;
}

/** Full ISO-ish datetime string if the source recorded time, else the date. */
export function normalizeDateTime(raw: string | null | undefined): string | null {
  if (!raw) return null;
  const s = String(raw).trim();
  if (!s) return null;
  const date = normalizeDate(s);
  if (!date) return null;
  const timeMatch = s.match(/(\d{2}:\d{2}(?::\d{2})?)/);
  if (timeMatch) return `${date} ${timeMatch[1]}`;
  return date;
}

/** Parse a goal/score cell that may be numeric, quoted, or blank → number|null. */
export function parseScore(raw: string | null | undefined): number | null {
  if (raw === null || raw === undefined) return null;
  const s = String(raw).trim();
  if (s === "") return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

/** Parse a year/season cell → integer or null. */
export function parseSeason(raw: string | null | undefined): number | null {
  if (raw === null || raw === undefined) return null;
  const s = String(raw).trim();
  if (!s) return null;
  // Accept "2019" or the year out of an ISO date.
  const m = s.match(/^(\d{4})/);
  if (!m) return null;
  const n = Number(m[1]);
  return Number.isFinite(n) ? n : null;
}
