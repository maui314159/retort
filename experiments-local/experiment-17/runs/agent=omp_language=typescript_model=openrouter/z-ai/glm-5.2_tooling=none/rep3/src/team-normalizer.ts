/**
 * brazilian-soccer-mcp / src/team-normalizer.ts
 *
 * Team-name normalization.
 *
 * Context block:
 * The datasets use inconsistent team naming: some append a Brazilian state
 * suffix ("Palmeiras-SP", "Flamengo-RJ"), some append a country marker for
 * non-Brazilian sides ("Nacional (URU)", "Barcelona-EQU"), some carry
 * historical annotations ("Boavista Sport Club (antigo Esporte Clube
 * Barreira) - RJ"), and the extended stats file uses bare names ("Sao Paulo").
 * To answer cross-file queries reliably we reduce every name to a canonical
 * matching key plus a clean display name. The key strips suffixes/markers and
 * lowercases; the display name keeps the cleaned human-readable form.
 */

// Brazilian state abbreviations used as suffixes in the match files.
const STATE_ABBREVS: Record<string, true> = {
  AC: true, AL: true, AP: true, AM: true, BA: true, CE: true, DF: true, ES: true,
  GO: true, MA: true, MT: true, MS: true, MG: true, PA: true, PB: true, PR: true,
  PE: true, PI: true, RJ: true, RN: true, RS: true, RO: true, RR: true, SC: true,
  SP: true, SE: true, TO: true,
};

// Country / federation markers seen in Libertadores data, e.g. "(URU)", "(EQU)".
const COUNTRY_MARKER = /\s*\(([A-Z]{3})\)\s*/g;

// Historical annotation, e.g. " (antigo Esporte Clube Barreira)".
const ANTIGO_MARKER = /\s*\(antigo[^)]*\)\s*/gi;

// Trailing state suffix: "-SP", " - RJ", " -RJ".
const STATE_SUFFIX = /\s*-\s*([A-Z]{2})\s*$/;

/**
 * Strip noise (state suffix, country marker, historical annotation) from a raw
 * team name, returning a clean display name. Does not lowercase.
 */
export function cleanTeamName(raw: string): string {
  let s = raw.trim();
  s = s.replace(ANTIGO_MARKER, ' ');
  s = s.replace(COUNTRY_MARKER, ' ');
  // Repeatedly strip a trailing state suffix only when it actually is a state.
  for (let i = 0; i < 3; i++) {
    const m = s.match(STATE_SUFFIX);
    if (m && STATE_ABBREVS[m[1]]) {
      s = s.slice(0, m.index).trim();
    } else {
      break;
    }
  }
  return s.replace(/\s+/g, ' ').trim();
}

/**
 * Canonical matching key for a team name: cleaned, lowercased, accents folded
 * to ASCII so that "São Paulo" and "Sao Paulo" match across files.
 */
export function teamKey(raw: string): string {
  const cleaned = cleanTeamName(raw);
  return foldAccents(cleaned).toLowerCase().trim();
}

/** Fold common Portuguese accented characters to ASCII equivalents. */
export function foldAccents(s: string): string {
  return s.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

