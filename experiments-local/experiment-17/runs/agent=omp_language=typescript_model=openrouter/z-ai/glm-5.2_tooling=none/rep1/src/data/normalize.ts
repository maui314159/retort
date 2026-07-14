/**
 * Brazilian Soccer MCP Server — Team-name normalization.
 *
 * Context block
 * -------------
 * The six source CSVs use wildly inconsistent team naming:
 *   - With state suffix:        "Palmeiras-SP", "Flamengo-RJ", "Botafogo-RJ"
 *   - Official long names:      "Atlético Mineiro", "Athletico Paranaense",
 *                               "Sport Club Corinthians Paulista", "EC Bahia"
 *   - Without accents:          "Sao Paulo", "Atletico Mineiro" (BR-Football)
 *   - With accents:             "São Paulo", "Atlético-MG" (other files)
 *   - Ambiguous base names:     "Atletico-MG" vs "Atletico-PR" — two different
 *                               clubs (Atlético Mineiro vs Athletico Paranaense)
 *                               that share the base "Atletico" once the state
 *                               suffix is stripped.
 *
 * No single text rule (strip suffix / keep suffix) reconciles all of these, so
 * normalization is driven by a curated `CANONICAL_CLUBS` alias table that maps
 * every known variant of the Brazilian Série A/Série B regulars to one
 * canonical display name. Variants are matched on an accent-free, lowercased,
 * punctuation-collapsed key. Names not in the table fall back to a tolerant
 * clean (parentheticals removed, case normalized) so that identical strings
 * still merge without inventing false equivalences.
 */

const ACCENT_STRIP = /[\u0300-\u036f]/g;

/**
 * Canonical club definitions. Each entry's `aliases` are the aliasKey() forms
 * of every known variant; all resolve to `display`. Order is irrelevant — the
 * lookup map is built once at module load.
 */
const CANONICAL_CLUBS: { display: string; aliases: string[] }[] = [
  { display: "Flamengo", aliases: ["flamengo", "flamengo rj", "clube de regatas do flamengo"] },
  { display: "Fluminense", aliases: ["fluminense", "fluminense rj", "fluminense rj"] },
  { display: "Vasco da Gama", aliases: ["vasco da gama", "vasco da gama rj", "vasco", "vasco rj", "vasco da gama rj"] },
  { display: "Botafogo", aliases: ["botafogo", "botafogo rj", "botafogo rj"] },
  { display: "Corinthians", aliases: ["corinthians", "corinthians sp", "sport club corinthians paulista", "corinthians paulista"] },
  { display: "Palmeiras", aliases: ["palmeiras", "palmeiras sp", "sociedade esportiva palmeiras"] },
  { display: "São Paulo", aliases: ["sao paulo", "sao paulo sp", "sao paulo fc", "sao paulo futebol clube"] },
  { display: "Santos", aliases: ["santos", "santos sp", "santos fc"] },
  { display: "Grêmio", aliases: ["gremio", "gremio rs", "gremio foot ball porto alegrense"] },
  { display: "Internacional", aliases: ["internacional", "internacional rs", "sport club internacional", "sc internacional"] },
  { display: "Atlético Mineiro", aliases: ["atletico mg", "atletico mineiro", "atlético mineiro"] },
];
// (The list above is extended programmatically below; kept here for readability.)

