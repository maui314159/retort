/**
 * Brazilian Soccer MCP Server — Team Name Normalization
 * -----------------------------------------------------------------------------
 * Context block:
 *   The six datasets use inconsistent team naming:
 *     • "Palmeiras-SP" / "Palmeiras"           (state suffix optional)
 *     • "Atletico-MG", "Atletico-GO", "Atletico-PR" — THREE different clubs
 *       (Atlético Mineiro, Atlético Goianiense, Athletico Paranaense) sharing
 *       the base name "Atletico". The state suffix is IDENTITY, not noise:
 *       stripping it merges distinct clubs.
 *     • "Nacional (URU)" / "Barcelona-EQU"     (country parens, Libertadores)
 *     • "Sport Club Corinthians Paulista"      (long form → short alias)
 *     • Accented vs not: "Atlético-MG" / "Atletico-MG"; "Athletico-PR" /
 *       "Atletico-PR" (Athletico Paranaense) — same club spelled differently
 *       across the modern and historical Brasileirão files.
 *
 *   Two separate concerns:
 *
 *     1. CANONICAL NAME (identity) — `normalizeTeamName(raw, state?)`:
 *        strip trailing `(COUNTRY)`; split a trailing `-UF` / ` - UF` suffix
 *        (falling back to the `state` arg when the raw name has none); expand
 *        long-form base names via BASE_ALIASES; re-append `-UF`; then unify
 *        spelling/accent via FULL_ALIASES. Result keeps the suffix so clubs
 *        sharing a base stay distinct, and is stable across sources:
 *          "Flamengo-RJ" / "Flamengo"+"RJ"  → "Flamengo-RJ"
 *          "Atletico-MG"                    → "Atlético-MG"
 *          "Atletico-GO"                    → "Atlético-GO"  (distinct from -MG)
 *          "Atletico-PR" / "Athletico-PR"   → "Athletico-PR" (unified)
 *          "Sao Paulo-SP"                   → "São Paulo-SP"
 *
 *     2. TOLERANT MATCHING — `teamKey`/`teamMatches`: lowercase, accent-stripped,
 *        punctuation-flattened, substring-either-way. A user asking for
 *        "Flamengo" matches the stored "Flamengo-RJ"; "Atletico-MG" matches
 *        only "Atlético-MG"; a bare "Atletico" matches all Atleticos.
 *
 *   Grouping (standings, head-to-head) groups by `teamKey` of the canonical
 *   name, so distinct clubs never collapse and a club is stable across sources.
 */

/** Long-form base names → short form, keyed by folded (accent-stripped,
 *  lowercased) base. Applied to the suffix-stripped base before re-appending
 *  the state, so the state is preserved on the short form. */
const BASE_ALIASES: Record<string, string> = {
  "sport club corinthians paulista": "Corinthians",
  "corinthians paulista": "Corinthians",
  "sc corinthians paulista": "Corinthians",
  "sport club internacional": "Internacional",
  "gremio foot-ball porto-alegrense": "Grêmio",
  "grêmio foot-ball porto-alegrense": "Grêmio",
  "são paulo futebol clube": "São Paulo",
  "sao paulo futebol clube": "São Paulo",
  "club de regatas do flamengo": "Flamengo",
  "clube de regatas do flamengo": "Flamengo",
  "fluminense football club": "Fluminense",
  "club de regatas vasco da gama": "Vasco da Gama",
  "clube de regatas vasco da gama": "Vasco da Gama",
  "club athletico paranaense": "Athletico-PR",
  "clube athletico paranaense": "Athletico-PR",
  "athletico paranaense": "Athletico-PR",
  "clube atlético mineiro": "Atlético-MG",
  "club atletico mineiro": "Atlético-MG",
  "atletico mineiro": "Atlético-MG",
  "atlético mineiro": "Atlético-MG",
  "atletico goianiense": "Atlético-GO",
  "atlético goianiense": "Atlético-GO",
  "esporte clube bahia": "Bahia",
  "bahia de feira": "Bahia de Feira",
};

