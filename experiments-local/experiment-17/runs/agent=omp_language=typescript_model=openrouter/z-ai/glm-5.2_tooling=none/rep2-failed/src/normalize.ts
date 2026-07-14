/**
 * brazilian-soccer-mcp / src/normalize.ts
 *
 * Name, date and value normalization.
 *
 * Context block:
 * The six datasets spell team and club names in many incompatible ways:
 *   - state suffixes: "Palmeiras-SP", "Botafogo RJ", "Atletico-MG"
 *   - parenthetical countries (Libertadores): "Nacional (URU)"
 *   - full names: "Atletico Mineiro", "Athletico Paranaense"
 *   - accents present in some files, absent in others: "São Paulo" vs "Sao Paulo"
 *   - spelling variants of the same club: "Atletico-PR" vs "Athletico-PR"
 *
 * To match the SAME club across files without MERGING DISTINCT clubs that share
 * a nickname (Atlético-MG vs Atlético-GO vs Athletico-PR; Botafogo-RJ vs
 * Botafogo-PB; América-MG vs América-RN) we split each name into a `core`
 * (accent/diacritic-free, parenthetical- and state-suffix-stripped, with known
 * full names folded to their short form) and a `state` (from a state column, a
 * trailing suffix, or a parenthetical country). The loader then does a two-pass
 * resolution: a core seen with only one state is "unambiguous" and keyed by its
 * bare core (so "Flamengo-RJ" and "Flamengo" both key to "flamengo"); a core
 * seen with multiple states is "ambiguous" and keyed as `core-state` (so
 * "atletico-mg" and "atletico-go" stay distinct). Query matching is done on the
 * `core`, with an optional state filter for precision.
 */

import type { PositionGroup } from "./types.js";

/** Matches a trailing state/country suffix: "-SP", " - RJ", " RJ" (2 letters). */
const TRAILING_STATE = /[\s-]+([A-Za-z]{2})$/;
/** Matches a parenthetical 2-3 letter country code: "(URU)", "(EQU)". */
const PAREN_COUNTRY = /\(([A-Za-z]{2,3})\)/;

/** Full-name → {core, state?} aliases (lowercased, diacritics-stripped). */
const FULL_NAME_ALIASES: Record<string, { core: string; state?: string }> = {
  "atletico mineiro": { core: "atletico", state: "MG" },
  "atletico goianiense": { core: "atletico", state: "GO" },
  "atletico paranaense": { core: "atletico", state: "PR" },
  "athletico paranaense": { core: "atletico", state: "PR" },
  athletico: { core: "atletico" }, // bare token -> same core as "atletico"
  "america mineiro": { core: "america", state: "MG" },
  "america fc natal": { core: "america", state: "RN" },
  "america f c natal": { core: "america", state: "RN" },
  "sport club do recife": { core: "sport", state: "PE" },
  "sport recife": { core: "sport", state: "PE" },
};
/** Normalize a competition label to a canonical form (e.g. "Serie A" → "Brasileirão"). */
export function canonicalCompetition(raw: string): string {
  const t = (raw ?? "").trim();
  if (/^s[ée]rie\s*a$/i.test(t)) return "Brasileirão";
  if (/^s[ée]rie\s*b$/i.test(t)) return "Brasileirão Série B";
  if (/^s[ée]rie\s*c$/i.test(t)) return "Brasileirão Série C";
  if (/^copa\s*do\s*brasil$/i.test(t)) return "Copa do Brasil";
  if (/libertadores/i.test(t)) return "Libertadores";
  return t;
}

