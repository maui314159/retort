/**
 * Context
 * =======
 * Normalization helpers for the Brazilian Soccer MCP server.
 *
 * The provided datasets use wildly inconsistent conventions for the same
 * entities. The same club appears as "Palmeiras-SP", "Palmeiras", "Sao Paulo"
 * vs "São Paulo", or "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ".
 * Dates appear as ISO ("2023-09-24"), Brazilian ("29/03/2003"), and ISO with
 * time ("2012-05-19 18:30:00"). Competitions are spelled differently across
 * files ("Serie A" vs "Brasileirão").
 *
 * This module produces a single canonical form per entity so that queries
 * issued in any spelling match rows loaded from any file. Everything here is
 * pure and allocation-conscious: a single lowercase + diacritic strip + suffix
 * trim, no regex compilation in hot loops beyond module-level constants.
 */

/** Module-level constants — compiled once, reused across every call. */
const STATE_SUFFIX_RE = /[\s\-]+(?:[A-Z]{2}|[A-Z]{3})$/; // " - RJ", "-SP", " EQU", " URU"
const PAREN_RE = /\([^)]*\)/g; // "(antigo Esporte Clube Barreira)"
const WS_RE = /\s+/g;
const NON_ALNUM_EDGE_RE = /^[\s\-]+|[\s\-]+$/g;

/** Brazilian state abbreviations used as team-name suffixes. */
const BR_STATES: Record<string, true> = {
  AC: true, AL: true, AP: true, AM: true, BA: true, CE: true, DF: true,
  ES: true, GO: true, MA: true, MT: true, MS: true, MG: true, PA: true,
  PB: true, PR: true, PE: true, PI: true, RJ: true, RN: true, RS: true,
  RO: true, RR: true, SC: true, SP: true, SE: true, TO: true,
};

/** Foreign-country suffixes seen in the Libertadores dataset. */
const FOREIGN_SUFFIX: Record<string, true> = {
  URU: true, ARG: true, EQU: true, PAR: true, CHI: true, COL: true,
  BOL: true, VEN: true, PER: true, MEX: true, BRA: true,
};

/**
 * Strip diacritics and lowercase. "São Paulo" -> "sao paulo", "Grêmio" -> "gremio".
 * Uses Unicode NFD decomposition so cedillas/accents become combining marks we drop.
 */
function deaccentLower(input: string): string {
  return input
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
}

/**
 * Base names that are NOT unique on their own: several distinct clubs share the
 * base and are told apart only by their state/country suffix (e.g. "Atlético-MG"
 * Mineiro vs "Athletico-PR" Paranaense vs "Atlético-GO" Goianiense — all have
 * played Série A). For these the suffix is retained as part of the canonical
 * key; for every other base the suffix is redundant and dropped.
 */
const AMBIGUOUS_BASES: Record<string, true> = {
  atletico: true,
  america: true,
  botafogo: true,
  nacional: true,
  'santa cruz': true,
};

/**
 * Full-name and irregular spellings that diacritic-stripping + suffix-trimming
 * cannot reconcile. Keys are the deaccented/lowercased name (parentheticals
 * removed, whitespace collapsed) as produced mid-pipeline; values are the final
 * canonical key. Checked before the generic suffix logic so e.g. "Atlético
 * Mineiro" (no state token) lands on the same key as "Atlético-MG".
 */
const TEAM_ALIASES: Record<string, string> = {
  // Athletico Paranaense is always PR; "Athletico" (with h) never refers to another club.
  athletico: 'atletico pr',
  'athletico paranaense': 'atletico pr',
  'atletico paranaense': 'atletico pr',
  'atletico mineiro': 'atletico mg',
  'atletico goianiense': 'atletico go',
  'atletico cearense': 'atletico ce',
  'atletico acreano': 'atletico ac',
  // América variants.
  'america mineiro': 'america mg',
  'america fc': 'america mg',
  'america fc minas gerais': 'america mg',
  'america de natal': 'america rn',
  'america fc natal': 'america rn',
  // Single-club full names -> base key.
  'sport club do recife': 'sport',
  'sport recife': 'sport',
  'sport club corinthians paulista': 'corinthians',
  'ceara sporting club': 'ceara',
  'gremio foot-ball porto alegrense': 'gremio',
  'fortaleza esporte clube': 'fortaleza',
  'fortaleza fc': 'fortaleza',
  'fortaleza ec': 'fortaleza',
  'nautico capibaribe': 'nautico',
  'ec bahia': 'bahia',
  vasco: 'vasco da gama',
  'red bull bragantino': 'bragantino',
  'ec juventude': 'juventude',
};

/**
 * Split a deaccented/lowercased, parenthetical-free name into a base and an
 * optional trailing state/country suffix. Recognizes "-sp", " - rj", " pe"
 * forms. Returns the suffix only when the trailing token is a known
 * state/country abbreviation; otherwise the whole string is the base.
 */
function splitBaseSuffix(s: string): { base: string; suffix?: string } {
  const m = /^(.*?)[\s\-]+([a-z]{2,3})$/.exec(s);
  if (m) {
    const suf = m[2].toUpperCase();
    if (BR_STATES[suf] || FOREIGN_SUFFIX[suf]) {
      return { base: m[1].replace(WS_RE, ' ').trim(), suffix: m[2] };
    }
  }
  return { base: s };
}