/** Spelling/accent unification on the FULL canonical name (base + suffix),
 *  keyed by `teamKey` (folded + alphanumeric-stripped). Applied last so display
 *  is consistent regardless of which source/spelling produced the name. */
const FULL_ALIASES: Record<string, string> = {
  // Athletico Paranaense: modern "Atletico-PR" and historical "Athletico-PR".
  atleticopr: "Athletico-PR",
  athleticopr: "Athletico-PR",
  // Atlético Mineiro / Goianiense: unify accent on display.
  atleticomg: "Atlético-MG",
  atleticogo: "Atlético-GO",
  // Common accented club names (modern file is unaccented).
  saopaulosp: "São Paulo-SP",
  gremiors: "Grêmio-RS",
  avaisc: "Avaí-SC",
  cearace: "Ceará-CE",
  goiasgo: "Goiás-GO",
  vitoriaba: "Vitória-BA",
  vitoriaes: "Vitória-ES",
  saocarlosp: "São Carlos-SP",
};

const STATE_ABBREVS = new Set([
  "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
  "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
  "SP", "SE", "TO",
]);

/** Strip a trailing ` - UF` or `-UF` state suffix; return {base, uf}. */
function splitSuffix(name: string): { base: string; uf: string | null } {
  let m = name.match(/\s+-\s+([A-Z]{2})\s*$/);
  if (m && STATE_ABBREVS.has(m[1])) {
    return { base: name.slice(0, m.index).trim(), uf: m[1] };
  }
  m = name.match(/-([A-Z]{2})\s*$/);
  if (m && STATE_ABBREVS.has(m[1])) {
    return { base: name.slice(0, m.index).trim(), uf: m[1] };
  }
  return { base: name, uf: null };
}

/** Strip a trailing `(COUNTRY)` annotation, e.g. "Nacional (URU)" → "Nacional". */
function stripCountryParens(name: string): string {
  const m = name.match(/\s*\([A-Z]{3}\)\s*$/);
  return m ? name.slice(0, m.index).trim() : name;
}

/** Accent-stripped lowercase, for alias-map lookup keys. */
function fold(s: string): string {
  return s
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

/**
 * Canonical, disambiguating team name. Keeps the `-UF` state suffix (from the
 * raw name, or from `state` when absent) so clubs sharing a base stay distinct;
 * expands long-form names; unifies spelling/accent across sources.
 */
export function normalizeTeamName(raw: string, state?: string | null): string {
  if (!raw) return "";
  let n = raw.trim();
  n = stripCountryParens(n);
  let { base, uf } = splitSuffix(n);
  uf = uf ?? state ?? null;

  // Long-form base expansion (also try base WITH suffix, for cup data).
  const bk = fold(base);
  if (BASE_ALIASES[bk]) {
    base = BASE_ALIASES[bk];
  } else if (uf) {
    const bsk = fold(`${base}-${uf}`);
    if (BASE_ALIASES[bsk]) {
      const r = BASE_ALIASES[bsk];
      const sp = splitSuffix(r);
      base = sp.base;
      uf = sp.uf ?? uf;
    }
  }

  let candidate = uf ? `${base}-${uf}` : base;
  // Spelling/accent unification on the full canonical name.
  candidate = FULL_ALIASES[teamKey(candidate)] ?? candidate;
  return candidate;
}

/**
 * Comparison key for a team name: lowercase, accents stripped, non-alphanumeric
 * removed. For equality/grouping only — never for display.
 */
export function teamKey(name: string): string {
  return fold(name).replace(/[^a-z0-9]/g, "").trim();
}

/** True iff two team names refer to the same club. */
export function sameTeam(a: string, b: string): boolean {
  return teamKey(a) === teamKey(b);
}

/** Does `candidate` match `query` under tolerant normalization? Substring
 *  either way: "Flamengo" matches "Flamengo-RJ"; "Atletico-MG" matches only
 *  "Atlético-MG"; a bare "Atletico" matches all Atleticos. */
export function teamMatches(query: string, candidate: string): boolean {
  const qk = teamKey(query);
  const ck = teamKey(candidate);
  if (!qk || !ck) return false;
  if (qk === ck) return true;
  return ck.includes(qk) || qk.includes(ck);
}
