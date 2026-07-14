/**
 * Brazilian Soccer MCP Server - Name & Date Normalization
 * -------------------------------------------------------
 * Context: The six Kaggle datasets use inconsistent conventions for team
 * names (with/without state suffixes, full legal names, accents, parenthesized
 * disambiguators) and for dates (ISO, DD/MM/YYYY, ISO+time). This module
 * provides the canonical normalization functions used by the loaders and the
 * query layer so that lookups like "Flamengo" reliably match "Flamengo-RJ",
 * "Clube de Regatas do Flamengo", etc.
 */

/**
 * Normalize a team name into a stable, accent-folded, lowercased key.
 *
 * Rules applied in order:
 *  1. Trim and collapse internal whitespace.
 *  2. Strip trailing "-UF" suffixes ("Palmeiras-SP" -> "Palmeiras").
 *  3. Strip parenthesized disambiguators ("América (MG)" -> "América").
 *  4. Replace common Brazilian club legal-name prefixes/suffixes
 *     ("Sport Club Corinthians Paulista" -> "Corinthians").
 *  5. Fold accents to ASCII and lowercase.
 *  6. Strip a trailing " - <state>" pattern used in some datasets.
 */
export function normalizeTeamName(raw: string): string {
  if (!raw) return "";
  let s = String(raw).trim();

  // Drop trailing " - RJ" / "-SP" style suffixes (with or without spaces).
  s = s.replace(/\s*-\s*([A-Z]{2})\s*$/, "");
  s = s.replace(/\s+-\s+[A-Z]{2}$/, "");

  // Drop parenthesized content, e.g. "Nacional (URU)" -> "Nacional".
  s = s.replace(/\s*\([^)]*\)\s*/g, " ").trim();

  // Drop " - RJ" suffix appearing after parentheses were stripped too.
  s = s.replace(/\s*-\s*([A-Z]{2})\s*$/, "");

  // Collapse repeated whitespace.
  s = s.replace(/\s+/g, " ").trim();

  // Map common full legal names to short forms.
  s = applyKnownAliases(s);

  // Fold accents to ASCII.
  s = foldAccents(s);

  return s.toLowerCase().trim();
}

/**
 * Return a *display* version of a team name: trimmed, with the trailing
 * "-UF" suffix removed, but accents preserved. Used when surfacing team
 * names to users so we don't uglify "São Paulo" into "sao paulo".
 */
export function displayTeamName(raw: string): string {
  if (!raw) return "";
  let s = String(raw).trim();
  s = s.replace(/\s*-\s*([A-Z]{2})\s*$/, "");
  s = s.replace(/\s*\([^)]*\)\s*/g, " ").trim();
  s = s.replace(/\s*-\s*([A-Z]{2})\s*$/, "");
  s = applyKnownAliases(s);
  s = s.replace(/\s+/g, " ").trim();
  return s;
}

const ALIASES: Array<[RegExp, string]> = [
  [/^sport club corinthians paulista$/i, "Corinthians"],
  [/^sport club corinthians$/i, "Corinthians"],
  [/^são paulo futebol clube$/i, "São Paulo"],
  [/^sao paulo futebol clube$/i, "São Paulo"],
  [/^clube de regatas do flamengo$/i, "Flamengo"],
  [/^clube atlético mineiro$/i, "Atlético Mineiro"],
  [/^clube atletico mineiro$/i, "Atlético Mineiro"],
  [/^grêmio foot-ball porto alegrense$/i, "Grêmio"],
  [/^gremio foot-ball porto alegrense$/i, "Grêmio"],
  [/^sport club internacional$/i, "Internacional"],
  [/^sociedade esportiva palmeiras$/i, "Palmeiras"],
  [/^santos futebol clube$/i, "Santos"],
  [/^crf vasco da gama$/i, "Vasco da Gama"],
  [/^club de regatas vasco da gama$/i, "Vasco da Gama"],
  [/^fluminense football club$/i, "Fluminense"],
  [/^botafogo de futebol e regatas$/i, "Botafogo"],
  [/^botafogo futebol e regatas$/i, "Botafogo"],
  [/^club athletico paranaense$/i, "Athletico Paranaense"],
  [/^athletico paranaense$/i, "Athletico Paranaense"],
];

function applyKnownAliases(s: string): string {
  for (const [re, replacement] of ALIASES) {
    if (re.test(s)) return replacement;
  }
  return s;
}

/** Fold Portuguese accents/diacritics to ASCII equivalents. */
export function foldAccents(s: string): string {
  return s.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

/**
 * Parse a date string from any of the source datasets.
 *
 * Supported inputs:
 *  - "2023-09-24"
 *  - "2023-09-24 20:00:00"
 *  - "29/03/2003"
 *  - "29/03/2003 16:00"
 *
 * Returns an ISO date string (YYYY-MM-DD) or null if unparseable.
 */
export function parseDate(raw: string): string | null {
  if (!raw) return null;
  const s = String(raw).trim();
  if (!s) return null;

  // ISO datetime: "2023-09-24 20:00:00" or "2023-09-24"
  let m = s.match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T]\d{2}:\d{2}(?::\d{2})?)?$/);
  if (m) {
    return `${m[1]}-${m[2]}-${m[3]}`;
  }

  // Brazilian DD/MM/YYYY
  m = s.match(/^(\d{2})\/(\d{2})\/(\d{4})(?:\s+\d{2}:\d{2}(?::\d{2})?)?$/);
  if (m) {
    return `${m[3]}-${m[2]}-${m[1]}`;
  }

  // Fall back to Date parsing.
  const d = new Date(s);
  if (!isNaN(d.getTime())) {
    return d.toISOString().slice(0, 10);
  }
  return null;
}

/** Parse a numeric value that may be empty, null, or already a number. */
export function parseNumber(raw: unknown): number | null {
  if (raw === null || raw === undefined || raw === "") return null;
  const n = Number(raw);
  return isNaN(n) ? null : n;
}
