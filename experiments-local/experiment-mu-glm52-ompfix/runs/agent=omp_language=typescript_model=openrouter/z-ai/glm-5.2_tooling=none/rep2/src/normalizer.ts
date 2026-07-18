/**
 * Brazilian Soccer MCP Server — team-name normaliser
 * ---------------------------------------------------
 * Context block:
 *   The five match datasets spell team names inconsistently:
 *     - "Palmeiras-SP" (state suffix)        [Brasileirão]
 *     - "Flamengo - RJ" (spaced suffix)      [Copa do Brasil]
 *     - "Flamengo"                            [Libertadores]
 *     - "Sao Paulo" (ASCII, no accents)       [BR-Football]
 *     - "São Paulo" (UTF-8, accented)         [histórico]
 *   Queries must match across all of these.
 *
 *   Strategy: `teamKey` keeps any state suffix in the key (so "Atletico-PR"
 *   and "Atletico-MG" stay distinct), de-accents and lowercases. An explicit
 *   ALIASES table then collapses spelling/suffix variants onto a single
 *   canonical key per club (e.g. "flamengo_rj" → "flamengo", "atletico_pr" →
 *   "athletico_pr"). Bare names without an alias pass through unchanged, so a
 *   canonical key like "flamengo" used directly in fixtures matches the
 *   aliased "flamengo_rj" from real data.
 *
 *   The display form (`teamDisplay`) strips the suffix and keeps accents so
 *   user-facing output reads naturally ("São Paulo" not "sao paulo").
 */

/** De-accent and lowercase. */
export function deaccent(s: string): string {
  return s
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

/** Canonical key: de-accented, lowercased, non-alphanumerics → single spaces → underscores. */
export function teamKey(name: string): string {
  const de = deaccent(name);
  return de
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .replace(/\s+/g, "_");
}

/**
 * Curated alias map. Keys are the raw `teamKey()` output of names appearing in
 * the datasets; values are the canonical key every variant collapses onto.
 * Suffixed forms map to a bare canonical key, EXCEPT where the suffix
 * disambiguates two clubs sharing a base name (Atletico-PR vs Atletico-MG,
 * Botafogo-RJ vs Botafogo-SP), where the suffix is retained in the canonical
 * key.
 */
const ALIASES: Record<string, string> = {
  // Suffix-bearing forms → bare canonical (single club per base name).
  palmeiras_sp: "palmeiras",
  flamengo_rj: "flamengo",
  fluminense_rj: "fluminense",
  vasco_rj: "vasco",
  vasco_da_gama: "vasco",
  internacional_rs: "internacional",
  gremio_rs: "gremio",
  sao_paulo_sp: "sao_paulo",
  coritiba_pr: "coritiba",
  cuiaba_mt: "cuiaba",
  goias_go: "goias",
  ceara_ce: "ceara",
  fortaleza_ce: "fortaleza",
  juventude_rs: "juventude",
  sport_pe: "sport",
  sport_recife: "sport",
  santos_sp: "santos",
  corinthians_sp: "corinthians",
  bahia_ba: "bahia",
  cruzeiro_mg: "cruzeiro",
  atletico_go: "atletico_go",
  atletico_goianiense: "atletico_go",

  // Disambiguated clubs: suffix kept in the canonical key.
  atletico_pr: "athletico_pr",
  athletico_pr: "athletico_pr",
  atletico_mg: "atletico_mg",
  atletico_mineiro: "atletico_mg",
  botafogo_rj: "botafogo",
  botafogo_sp: "botafogo_sp",
  america_mg: "america_mg",
  america_rn: "america_rn",
  america_ce: "america_ce",
};

/** Canonical key for a team name, applying the alias table. */
export function canonicalTeamKey(name: string): string {
  const k = teamKey(name);
  return ALIASES[k] ?? k;
}

/** Strip a trailing "-XX"/" - XX" state suffix for display purposes. */
function stripStateSuffix(name: string): string {
  return name.replace(/\s*-\s*([A-Z]{2})\s*$/, "").trim();
}

/** Display name: suffix-stripped, trimmed; keeps accents as in the input. */
export function teamDisplay(name: string): string {
  return stripStateSuffix(name).trim();
}
