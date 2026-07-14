/**
 * Name and date normalization helpers.
 *
 * The six source datasets use several different conventions for team names
 * (with/without a "-SP" state suffix, full club names, mixed-case accented
 * text) and for dates (ISO `YYYY-MM-DD`, Brazilian `DD/MM/YYYY`, ISO with
 * time `YYYY-MM-DD HH:MM:SS`). This module collapses those variations into
 * canonical forms so that lookups and joins across files behave consistently.
 *
 * Disambiguation: a bare base name like "Atletico" is shared by several
 * distinct clubs (Atletico-MG, Atletico-PR, Atletico-GO). Blindly stripping
 * the state suffix would merge their records. {@link TeamNameRegistry}
 * therefore keeps the suffix only when the base name is ambiguous across the
 * whole dataset, and strips it otherwise (so "Palmeiras-SP" -> "Palameras"
 * while "Atletico-MG" is preserved).
 */

/** Strip a trailing "-UF" state suffix (e.g. "Palmeiras-SP" -> "Palmeiras"). */
export function stripStateSuffix(name: string): string {
  return name.replace(/-[A-Z]{2}$/, '').trim();
}

const ACCENT_MAP: Record<string, string> = {
  á: 'a', à: 'a', ã: 'a', â: 'a', ä: 'a',
  é: 'e', è: 'e', ê: 'e', ë: 'e',
  í: 'i', ì: 'i', î: 'i', ï: 'i',
  ó: 'o', ò: 'o', õ: 'o', ô: 'o', ö: 'o',
  ú: 'u', ù: 'u', û: 'u', ü: 'u',
  ç: 'c', ñ: 'n',
};
const ACCENT_RE = new RegExp(`[${Object.keys(ACCENT_MAP).join('')}]`, 'g');

/** Lowercase ASCII-folded form used only for fuzzy equality comparison. */
export function normalizeKey(name: string): string {
  const folded = name
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, (m) => ACCENT_MAP[m.toLowerCase()] ?? m)
    .toLowerCase()
    .replace(ACCENT_RE, (m) => ACCENT_MAP[m] ?? m)
    .replace(/[^a-z0-9]/g, '')
    .trim();
  return folded;
}

/** Extract a trailing 2-letter state code from a team name, if present. */
export function extractState(name: string): string | undefined {
  const m = name.match(/-([A-Z]{2})$/);
  return m ? m[1] : undefined;
}

/** Trim + collapse internal whitespace; preserve accents/suffix. */
export function cleanTeamName(raw: string): string {
  if (raw == null) return '';
  return String(raw).trim().replace(/\s+/g, ' ');
}

/**
 * Basic canonical team name: strips an *unambiguous* state suffix, trims, and
 * collapses whitespace. For dataset-wide disambiguation use
 * {@link TeamNameRegistry.canonical} instead.
 */
export function normalizeTeamName(raw: string): string {
  return stripStateSuffix(cleanTeamName(raw));
}

/** True if two team names refer to the same team (accent/period/suffix-insensitive). */
export function teamsEqual(a: string, b: string): boolean {
  return normalizeKey(a) === normalizeKey(b);
}

/** True if `name` matches `query` (team), supporting substring + normalization. */
export function teamMatches(name: string, query: string): boolean {
  const nk = normalizeKey(name);
  const qk = normalizeKey(query);
  if (!qk) return false;
  if (nk === qk) return true;
  // Substring match catches "Corinthians" inside "Sport Club Corinthians Paulista"
  // and "Palmeiras" inside "Palmeiras-SP".
  return nk.includes(qk) || qk.includes(nk);
}

/**
 * Registry that resolves canonical team names across the whole dataset.
 *
 * Built by registering every (rawName, state) pair observed, then finalized.
 * A base name (suffix-stripped) is considered ambiguous if it appears with
 * more than one distinct state; for ambiguous base names the suffix is
 * retained, otherwise it is dropped.
 */
export class TeamNameRegistry {
  private baseToStates = new Map<string, Set<string>>();
  private finalized = false;

  /** Register an observation of a team name (with optional state). */
  register(rawName: string, state?: string): void {
    const cleaned = cleanTeamName(rawName);
    if (!cleaned) return;
    const base = stripStateSuffix(cleaned);
    const st = (state || extractState(cleaned) || '').toUpperCase();
    let set = this.baseToStates.get(base);
    if (!set) {
      set = new Set<string>();
      this.baseToStates.set(base, set);
    }
    if (st) set.add(st);
  }

  /** Finalize the registry (no more registrations). */
  finalize(): void {
    this.finalized = true;
  }

  /** Resolve the canonical name for an observed team. */
  canonical(rawName: string, state?: string): string {
    if (!this.finalized) this.finalize();
    const cleaned = cleanTeamName(rawName);
    if (!cleaned) return '';
    const base = stripStateSuffix(cleaned);
    const st = (state || extractState(cleaned) || '').toUpperCase();
    const states = this.baseToStates.get(base);
    // Keep the suffix when the base name maps to >1 distinct states.
    if (states && states.size > 1 && st) {
      return `${base}-${st}`;
    }
    return base;
  }
}

/**
 * Parse a date from any of the formats used in the datasets.
 * Returns ISO `YYYY-MM-DD` or null when unparseable.
 */
export function parseDate(raw: string): string | null {
  if (!raw) return null;
  const s = String(raw).trim();
  if (!s) return null;

  // ISO with optional time: 2012-05-19 18:30:00  or  2023-09-24
  const iso = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (iso) {
    const [, y, m, d] = iso;
    return `${y}-${m}-${d}`;
  }

  // Brazilian DD/MM/YYYY
  const br = s.match(/^(\d{2})\/(\d{2})\/(\d{4})/);
  if (br) {
    const [, d, m, y] = br;
    return `${y}-${m}-${d}`;
  }

  // YYYY.MM.DD (sometimes used in IDs)
  const dotted = s.match(/^(\d{4})\.(\d{2})\.(\d{2})/);
  if (dotted) {
    const [, y, m, d] = dotted;
    return `${y}-${m}-${d}`;
  }

  return null;
}

/** Parse a year/season from a value that may be a number or numeric string. */
export function parseSeason(raw: unknown): number | undefined {
  if (raw == null || raw === '') return undefined;
  const n = typeof raw === 'number' ? raw : parseInt(String(raw), 10);
  return Number.isFinite(n) ? n : undefined;
}

/** Parse a numeric goal value, tolerating "2", 2, "2.0", or empty. */
export function parseGoals(raw: unknown): number | null {
  if (raw == null || raw === '') return null;
  const n = typeof raw === 'number' ? raw : Number(String(raw).trim());
  return Number.isFinite(n) ? n : null;
}
