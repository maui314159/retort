/**
 * Strip accents/diacritics and lowercase for fuzzy comparison.
 */
export function normalizeForSearch(s: string): string {
  return s
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim();
}

/**
 * Remove the Brazilian state suffix (e.g. "-SP", " - RJ") from team names.
 * Handles:
 *   "Palmeiras-SP"         → "Palmeiras"
 *   "Flamengo-RJ"          → "Flamengo"
 *   "América - MG"         → "América"
 *   "Nacional (URU)"       → "Nacional (URU)"  (kept — 3-letter suffix, not a state)
 */
export function stripStateSuffix(name: string): string {
  return name.replace(/\s*-\s*[A-Z]{2}$/, '').trim();
}

/**
 * Determine whether a stored team name matches a search query.
 * Returns true if the normalized query is found anywhere in the normalized stored name
 * (or its de-suffixed form).
 */
export function teamMatches(storedName: string, query: string): boolean {
  if (!query) return false;
  const q = normalizeForSearch(query);
  const full = normalizeForSearch(storedName);
  const stripped = normalizeForSearch(stripStateSuffix(storedName));
  return full === q || stripped === q || full.includes(q) || stripped.includes(q);
}

/**
 * Parse a Brazilian-style date (DD/MM/YYYY) or ISO-prefixed datetime to ISO date YYYY-MM-DD.
 */
export function parseDate(raw: string): string {
  if (!raw) return '';
  const trimmed = raw.trim();
  // "DD/MM/YYYY"
  if (/^\d{2}\/\d{2}\/\d{4}$/.test(trimmed)) {
    const [d, m, y] = trimmed.split('/');
    return `${y}-${m}-${d}`;
  }
  // "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS"
  if (/^\d{4}-\d{2}-\d{2}/.test(trimmed)) {
    return trimmed.substring(0, 10);
  }
  return trimmed;
}

/**
 * Safely parse a numeric value from a string or number, returning 0 on failure.
 */
export function parseGoals(raw: string | number | undefined): number {
  if (raw === undefined || raw === null || raw === '') return 0;
  const n = typeof raw === 'number' ? raw : parseFloat(String(raw));
  return isFinite(n) ? Math.round(n) : 0;
}