/** Additional canonical clubs beyond the seed list. */
const EXTRA_CLUBS: { display: string; aliases: string[] }[] = [
  { display: "Atlético Mineiro", aliases: ["atletico mg", "atletico mineiro"] },
  { display: "Athletico Paranaense", aliases: ["atletico pr", "atletico paranaense", "athletico paranaense", "athletico pr", "club athletico paranaense"] },
  { display: "Atlético Goianiense", aliases: ["atletico go", "atletico goianiense", "atlético goianiense"] },
  { display: "Coritiba", aliases: ["coritiba", "coritiba pr"] },
  { display: "Ceará", aliases: ["ceara", "ceara ce", "ceará sc"] },
  { display: "Fortaleza", aliases: ["fortaleza", "fortaleza ce", "fortaleza fc", "fortaleza ec", "fortaleza ce"] },
  { display: "Bahia", aliases: ["bahia", "bahia ba", "ec bahia", "esporte clube bahia"] },
  { display: "Vitória", aliases: ["vitoria", "vitoria ba", "ec vitoria", "esporte clube vitoria"] },
  { display: "Sport", aliases: ["sport", "sport pe", "sport recife", "sport club do recife"] },
  { display: "Santa Cruz", aliases: ["santa cruz", "santa cruz pe", "santa cruz fc"] },
  { display: "Náutico", aliases: ["nautico", "nautico pe", "nautico capibaribe", "clube nautico capibaribe"] },
  { display: "Cruzeiro", aliases: ["cruzeiro", "cruzeiro mg", "cruzeiro ec"] },
  { display: "América Mineiro", aliases: ["america mg", "america mineiro", "america fc mg"] },
  { display: "América (RN)", aliases: ["america rn", "america fc natal", "america rn"] },
  { display: "Goiás", aliases: ["goias", "goias go", "goiás ec", "goiás"] },
  { display: "Chapecoense", aliases: ["chapecoense", "chapecoense sc", "associacao chapecoense de futebol"] },
  { display: "Avaí", aliases: ["avai", "avai sc", "avai futebol clube"] },
  { display: "Criciúma", aliases: ["criciuma", "criciuma sc", "criciúma ec"] },
  { display: "Figueirense", aliases: ["figueirense", "figueirense sc"] },
  { display: "Joinville", aliases: ["joinville", "joinville sc", "joinville ec"] },
  { display: "Paraná", aliases: ["parana", "parana pr", "parana clube"] },
  { display: "CSA", aliases: ["csa", "csa al", "cs alagoano", "centro sportivo alagoano"] },
  { display: "Cuiabá", aliases: ["cuiaba", "cuiaba mt", "cuiaba ec", "cuiabá ec"] },
  { display: "Juventude", aliases: ["juventude", "juventude rs", "ec juventude", "esporte clube juventude"] },
  { display: "Red Bull Bragantino", aliases: ["bragantino", "red bull bragantino", "red bull bragantino sp", "rb bragantino", "red bull brasil"] },
  { display: "Ponte Preta", aliases: ["ponte pretta", "ponte preta", "ponte preta sp", "associacao atlética ponte preta"] },
  { display: "Portuguesa", aliases: ["portuguesa", "portuguesa sp", "portuguesa desportos", "associacao portuguesa de desportos"] },
  { display: "Guarani", aliases: ["guarani", "guarani sp", "guarani futebol clube"] },
  { display: "Santo André", aliases: ["santo andre", "santo andre sp", "esporte clube santo andre"] },
  { display: "São Caetano", aliases: ["sao caetano", "sao caetano sp", "ad sao caetano"] },
  { display: "Paysandu", aliases: ["paysandu", "paysandu pa", "paysandu sport club"] },
  { display: "Brasiliense", aliases: ["brasiliense", "brasiliense df", "brasiliense fc"] },
  { display: "Barueri", aliases: ["barueri", "barueri sp", "grêmio barueri", "gremio prudente", "grêmio prudente"] },
  { display: "Ipatinga", aliases: ["ipatinga", "ipatinga mg", "ipatinga fc"] },
  { display: "Náutico (RR)" , aliases: ["nautico rr"] },
  { display: "ABC", aliases: ["abc", "abc fc", "abc natal"] },
  { display: "CRB", aliases: ["crb", "crb al", "clube de regatas brasil"] },
  { display: "Botafogo (PB)", aliases: ["botafogo pb"] },
  { display: "Botafogo (SP)", aliases: ["botafogo sp"] },
  { display: "America-RJ", aliases: ["americano rj", "americano fc rj"] },
  { display: "Operário (PR)", aliases: ["operario pr", "operario ferroviario ec"] },
  { display: "Operário (MS)", aliases: ["operario ms", "operario fc ms"] },
];

