/**
 * Context
 * -------
 * Team-name and date normalization for the Brazilian Soccer MCP server.
 *
 * The source datasets disagree on how they spell the same team:
 *   - state suffix glued with a hyphen:  "Palmeiras-SP", "Vasco da Gama-RJ"
 *   - state suffix with spaced dash:     "América - MG"
 *   - state suffix glued with a space:   "America MG"
 *   - country code in parentheses:       "Nacional (URU)"
 *   - country code with a hyphen:        "Barcelona-EQU"
 *   - bare name, sometimes unaccented:   "Flamengo", "Sao Paulo", "Grêmio"
 *
 * Dates likewise come in three shapes: ISO ("2023-09-24"), ISO-with-time
 * ("2012-05-19 18:30:00") and Brazilian ("29/03/2003").
 *
 * This module provides:
 *   - `parseTeam`   : split a raw team string into { base, suffix, displayBase }
 *                     plus folded comparison keys.
 *   - `teamMatches` : suffix-aware identity matching used for grouping and
 *                     "team = X" queries (so Atlético-MG never collapses into
 *                     Atlético-GO).
 *   - `looseMatches`: accent-insensitive substring matching used for free-text
 *                     club / nationality / player lookups.
 *   - `parseDate`   : multi-format date parser returning an ISO date + epoch ms.
 */

/** Fold a string to a lowercase, accent-free, single-spaced comparison form. */
export function foldText(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "") // strip combining diacritics
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .replace(/\s+/g, " ");
}

/** Trailing 2–3 letter state/country code, in any of the observed shapes. */
const SUFFIX_RE = /[\s-]*\(?([A-Za-z]{2,3})\)?\s*$/;

export interface ParsedTeam {
  /** Raw input, untouched (best for display). */
  readonly raw: string;
  /** Display form of the base name with the suffix removed. */
  readonly displayBase: string;
  /** Folded full name (base + suffix), e.g. "atletico mg". */
  readonly fullKey: string;
  /** Folded base name only, e.g. "atletico". */
  readonly baseKey: string;
  /** Folded suffix code if present (state/country), else "". */
  readonly suffix: string;
}

const KNOWN_SUFFIX =
  /^(ac|al|ap|am|ba|ce|df|es|go|ma|mt|ms|mg|pa|pb|pr|pe|pi|rj|rn|rs|ro|rr|sc|sp|se|to|uru|arg|par|bol|chi|col|equ|per|ven|bra|mex)$/;

/**
 * Split a raw team name into base + state/country suffix.
 *
 * A trailing 2–3 letter token is only treated as a suffix when it matches a
 * known Brazilian state UF or South-American country code; otherwise it is kept
 * as part of the name (so "Sport-PE" → base "Sport"/suffix "pe", but a real
 * word is never amputated).
 */
export function parseTeam(raw: string): ParsedTeam {
  const trimmed = raw.trim();
  // Strip a descriptive parenthetical that is NOT a country code,
  // e.g. "Boavista Sport Club (antigo ...) - RJ" or "América FC (Minas Gerais)".
  const withoutParenNote = trimmed.replace(/\s*\([^)]*\)\s*/g, (m) => {
    const inner = foldText(m);
    return KNOWN_SUFFIX.test(inner) ? m : " ";
  });

  let base = withoutParenNote.trim();
  let suffix = "";

  const match = SUFFIX_RE.exec(base);
  if (match && match[1]) {
    const candidate = foldText(match[1]);
    if (KNOWN_SUFFIX.test(candidate)) {
      suffix = candidate;
      base = base.slice(0, match.index).trim();
    }
  }

  const baseKey = foldText(base);
  const fullKey = suffix ? `${baseKey} ${suffix}` : baseKey;
  return { raw: trimmed, displayBase: base || trimmed, fullKey, baseKey, suffix };
}

/**
 * Suffix-aware team identity match.
 *
 * - If the query carries a suffix, require the same base AND suffix.
 * - Otherwise the query base must equal the candidate base, or be a
 *   leading-word prefix of it, so "Vasco" matches "Vasco da Gama-RJ" while
 *   "Paulo" does not match "São Paulo-SP" and "Gama" does not match
 *   "Vasco da Gama".
 */
export function teamMatches(query: string, candidate: string): boolean {
  const q = parseTeam(query);
  const c = parseTeam(candidate);
  if (!q.baseKey) return false;

  if (q.suffix) {
    return q.baseKey === c.baseKey && q.suffix === c.suffix;
  }

  return q.baseKey === c.baseKey || c.baseKey.startsWith(`${q.baseKey} `);
}

/** Accent-insensitive substring match for free-text lookups (clubs, names). */
export function looseMatches(query: string, candidate: string): boolean {
  const q = foldText(query);
  if (!q) return false;
  return foldText(candidate).includes(q);
}

export interface ParsedDate {
  /** ISO calendar date, "YYYY-MM-DD". */
  readonly iso: string;
  /** Epoch milliseconds at UTC midnight of that date (for sorting/ranges). */
  readonly epoch: number;
  /** Calendar year. */
  readonly year: number;
}

/**
 * Parse the three date shapes used across the datasets. Returns `undefined`
 * for blank or unrecognizable values rather than throwing, so a few bad rows
 * never abort a whole load.
 */
export function parseDate(value: string | undefined | null): ParsedDate | undefined {
  if (!value) return undefined;
  const raw = value.trim();
  if (!raw) return undefined;

  // ISO, optionally with a time component: "2023-09-24" / "2012-05-19 18:30:00"
  const iso = /^(\d{4})-(\d{2})-(\d{2})/.exec(raw);
  if (iso) {
    return makeDate(Number(iso[1]), Number(iso[2]), Number(iso[3]));
  }

  // Brazilian "DD/MM/YYYY", optionally with time.
  const br = /^(\d{1,2})\/(\d{1,2})\/(\d{4})/.exec(raw);
  if (br) {
    return makeDate(Number(br[3]), Number(br[2]), Number(br[1]));
  }

  return undefined;
}

function makeDate(year: number, month: number, day: number): ParsedDate | undefined {
  if (!year || !month || !day) return undefined;
  const epoch = Date.UTC(year, month - 1, day);
  if (Number.isNaN(epoch)) return undefined;
  const iso = `${String(year).padStart(4, "0")}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
  return { iso, epoch, year };
}
