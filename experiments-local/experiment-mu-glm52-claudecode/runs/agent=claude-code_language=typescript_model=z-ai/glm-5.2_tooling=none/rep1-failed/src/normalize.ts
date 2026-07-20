/**
 * Brazilian Soccer MCP Server — normalization helpers
 * ===================================================
 * Context block:
 *   The five match datasets use incompatible naming conventions for the same
 *   clubs (state suffixes like "Palmeiras-SP", parenthetical annotations like
 *   "Nacional (URU)", and multiple date formats — ISO, ISO+time, and Brazilian
 *   DD/MM/YYYY). This module provides the pure functions that flatten those
 *   differences into stable lookup keys and `Date` objects so the query engine
 *   can join records across files.
 *
 *   All functions are deterministic and side-effect free; they are exercised
 *   directly by the BDD scenarios in `tests/bdd.test.ts`.
 */

import type { MatchRecord, PlayerRecord, TeamRef } from './types.js';

/** Canonical competition labels used throughout the query layer. */
export const COMPETITIONS = {
  BRASILEIRAO: 'Brasileirão',
  COPA_DO_BRASIL: 'Copa do Brasil',
  LIBERTADORES: 'Libertadores',
  SERIE_B: 'Série B',
  SERIE_C: 'Série C',
} as const;

/** Strip combining diacritics, so "São Paulo" → "Sao Paulo". */
export function stripAccents(s: string): string {
  if (!s) return '';
  return s.normalize('NFD').replace(/[̀-ͯ]/g, '');
}

/**
 * Parse a raw team name into a stable display name and a lookup key.
 *
 * Handles:
 *   - state suffixes:        "Palmeiras-SP", "América - MG", "Atletico-GO"
 *   - parenthetical notes:   "Nacional (URU)", "Boavista Sport Club (antigo ...)"
 *   - accents and case:      "São Paulo" / "sao paulo" collapse to the same key
 */
export function normalizeTeam(raw: string): { display: string; key: string; state?: string } {
  if (!raw) return { display: '', key: '' };
  let s = String(raw).trim();

  // Capture a trailing state code before stripping it.
  let state: string | undefined;
  const stateMatch = s.match(/-\s*([A-Za-z]{2})\s*$/);
  if (stateMatch) {
    state = stateMatch[1].toUpperCase();
  }

  // Drop parenthetical content (foreign-team markers, historical notes).
  s = s.replace(/\([^)]*\)/g, ' ');
  // Drop trailing "-XX" / "- XX" state suffix.
  s = s.replace(/\s*-\s*[A-Za-z]{2}\s*$/, ' ');
  // Tidy whitespace.
  s = s.replace(/\s+/g, ' ').trim();

  const display = s;
  const key = tokenize(s);
  return { display, key, state };
}

/** Produce the accent-stripped, lowercased, whitespace-collapsed lookup key. */
export function tokenize(s: string): string {
  if (!s) return '';
  let t = stripAccents(s).toLowerCase();
  t = t.replace(/[^\p{L}\p{N}\s]/gu, ' ');
  t = t.replace(/\s+/g, ' ').trim();
  return t;
}

/**
 * Parse a user-supplied team query (e.g. "Flamengo", "atletico-mg", "São Paulo")
 * into a TeamRef. A trailing 2-letter token after a hyphen or space is treated
 * as a state filter.
 */
export function parseTeamRef(raw: string): TeamRef {
  const { display, key, state } = normalizeTeam(raw);
  return { nameKey: key, state, raw: display || raw };
}

/**
 * Decide whether a record team (key + optional state) matches a query TeamRef.
 *
 * Matching is intentionally lenient: an exact key match wins, otherwise we fall
 * back to bidirectional substring containment so that "Corinthians" resolves
 * "Sport Club Corinthians Paulista" and a bare prefix ("Palmeiras") still hits.
 * When the query supplies a state, it must match the record's state.
 */
export function teamMatches(
  recordKey: string,
  recordState: string | undefined,
  query: TeamRef,
): boolean {
  if (!query.nameKey || !recordKey) return false;
  const stateOk = !query.state || (recordState ?? '').toUpperCase() === query.state.toUpperCase();
  if (!stateOk) return false;
  if (recordKey === query.nameKey) return true;
  if (recordKey.includes(query.nameKey)) return true;
  if (query.nameKey.includes(recordKey)) return true;
  return false;
}

/**
 * Parse the heterogeneous date strings across the datasets:
 *   - ISO:        "2023-09-24"
 *   - ISO + time: "2012-05-19 18:30:00"
 *   - Brazilian:  "29/03/2003" or "29/03/2003 16:00"
 * Returns {date, iso} where `iso` is a YYYY-MM-DD string when parseable.
 */
export function parseDate(raw: string): { date: Date | null; iso: string | null } {
  if (!raw) return { date: null, iso: null };
  const s = String(raw).trim();
  if (!s) return { date: null, iso: null };

  const br = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})(.*)$/);
  if (br) {
    const day = br[1].padStart(2, '0');
    const month = br[2].padStart(2, '0');
    const year = br[3];
    let time = br[4].trim();
    if (time && !/\d{2}:\d{2}/.test(time)) time = '';
    const iso = `${year}-${month}-${day}`;
    const dt = new Date(`${iso}T${time || '00:00:00'}`);
    return { date: isNaN(dt.getTime()) ? null : dt, iso };
  }

  // ISO-ish: replace space separator with T for Safari-style safety.
  const normalized = s.replace(' ', 'T');
  const dt = new Date(normalized);
  if (isNaN(dt.getTime())) return { date: null, iso: null };
  const iso = `${dt.getUTCFullYear()}-${String(dt.getUTCMonth() + 1).padStart(2, '0')}-${String(
    dt.getUTCDate(),
  ).padStart(2, '0')}`;
  return { date: dt, iso };
}

/** Coerce a CSV cell to an integer, returning null when blank or non-numeric. */
export function toInt(v: string | undefined): number | null {
  if (v === undefined || v === null) return null;
  const s = String(v).trim();
  if (!s || s.toLowerCase() === 'na') return null;
  const n = Number(s);
  if (!Number.isFinite(n)) return null;
  return Math.trunc(n);
}

/** Coerce a CSV cell to a number (goals may be "1.0" in the BR dataset). */
export function toNum(v: string | undefined): number | null {
  if (v === undefined || v === null) return null;
  const s = String(v).trim();
  if (!s || s.toLowerCase() === 'na') return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

/** Normalize a competition label from a query against a canonical competition. */
export function competitionMatches(recordCompetition: string, query: string | undefined): boolean {
  if (!query) return true;
  const q = tokenize(query);
  const r = tokenize(recordCompetition);
  if (!q) return true;
  if (r === q || r.includes(q) || q.includes(r)) return true;
  // Convenience aliases.
  if ((q === 'brasileirao' || q === 'serie a') &&
      (r.includes('brasileirao') || r === 'serie a')) return true;
  if (q === 'copa do brasil' && r.includes('copa do brasil')) return true;
  if (q === 'libertadores' && r.includes('libertadores')) return true;
  return false;
}

/** A no-op placeholder re-exported for test convenience. */
export type { MatchRecord, PlayerRecord, TeamRef } from './types.js';