// Merge seed + extra, deduping alias collisions in favor of the first definition.
const ALIAS_TO_CANONICAL: Map<string, string> = (() => {
  const map = new Map<string, string>();
  for (const club of [...CANONICAL_CLUBS, ...EXTRA_CLUBS]) {
    for (const alias of club.aliases) {
      if (!map.has(alias)) map.set(alias, club.display);
    }
  }
  return map;
})();

/**
 * Compute a stable alias key: accent-free, lowercased, parentheticals removed,
 * all non-alphanumeric runs collapsed to single spaces. Used both for curated
 * alias lookup and for the fallback identity map.
 */
export function aliasKey(raw: string): string {
  let s = (raw ?? "").normalize("NFD").replace(ACCENT_STRIP, "").toLowerCase();
  s = s.replace(/\s*\([^)]*\)\s*/g, " ");
  s = s.replace(/[^a-z0-9]+/g, " ").trim();
  return s.replace(/\s+/g, " ");
}

/** Backwards-compatible alias kept for callers that want an accent-free key. */
export function deaccent(s: string): string {
  return s.normalize("NFD").replace(ACCENT_STRIP, "");
}

/**
 * Remove parenthetical segments and a trailing two-letter state/country suffix
 * from a raw team name. Used only for the fallback display path; curated clubs
 * bypass this entirely.
 */
export function cleanTeamName(raw: string): string {
  let s = (raw ?? "").trim();
  s = s.replace(/\s*\([^)]*\)\s*/g, " ").trim();
  s = s.replace(/\s*-\s*[A-Za-z]{2,3}$/, "").trim();
  return s.replace(/\s+/g, " ");
}

/** Accent-free lowercase key (legacy helper). Prefer aliasKey for matching. */
export function teamKey(raw: string): string {
  return deaccent(cleanTeamName(raw)).toLowerCase().trim();
}

/** Title-case a cleaned name, preserving known uppercase tokens. */
export function displayCase(cleaned: string): string {
  const upper = new Set(["FC", "EC", "SC", "SP", "RJ", "MG", "AC", "PA", "BA", "GO", "RS", "PR", "CE"]);
  return cleaned
    .split(/\s+/)
    .map((w) => {
      if (upper.has(w.toUpperCase())) return w.toUpperCase();
      if (w.length <= 4 && w === w.toUpperCase() && /[A-Z]/.test(w)) return w;
      return w.charAt(0).toUpperCase() + w.slice(1).toLowerCase();
    })
    .join(" ");
}

/**
 * Registry mapping every observed team name to a canonical display name.
 * Curated clubs resolve via ALIAS_TO_CANONICAL; everything else falls back to
 * a cleaned, title-cased form stored under its aliasKey so identical strings
 * still merge.
 */
export class TeamRegistry {
  private fallbackByKey = new Map<string, string>();

  /** Register a raw team name; returns the canonical display name. */
  register(raw: string): string {
    const key = aliasKey(raw);
    if (!key) return raw.trim();
    const curated = ALIAS_TO_CANONICAL.get(key);
    if (curated) return curated;
    const existing = this.fallbackByKey.get(key);
    if (existing) return existing;
    const display = displayCase(cleanTeamName(raw));
    this.fallbackByKey.set(key, display);
    return display;
  }

  /** Resolve a raw name to its canonical display name (registering if new). */
  resolve(raw: string): string {
    return this.register(raw);
  }

  /** Look up the canonical display name without registering. */
  lookup(raw: string): string | undefined {
    const key = aliasKey(raw);
    if (!key) return undefined;
    return ALIAS_TO_CANONICAL.get(key) ?? this.fallbackByKey.get(key);
  }

  /** All known canonical display names. */
  all(): string[] {
    const set = new Set<string>();
    for (const d of ALIAS_TO_CANONICAL.values()) set.add(d);
    for (const d of this.fallbackByKey.values()) set.add(d);
    return [...set];
  }

  /** True if a raw name maps to a known team. */
  has(raw: string): boolean {
    const key = aliasKey(raw);
    return !!key && (ALIAS_TO_CANONICAL.has(key) || this.fallbackByKey.has(key));
  }
}