/**
 * Canonicalize a raw team name to a stable key used for grouping and matching.
 *
 * Pipeline: capture any foreign "(URU)"-style code -> deaccent+lowercase ->
 * drop parentheticals -> collapse whitespace -> apply alias table -> split off a
 * trailing state/country suffix -> for ambiguous bases keep the suffix in the
 * key, otherwise drop it.
 *
 * Returns "" for empty/blank input so callers can skip header artifacts.
 */
export function canonicalTeam(raw: string | undefined | null): string {
  if (!raw) return '';
  const dea = deaccentLower(raw);

  // A foreign country code is sometimes written parenthetically: "Nacional (URU)".
  const paren = /\(([a-z]{2,3})\)/.exec(dea);
  const parenSuffix =
    paren && (BR_STATES[paren[1].toUpperCase()] || FOREIGN_SUFFIX[paren[1].toUpperCase()])
      ? paren[1]
      : undefined;

  const cleaned = dea.replace(PAREN_RE, ' ').replace(WS_RE, ' ').replace(NON_ALNUM_EDGE_RE, '');
  if (!cleaned) return '';

  const direct = TEAM_ALIASES[cleaned];
  if (direct) return direct;

  const { base, suffix } = splitBaseSuffix(cleaned);
  const aliasedBase = TEAM_ALIASES[base];
  if (aliasedBase) return aliasedBase;

  const effectiveSuffix = suffix ?? parenSuffix;
  if (AMBIGUOUS_BASES[base]) {
    return effectiveSuffix ? `${base} ${effectiveSuffix}` : base;
  }
  return base;
}

/**
 * Produce a human-readable display name from a raw team string: drop
 * parentheticals and any trailing state suffix, collapse whitespace, but keep
 * the original accents and casing. For ambiguous bases (e.g. Atlético) the
 * uppercase state suffix is preserved so the club remains distinguishable.
 */
export function displayTeam(raw: string | undefined | null): string {
  if (!raw) return '';
  let s = raw.replace(PAREN_RE, ' ');
  const { base, suffix } = splitBaseSuffix(deaccentLower(s).replace(WS_RE, ' ').replace(NON_ALNUM_EDGE_RE, ''));
  const upper = deaccentLower(s).toUpperCase();
  const m = STATE_SUFFIX_RE.exec(upper);
  if (m) {
    const found = m[0].replace(/[\s\-]+/g, '');
    if (BR_STATES[found] || FOREIGN_SUFFIX[found]) {
      const stripped = s.slice(0, s.length - m[0].length).replace(WS_RE, ' ').replace(NON_ALNUM_EDGE_RE, '');
      // Keep the suffix visible for ambiguous bases so clubs stay distinct.
      s = AMBIGUOUS_BASES[base] && suffix ? `${stripped} (${found})` : stripped;
    }
  }
  return s.replace(WS_RE, ' ').replace(NON_ALNUM_EDGE_RE, '');
}

/**
 * Parse a date in any of the dataset formats into a YYYY-MM-DD ISO date string.
 * Accepts:
 *   - "2023-09-24"
 *   - "2012-05-19 18:30:00"
 *   - "29/03/2003" (DD/MM/YYYY)
 * Returns undefined when the value cannot be parsed.
 */
export function parseDate(raw: string | undefined | null): string | undefined {
  if (!raw) return undefined;
  const s = raw.trim();
  if (!s) return undefined;

  // ISO with optional time component.
  const iso = /^(\d{4})-(\d{2})-(\d{2})/.exec(s);
  if (iso) return `${iso[1]}-${iso[2]}-${iso[3]}`;

  // Brazilian DD/MM/YYYY.
  const br = /^(\d{1,2})\/(\d{1,2})\/(\d{4})/.exec(s);
  if (br) {
    const day = br[1].padStart(2, '0');
    const month = br[2].padStart(2, '0');
    return `${br[3]}-${month}-${day}`;
  }
  return undefined;
}

/** Canonical competition identifiers used across the store. */
export type Competition =
  | 'Brasileirão Série A'
  | 'Brasileirão Série B'
  | 'Brasileirão Série C'
  | 'Copa do Brasil'
  | 'Copa Libertadores';

/**
 * Map a free-text competition name (from data or a user query) to a canonical
 * competition label, or undefined when it does not match a known competition.
 */
export function canonicalCompetition(raw: string | undefined | null): Competition | undefined {
  if (!raw) return undefined;
  const s = deaccentLower(raw).replace(WS_RE, ' ').trim();
  if (s.includes('libertadores')) return 'Copa Libertadores';
  if (s.includes('copa do brasil') || s === 'cup' || s.includes('brazilian cup')) return 'Copa do Brasil';
  if (s.includes('serie b') || s.includes('serie 2') || s.includes('serie ii')) return 'Brasileirão Série B';
  if (s.includes('serie c')) return 'Brasileirão Série C';
  if (
    s.includes('serie a') ||
    s.includes('brasileirao') ||
    s.includes('brasileiro') ||
    s === 'serie a'
  ) {
    return 'Brasileirão Série A';
  }
  return undefined;
}
