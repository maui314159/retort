/**
 * Context
 * -------
 * Normalization helpers for the Brazilian Soccer MCP server.
 *
 * The datasets describe the same club under several spellings:
 *   - with a state suffix:   "Palmeiras-SP", "Flamengo - RJ"
 *   - with a country suffix:  "Nacional (URU)", "Barcelona-EQU"
 *   - full legal names:       "Boavista Sport Club (antigo ...) - RJ"
 *   - accented Portuguese:    "São Paulo", "Grêmio", "Avaí"
 *
 * To answer "all Flamengo matches" regardless of source file we reduce every
 * club name to a stable `normalizeTeamKey` (accent-folded, lowercased, suffixes
 * stripped) used purely for matching, while preserving a human-readable display
 * name via `cleanDisplayName`. Dates arrive in three formats and are unified to
 * ISO `YYYY-MM-DD` by `parseDate`.
 */
/** Remove diacritics (accents, cedilla) and return a plain ASCII string. */
export function stripAccents(input: string): string {
  return input.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

/**
 * Normalize a team name for display: collapse internal whitespace and trim.
 * The geographic/country suffix is intentionally KEPT (e.g. "Atletico-MG",
 * "Nacional (URU)") because several distinct clubs share a base name —
 * Atlético-MG, Atlético-GO and Atlético-PR would otherwise collapse into one.
 */
export function cleanDisplayName(name: string): string {
  return name.replace(/\s+/g, " ").trim();
}

/**
 * Build the canonical matching key for a team name: accent-folded, lowercased,
 * with every run of non-alphanumeric characters collapsed to a single space.
 * The suffix is preserved as a token, so "Atletico-MG" -> "atletico mg" stays
 * distinct from "Atletico-GO" -> "atletico go". Cross-spelling lookups go
 * through `teamMatches` rather than relying on exact key equality.
 */
export function normalizeTeamKey(name: string): string {
  return stripAccents(name).toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

/**
 * Loose containment check used for fuzzy team lookups: does `candidate`
 * reference the same club as the user-supplied `query`? True on exact key
 * equality or when one normalized key contains the other as a whole-token
 * substring (so "Flamengo" matches "Flamengo-RJ", but "Santos" does not match
 * "Santo André").
 */
export function teamMatches(candidate: string, query: string): boolean {
  const c = normalizeTeamKey(candidate);
  const q = normalizeTeamKey(query);
  if (q.length === 0 || c.length === 0) return false;
  if (c === q) return true;
  return containsToken(c, q) || containsToken(q, c);
}

function containsToken(haystack: string, needle: string): boolean {
  let from = 0;
  for (;;) {
    const idx = haystack.indexOf(needle, from);
    if (idx === -1) return false;
    const before = idx === 0 ? " " : haystack[idx - 1];
    const afterIdx = idx + needle.length;
    const after = afterIdx >= haystack.length ? " " : haystack[afterIdx];
    if (before === " " && after === " ") return true;
    from = idx + 1;
  }
}

/**
 * Parse the various date formats present in the datasets into ISO
 * `YYYY-MM-DD`. Returns `undefined` when the value cannot be parsed.
 *
 * Handled:
 *   "2012-05-19 18:30:00"  (ISO with time)
 *   "2023-09-24"           (ISO date)
 *   "29/03/2003"           (Brazilian DD/MM/YYYY)
 */
export function parseDate(raw: string | undefined): string | undefined {
  if (!raw) return undefined;
  const s = raw.trim();
  if (s.length === 0) return undefined;

  // ISO date, optionally followed by a time component.
  const iso = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (iso) return `${iso[1]}-${iso[2]}-${iso[3]}`;

  // Brazilian DD/MM/YYYY.
  const br = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (br) {
    const dd = br[1].padStart(2, "0");
    const mm = br[2].padStart(2, "0");
    return `${br[3]}-${mm}-${dd}`;
  }

  return undefined;
}

/** Parse an integer from a possibly-float string ("2.0" -> 2). */
export function parseIntSafe(raw: string | undefined): number | undefined {
  if (raw === undefined) return undefined;
  const s = raw.trim();
  if (s === "") return undefined;
  const n = Number(s);
  return Number.isFinite(n) ? Math.trunc(n) : undefined;
}

/** Parse a float, returning `undefined` for blank/invalid values. */
export function parseFloatSafe(raw: string | undefined): number | undefined {
  if (raw === undefined) return undefined;
  const s = raw.trim();
  if (s === "") return undefined;
  const n = Number(s);
  return Number.isFinite(n) ? n : undefined;
}
