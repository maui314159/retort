/**
 * Normalization utilities for team names and dates across datasets.
 *
 * Team naming conventions differ per dataset:
 *   - Brasileirao: "Palmeiras-SP", "Flamengo-RJ"  (suffix, no spaces)
 *   - Copa do Brasil: "América - MG"               (suffix, with spaces)
 *   - BR-Football-Dataset / Historical: "Palmeiras" (no suffix)
 *
 * Date formats:
 *   - ISO with time: "2012-05-19 18:30:00"
 *   - ISO only:      "2023-09-24"
 *   - Brazilian:     "29/03/2003"
 */

/** Strip state suffix and return a comparable lowercase string. */
export function normalizeTeamName(name: string): string {
  if (!name) return '';
  let result = name.trim();
  // "América - MG" style (Copa do Brasil)
  result = result.replace(/\s*-\s*[A-Z]{2}$/, '');
  // "Palmeiras-SP" style (Brasileirao)
  result = result.replace(/-[A-Z]{2}$/, '');
  return result.trim();
}

/**
 * Returns true if the stored team name matches the search term.
 * Matching is case-insensitive and supports partial matches on normalized names.
 */
export function teamMatchesSearch(teamName: string, searchTerm: string): boolean {
  const term = searchTerm.trim();
  if (!term) return true;
  const normalizedTeam = normalizeTeamName(teamName).toLowerCase();
  const normalizedSearch = normalizeTeamName(term).toLowerCase();
  // Support partial: "Palmeiras" matches "Palmeiras-SP" and vice versa
  return normalizedTeam.includes(normalizedSearch) || normalizedSearch.includes(normalizedTeam);
}

/** Parse various date formats to ISO YYYY-MM-DD. */
export function parseDate(dateStr: string): string {
  if (!dateStr) return '';
  const s = dateStr.trim();
  // Brazilian DD/MM/YYYY
  const brMatch = s.match(/^(\d{2})\/(\d{2})\/(\d{4})/);
  if (brMatch) return `${brMatch[3]}-${brMatch[2]}-${brMatch[1]}`;
  // ISO YYYY-MM-DD with optional time
  const isoMatch = s.match(/^(\d{4}-\d{2}-\d{2})/);
  if (isoMatch) return isoMatch[1];
  return s;
}

/** Parse goal values (may be float strings like "1.0" from extended dataset). */
export function parseGoals(val: string | number | undefined): number {
  if (val === undefined || val === null || val === '') return 0;
  const n = parseFloat(String(val));
  return isNaN(n) ? 0 : Math.round(n);
}

/** Extract year from ISO date string. */
export function yearFromDate(date: string): number {
  const m = date.match(/^(\d{4})/);
  return m ? parseInt(m[1]) : 0;
}
