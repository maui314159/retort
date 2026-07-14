/**
 * Context
 * -------
 * Normalization helpers that make fuzzy, accent-insensitive matching possible
 * across datasets with inconsistent naming conventions. The datasets express the
 * same club many ways:
 *   - state suffix:   "Palmeiras-SP", "Flamengo-RJ"
 *   - " - UF" suffix: "América - MG", "Boavista Sport Club (...) - RJ"
 *   - country suffix: "Nacional (URU)", "Barcelona-EQU"
 *   - plain:          "Palmeiras", "Sao Paulo"
 *   - accented:       "São Paulo", "Grêmio", "Avaí", "Atlético-MG"
 *
 * Strategy: derive a canonical key by stripping diacritics, lowercasing,
 * removing state/country suffixes and parenthetical qualifiers, dropping common
 * club-name noise words, and collapsing whitespace. Matching is then done on
 * those keys with a substring fallback so "Sao Paulo" matches "São Paulo FC".
 *
 * Exports
 * -------
 * - stripDiacritics(s)
 * - normalizeTeam(name): canonical key for a team/club name
 * - normalizeText(s): generic accent-folded lowercase key (players, etc.)
 * - parseGoals(s): tolerant integer parse for goal columns ("2", "2.0", "")
 * - parseDate(s): parse ISO, Brazilian (DD/MM/YYYY) and datetime strings to a
 *   normalized ISO date string (YYYY-MM-DD) plus the original.
 */

/** Brazilian state UF codes used as team-name suffixes. */
export const UF_CODES: Record<string, true> = {
  AC: true, AL: true, AP: true, AM: true, BA: true, CE: true, DF: true,
  ES: true, GO: true, MA: true, MT: true, MS: true, MG: true, PA: true,
  PB: true, PR: true, PE: true, PI: true, RJ: true, RN: true, RS: true,
  RO: true, RR: true, SC: true, SP: true, SE: true, TO: true,
};

/** Noise words removed from team keys so long official names match short ones. */
const TEAM_NOISE: Record<string, true> = {
  fc: true, ec: true, sc: true, ac: true, cr: true, ca: true,
  esporte: true, clube: true, club: true, futebol: true, sport: true,
  associacao: true, atletica: true, de: true, do: true, da: true, the: true,
};

/** Remove combining diacritical marks (NFD-based). */
export function stripDiacritics(s: string): string {
  return s.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

/** Accent-folded, lowercased, whitespace-collapsed key for free text. */
export function normalizeText(s: string): string {
  return stripDiacritics(s).toLowerCase().replace(/\s+/g, " ").trim();
}

/**
 * Canonical key for a team / club name.
 *
 * Strips diacritics and country qualifiers ("Nacional (URU)" -> "nacional"),
 * folds punctuation to spaces, and drops generic club noise words. The state
 * suffix is DELIBERATELY KEPT as a token ("Atletico-MG" -> "atletico mg") so
 * same-named, different-state clubs (Atlético-MG vs Atlético-GO vs Athletico-PR)
 * never collapse into one key. Matching tolerates the suffix via the
 * token-bounded substring rule in `teamKeyMatches` ("palmeiras" ⊂ "palmeiras sp").
 */
export function normalizeTeam(name: string): string {
  let s = stripDiacritics(name).toLowerCase();

  // Remove parenthetical qualifiers: "nacional (uru)" -> "nacional".
  s = s.replace(/\([^)]*\)/g, " ");

  // Fold all punctuation (hyphens, dots) to spaces.
  s = s.replace(/[^a-z0-9 ]/g, " ");

  const tokens = s.split(/\s+/).filter(Boolean);
  const meaningful = tokens.filter((t) => !TEAM_NOISE[t]);
  const kept = meaningful.length > 0 ? meaningful : tokens;
  return kept.join(" ");
}

/** Tolerant integer parse for goal columns: "2", "2.0", "", "NA" -> number. */
export function parseGoals(s: string | undefined): number | null {
  if (s == null) return null;
  const t = s.trim();
  if (t === "" || /^na$/i.test(t)) return null;
  const n = Number(t);
  if (!Number.isFinite(n)) return null;
  return Math.trunc(n);
}

export interface ParsedDate {
  /** Normalized ISO date (YYYY-MM-DD) or null when unparseable. */
  iso: string | null;
  /** Original string as stored in the dataset. */
  raw: string;
}

/**
 * Parse the various date formats found across datasets:
 *   - "2023-09-24"            (ISO date)
 *   - "2012-05-19 18:30:00"   (ISO datetime)
 *   - "29/03/2003"            (Brazilian DD/MM/YYYY)
 */
export function parseDate(raw: string | undefined): ParsedDate {
  const value = (raw ?? "").trim();
  if (value === "") return { iso: null, raw: value };

  // ISO date or datetime: take the leading YYYY-MM-DD.
  const isoMatch = value.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (isoMatch) {
    return { iso: `${isoMatch[1]}-${isoMatch[2]}-${isoMatch[3]}`, raw: value };
  }

  // Brazilian DD/MM/YYYY (optionally with time).
  const brMatch = value.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (brMatch) {
    const day = brMatch[1].padStart(2, "0");
    const month = brMatch[2].padStart(2, "0");
    return { iso: `${brMatch[3]}-${month}-${day}`, raw: value };
  }

  return { iso: null, raw: value };
}