/** Strip diacritics by NFD decomposition + combining-mark removal. */
export function stripDiacritics(s: string): string {
  return s.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

/** Remove parenthetical content (including nested). */
function stripParens(s: string): string {
  let out = s;
  let prev: string;
  do {
    prev = out;
    out = out.replace(/\([^()]*\)/g, "");
  } while (out !== prev);
  return out;
}

/** Extract a 2-letter state from a trailing suffix, or null. */
function extractTrailingState(s: string): string | null {
  const m = s.match(TRAILING_STATE);
  return m && m[1] ? m[1].toUpperCase() : null;
}

export interface NameParts {
  /** Canonical short core (lowercased, diacritics stripped), e.g. "atletico". */
  core: string;
  /** Resolved state/country code (uppercase) or null. */
  state: string | null;
  /** Human-readable display name (state suffix/parentheticals trimmed, accents kept). */
  display: string;
}

/**
 * Split a team name into core + state + display.
 * `stateCol` is an explicit state column value (Brazilian files), used in
 * preference to a suffix when present.
 */
export function extractParts(name: string, stateCol?: string | null): NameParts {
  const trimmed = (name ?? "").trim();

  // Parenthetical country (Libertadores), captured before stripping.
  const parenMatch = trimmed.match(PAREN_COUNTRY);
  const parenCountry = parenMatch && parenMatch[1] ? parenMatch[1].toUpperCase() : null;

  // Display name: strip parens + trailing state suffix, keep accents/case.
  let display = stripParens(trimmed).trim();
  const displayState = extractTrailingState(display);
  if (displayState) display = display.replace(TRAILING_STATE, "").trim();
  display = display.replace(/\s+/g, " ").trim();

  // Core: lowercase, diacritics stripped, parens + trailing state removed.
  let base = stripDiacritics(stripParens(trimmed).toLowerCase());
  const trailing = extractTrailingState(base);
  if (trailing) base = base.replace(TRAILING_STATE, "").trim();
  base = base.replace(/\s+/g, " ").trim();
  const alias = FULL_NAME_ALIASES[base];
  const core = alias ? alias.core : base;
  const aliasState = alias?.state ?? null;

  // State resolution: explicit column > trailing suffix > paren country > alias.
  const colState =
    stateCol && /^[A-Za-z]{2}$/.test(stateCol.trim()) ? stateCol.trim().toUpperCase() : null;
  const state = colState ?? trailing ?? parenCountry ?? aliasState;

  return { core, state, display };
}

/**
 * Resolve a club key from core + state, given whether the core is ambiguous
 * (seen with multiple states) and the majority state for fallback.
 */
export function resolveClubKey(
  core: string,
  state: string | null,
  ambiguous: boolean,
  majorityState: string | null,
): string {
  if (!ambiguous) return core;
  const s = state ?? majorityState ?? "X";
  return `${core}-${s.toLowerCase()}`;
}

/** Core portion of a club key (inverse of resolveClubKey for matching). */
export function clubKeyCore(clubKey: string): string {
  const i = clubKey.lastIndexOf("-");
  // Only split off a trailing 2-letter state segment.
  if (i > 0 && clubKey.length - i - 1 <= 3) return clubKey.slice(0, i);
  return clubKey;
}

/**
 * Backwards-compatible bare key (core only). Kept for simple equality use and
 * tests; query matching in the store uses core-based comparison.
 */
export function teamKey(name: string): string {
  return extractParts(name).core;
}

/** Human-readable display name (state suffix/parentheticals trimmed, accents kept). */
export function teamDisplay(name: string): string {
  return extractParts(name).display;
}

/** Parse a date string from any supported format into ISO `YYYY-MM-DD`. */
export function parseDate(raw: string | null | undefined): string | null {
  if (raw == null) return null;
  const s = String(raw).trim();
  if (s === "") return null;

  const iso = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (iso && iso[1] && iso[2] && iso[3]) {
    return `${iso[1]}-${iso[2]}-${iso[3]}`;
  }

  const br = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (br && br[1] && br[2] && br[3]) {
    return `${br[3]}-${br[2].padStart(2, "0")}-${br[1].padStart(2, "0")}`;
  }

  return null;
}

/** Extract a 4-digit season/year from a value (number or numeric string). */
export function parseSeason(value: unknown): number | null {
  if (value == null || value === "") return null;
  const n = typeof value === "number" ? value : Number(String(value).trim());
  return Number.isFinite(n) && n >= 1900 && n <= 2100 ? Math.trunc(n) : null;
}

/** Best-effort integer parse; returns null for blanks/non-numbers. */
export function toInt(value: unknown): number | null {
  if (value == null || value === "") return null;
  if (typeof value === "number") return Number.isFinite(value) ? Math.trunc(value) : null;
  const s = String(value).trim();
  if (s === "") return null;
  const n = Number(s);
  return Number.isFinite(n) ? Math.trunc(n) : null;
}

/** Best-effort float parse; returns null for blanks/non-numbers. */
export function toFloat(value: unknown): number | null {
  if (value == null || value === "") return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  const s = String(value).trim();
  if (s === "") return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

/** Lowercase, diacritic-stripped comparison key for free-text fields. */
export function textKey(s: string): string {
  return stripDiacritics(s).toLowerCase().trim();
}

/** Map a FIFA position code to a coarse position group. */
export function positionGroupOf(position: string): PositionGroup | null {
  const p = position.toUpperCase().trim();
  if (p === "GK") return "goalkeeper";
  if (["CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"].includes(p)) return "defender";
  if (["CDM", "CM", "CAM", "LM", "RM", "LDM", "RDM", "LCM", "RCM", "LAM", "RAM"].includes(p))
    return "midfielder";
  if (["ST", "LS", "RS", "LW", "RW", "LF", "CF", "RF"].includes(p)) return "forward";
  return null;
}
