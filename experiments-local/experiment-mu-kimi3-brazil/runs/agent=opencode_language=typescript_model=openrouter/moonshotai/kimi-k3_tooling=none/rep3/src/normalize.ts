/**
 * Normalization utilities: team names, dates, and competition labels.
 *
 * The six source CSVs use wildly different naming conventions
 * ("Palmeiras-SP", "Palmeiras - SP", "Palmeiras", "São Paulo", "Sao Paulo",
 * "Sport Club Corinthians Paulista", ...). This module maps every raw name
 * to a canonical slug key plus a friendly display name so that all sources
 * join together correctly.
 */

import type { CompetitionLabel, TeamRef } from "./types.js";

/* ------------------------------------------------------------------ */
/* Low-level string helpers                                            */
/* ------------------------------------------------------------------ */

/** Remove diacritics (São -> Sao, Grêmio -> Gremio). */
export function stripDiacritics(s: string): string {
  return s.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

/** Case/accent-insensitive loose token used for substring matching. */
export function loose(s: string): string {
  return stripDiacritics(s).toLowerCase().replace(/\s+/g, " ").trim();
}

/** Normalize a base name: lowercase, no accents, no punctuation, single spaces. */
function normalizeBase(s: string): string {
  return stripDiacritics(s)
    .toLowerCase()
    .replace(/[.'’"]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

/** Slugify a normalized base: "atletico mineiro" -> "atletico-mineiro". */
function slug(s: string): string {
  return s.replace(/\s+/g, "-");
}

/* ------------------------------------------------------------------ */
/* State / country suffix handling                                     */
/* ------------------------------------------------------------------ */

const BR_STATES = new Set([
  "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
  "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
  "SE", "SP", "TO",
]);

/** Non-Brazilian suffix codes used by the Libertadores dataset. */
const COUNTRY_CODES = new Set([
  "PAR", "URU", "EQU", "PER", "VEN", "ARG", "BOL", "CHI", "COL", "MEX", "USA",
]);

const ALL_CODES = new Set([...BR_STATES, ...COUNTRY_CODES]);

/**
 * Foreign clubs whose *names* end in what looks like a Brazilian state code
 * (e.g. "Portimonense SC", "SC Braga" — SC = Sporting Clube, not Santa
 * Catarina). Suffix stripping is skipped for these.
 */
const FOREIGN_CLUB_BASES = new Set(
  [
    "Portimonense SC",
    "SC Braga",
    "Sporting CP",
    "Sporting Braga",
    "Clube Sport Marítimo",
    "CD Aves",
    "CD Nacional",
    "CD Tondela",
    "CD Feirense",
    "CD Santa Clara",
    "Rio Ave FC",
    "Vitória Guimarães",
    "Vitória Setúbal",
    "GD Chaves",
    "GD Estoril Praia",
    "Moreirense FC",
    "Belenenses",
    "Boavista FC",
    "FC Porto",
    "SL Benfica",
    "CS Marítimo",
  ].map(normalizeBase),
);

/* ------------------------------------------------------------------ */
/* Team aliases: normalized slug -> canonical key                      */
/* ------------------------------------------------------------------ */

const TEAM_ALIASES: Record<string, string> = {
  // Rio de Janeiro giants (bare names default to the big club)
  flamengo: "flamengo-rj",
  fluminense: "fluminense-rj",
  vasco: "vasco-rj",
  "vasco-da-gama": "vasco-rj",
  "vasco-da-gama-rj": "vasco-rj",
  botafogo: "botafogo-rj",
  boavista: "boavista-rj",
  "boavista-sport-club": "boavista-rj",
  "boavista-sc-saquarema": "boavista-rj",
  americano: "americano-rj",
  // São Paulo state
  palmeiras: "palmeiras-sp",
  corinthians: "corinthians-sp",
  "sport-club-corinthians-paulista": "corinthians-sp",
  santos: "santos-sp",
  "sao-paulo": "sao-paulo-sp",
  "sao-paulo-fc": "sao-paulo-sp",
  "ponte-preta": "ponte-preta-sp",
  portuguesa: "portuguesa-sp",
  "portuguesa-desportos": "portuguesa-sp",
  guarani: "guarani-sp",
  "sao-caetano": "sao-caetano-sp",
  "santo-andre": "santo-andre-sp",
  "sao-bento": "sao-bento-sp",
  ituano: "ituano-sp",
  mirassol: "mirassol-sp",
  novorizontino: "novorizontino-sp",
  "gremio-novorizontino": "novorizontino-sp",
  "inter-de-limeira": "inter-de-limeira-sp",
  audax: "audax-sp",
  oeste: "oeste-sp",
  ferroviaria: "ferroviaria-sp",
  "red-bull-bragantino": "red-bull-bragantino-sp",
  bragantino: "red-bull-bragantino-sp",
  "bragantino-sp": "red-bull-bragantino-sp",
  "red-bull-brasil": "red-bull-brasil-sp",
  "gremio-barueri": "gremio-barueri-sp",
  "gremio-prudente": "gremio-barueri-sp",
  barueri: "gremio-barueri-sp",
  // Rio Grande do Sul
  gremio: "gremio-rs",
  "gremio-foot-ball-porto-alegrense": "gremio-rs",
  internacional: "internacional-rs",
  "sport-club-internacional": "internacional-rs",
  juventude: "juventude-rs",
  "ec-juventude": "juventude-rs",
  caxias: "caxias-rs",
  "ser-caxias-rs": "caxias-rs",
  brasil: "brasil-de-pelotas-rs",
  "brasil-rs": "brasil-de-pelotas-rs",
  "brasil-de-pelotas": "brasil-de-pelotas-rs",
  "sao-jose-poa": "sao-jose-rs",
  // Minas Gerais
  cruzeiro: "cruzeiro-mg",
  "atletico-mineiro": "atletico-mg",
  "clube-atletico-mineiro": "atletico-mg",
  "america-mineiro": "america-mg",
  "america-fc": "america-mg",
  "america-fc-minas-gerais": "america-mg",
  ipatinga: "ipatinga-mg",
  urt: "urt-mg",
  tupi: "tupi-mg",
  "villa-nova": "villa-nova-mg",
  "villa-nova-mg": "villa-nova-mg",
  // Paraná
  "athletico-paranaense": "athletico-pr",
  "atletico-paranaense": "athletico-pr",
  "atletico-pr": "athletico-pr",
  athletico: "athletico-pr",
  "clube-athletico-paranaense": "athletico-pr",
  coritiba: "coritiba-pr",
  parana: "parana-pr",
  "parana-clube": "parana-pr",
  "ca-parana": "parana-pr",
  "operario-ferroviario": "operario-pr",
  "operario-ferroviario-esporte-c-pr": "operario-pr",
  pstc: "pstc-pr",
  "fc-cascavel": "cascavel-pr",
  cascavel: "cascavel-pr",
  // Santa Catarina
  avai: "avai-sc",
  chapecoense: "chapecoense-sc",
  figueirense: "figueirense-sc",
  criciuma: "criciuma-sc",
  joinville: "joinville-sc",
  tubarao: "tubarao-sc",
  brusque: "brusque-sc",
  // Northeast
  ceara: "ceara-ce",
  "ceara-sporting-club": "ceara-ce",
  fortaleza: "fortaleza-ce",
  "fortaleza-ec": "fortaleza-ce",
  "fortaleza-fc": "fortaleza-ce",
  "fortaleza-esporte-clube": "fortaleza-ce",
  bahia: "bahia-ba",
  "ec-bahia": "bahia-ba",
  "esporte-clube-bahia": "bahia-ba",
  vitoria: "vitoria-ba",
  "ec-vitoria": "vitoria-ba",
  "vitoria-ec": "vitoria-ba",
  "esporte-clube-vitoria": "vitoria-ba",
  "vitoria-f-c-es": "vitoria-es",
  "central-sc": "central-pe",
  "ec-internacional-sc": "internacional-sc",
  ferroviario: "ferroviario-ce",
  "macae-esporte-fc": "macae-rj",
  "macae-esporte-rj": "macae-rj",
  "madureira-ec": "madureira-rj",
  madureira: "madureira-rj",
  retro: "retro-pe",
  "retro-fc-brasil": "retro-pe",
  "sete-de-setembro": "7-de-setembro-ms",
  manaus: "manaus-am",
  caldense: "caldense-mg",
  cianorte: "cianorte-pr",
  londrina: "londrina-pr",
  maringa: "maringa-pr",
  tombense: "tombense-mg",
  uberlandia: "uberlandia-mg",
  "sao-bernardo": "sao-bernardo-sp",
  "xv-piracicaba": "xv-de-piracicaba-sp",
  linense: "linense-sp",
  "guarani-de-juazeiro": "guarani-de-juazeiro-ce",
  "guarany-de-sobral": "guarany-de-sobral-ce",
  juazeirense: "juazeirense-ba",
  salgueiro: "salgueiro-pe",
  ypiranga: "ypiranga-rs",
  anapolis: "anapolis-go",
  "anapolis-fc": "anapolis-go",
  jaragua: "jaragua-go",
  "jaragua-ec": "jaragua-go",
  brasilia: "brasilia-df",
  "brasilia-fc": "brasilia-df",
  ceilandia: "ceilandia-df",
  sobradinho: "sobradinho-df",
  luziania: "luziania-df",
  "foz-do-iguacu": "foz-do-iguacu-pr",
  lajeadense: "lajeadense-rs",
  "novo-hamburgo": "novo-hamburgo-rs",
  "esportivo-bento-goncalves": "esportivo-rs",
  avenida: "avenida-rs",
  "sao-luiz": "sao-luiz-rs",
  "ad-frei-paulistano": "frei-paulistano-se",
  afogados: "afogados-pe",
  "afogados-da-ingazeira-fc": "afogados-pe",
  coruripe: "coruripe-al",
  sergipe: "sergipe-se",
  estanciano: "estanciano-se",
  amadense: "amadense-se",
  "amadense-ec": "amadense-se",
  "santa-rita": "santa-rita-al",
  lagarto: "lagarto-se",
  corumbaense: "corumbaense-ms",
  aquidauanense: "aquidauanense-ms",
  "aquidauanense-futebol-clube-ms": "aquidauanense-ms",
  boa: "boa-mg",
  "nova-iguacu": "nova-iguacu-rj",
  resende: "resende-rj",
  "volta-redonda": "volta-redonda-rj",
  cabofriense: "cabofriense-rj",
  friburguense: "friburguense-rj",
  bangu: "bangu-rj",
  "duque-de-caxias-fc": "duque-de-caxias-rj",
  "real-noroeste-capixaba-es": "real-noroeste-es",
  "estrela-do-norte": "estrela-do-norte-es",
  "desportiva-ferroviaria-es": "desportiva-es",
  "vitoria-da-conquista": "vitoria-da-conquista-ba",
  "bahia-de-feira": "bahia-de-feira-ba",
  jacuipense: "jacuipense-ba",
  barbalha: "barbalha-ce",
  caucaia: "caucaia-ce",
  icasa: "icasa-ce",
  floresta: "floresta-ce",
  "floresta-ec": "floresta-ce",
  "fc-atletico-cearense": "atletico-cearense-ce",
  "atletico-cearense": "atletico-cearense-ce",
  "cs-alagoano": "csa-al",
  "princesa-do-solimoes": "princesa-do-solimoes-am",
  noroeste: "noroeste-sp",
  "paulista-futebol-clube-sp": "paulista-sp",
  sport: "sport-pe",
  "sport-recife": "sport-pe",
  "sport-club-do-recife": "sport-pe",
  "sport-club-recife": "sport-pe",
  nautico: "nautico-pe",
  "nautico-capibaribe": "nautico-pe",
  "clube-nautico-capibaribe": "nautico-pe",
  "santa-cruz": "santa-cruz-pe",
  "santa-cruz-fc": "santa-cruz-pe",
  abc: "abc-rn",
  "america-de-natal": "america-rn",
  "america-fc-natal": "america-rn",
  globo: "globo-rn",
  "globo-fc": "globo-rn",
  asa: "asa-al",
  csa: "csa-al",
  crb: "crb-al",
  murici: "murici-al",
  confianca: "confianca-se",
  "ad-confianca": "confianca-se",
  itabaiana: "itabaiana-se",
  "river-plate-se": "river-plate-se",
  "sampaio-correa": "sampaio-correa-ma",
  "moto-club": "moto-club-ma",
  "moto-clube": "moto-club-ma",
  "moto-club-de-sao-luis": "moto-club-ma",
  imperatriz: "imperatriz-ma",
  "4-de-julho": "4-de-julho-pi",
  "4-de-julho-ec": "4-de-julho-pi",
  "iv-de-julho-pi": "4-de-julho-pi",
  altos: "altos-pi",
  "ae-altos": "altos-pi",
  picos: "picos-pi",
  parnahyba: "parnahyba-pi",
  "flamengo-do-piaui": "flamengo-pi",
  "flamengo-do-piaui-pi": "flamengo-pi",
  "river-ac": "river-pi",
  // North / Center-West
  remo: "remo-pa",
  "clube-do-remo": "remo-pa",
  paysandu: "paysandu-pa",
  "aguia-de-maraba": "aguia-de-maraba-pa",
  "nacional-am": "nacional-am",
  "fast-clube": "fast-clube-am",
  "sao-raimundo-am": "sao-raimundo-am",
  "penarol-am": "penarol-am",
  "rio-branco-ac": "rio-branco-ac",
  "atletico-acreano": "atletico-acreano-ac",
  galvez: "galvez-ac",
  "galvez-ac": "galvez-ac",
  treze: "treze-pb",
  campinense: "campinense-pb",
  "campinense-clube": "campinense-pb",
  souza: "souza-pb",
  "sousa-ec": "souza-pb",
  goias: "goias-go",
  "atletico-goianiense": "atletico-go",
  "vila-nova-go": "vila-nova-go",
  "vila-nova": "vila-nova-go",
  aparecidense: "aparecidense-go",
  anapolina: "anapolina-go",
  crac: "crac-go",
  "goianesia": "goianesia-go",
  "gremio-anapolis": "gremio-anapolis-go",
  brasiliense: "brasiliense-df",
  gama: "gama-df",
  "se-gama": "gama-df",
  cuiaba: "cuiaba-mt",
  luverdense: "luverdense-mt",
  mixto: "mixto-mt",
  sinop: "sinop-mt",
  "sinop-fc": "sinop-mt",
  "uniao-rondonopolis": "uniao-rondonopolis-mt",
  "operario-mt": "operario-mt",
  "operario-ms": "operario-ms",
  tocantinopolis: "tocantinopolis-to",
  gurupi: "gurupi-to",
  trem: "trem-ap",
  "santos-ap": "santos-ap",
  "ypiranga-ap": "ypiranga-ap",
  // Libertadores aliases (foreign clubs with variant spellings)
  libertad: "libertad-par",
  "guarani-par": "guarani-par",
  "nacional-uru": "nacional-uru",
  "nacional-par": "nacional-par",
  "olimpia-par": "olimpia-par",
  delfin: "delfin-equ",
  "barcelona-equ": "barcelona-equ",
  "universitario-per": "universitario-per",
  "trujillanos-ven": "trujillanos-ven",
  tolima: "deportes-tolima",
  "deportes-tolima": "deportes-tolima",
  "ldu": "ldu-quito",
  "ldu-quito": "ldu-quito",
  "ind-santa-fe": "independiente-santa-fe",
  "independiente-santa-fe": "independiente-santa-fe",
  "mineros-de-guaiana": "mineros-de-guayana",
  "mineros-de-guayana": "mineros-de-guayana",
  "real-atletico": "real-atletico",
  "sport-boys": "sport-boys",
  "the-strongest": "the-strongest",
  "jorge-wilstermann": "jorge-wilstermann",
  "san-jose": "san-jose-oruro",
};

/* ------------------------------------------------------------------ */
/* Display names for canonical keys                                    */
/* ------------------------------------------------------------------ */

const DISPLAY_NAMES: Record<string, string> = {
  "flamengo-rj": "Flamengo",
  "fluminense-rj": "Fluminense",
  "vasco-rj": "Vasco da Gama",
  "botafogo-rj": "Botafogo",
  "boavista-rj": "Boavista",
  "americano-rj": "Americano",
  "palmeiras-sp": "Palmeiras",
  "corinthians-sp": "Corinthians",
  "santos-sp": "Santos",
  "sao-paulo-sp": "São Paulo",
  "ponte-preta-sp": "Ponte Preta",
  "portuguesa-sp": "Portuguesa",
  "guarani-sp": "Guarani",
  "sao-caetano-sp": "São Caetano",
  "santo-andre-sp": "Santo André",
  "red-bull-bragantino-sp": "Red Bull Bragantino",
  "gremio-barueri-sp": "Grêmio Barueri",
  "gremio-rs": "Grêmio",
  "internacional-rs": "Internacional",
  "juventude-rs": "Juventude",
  "caxias-rs": "Caxias",
  "brasil-de-pelotas-rs": "Brasil de Pelotas",
  "cruzeiro-mg": "Cruzeiro",
  "atletico-mg": "Atlético Mineiro",
  "america-mg": "América Mineiro",
  "america-rn": "América de Natal",
  "athletico-pr": "Athletico Paranaense",
  "coritiba-pr": "Coritiba",
  "parana-pr": "Paraná Clube",
  "operario-pr": "Operário Ferroviário",
  "avai-sc": "Avaí",
  "chapecoense-sc": "Chapecoense",
  "figueirense-sc": "Figueirense",
  "criciuma-sc": "Criciúma",
  "joinville-sc": "Joinville",
  "ceara-ce": "Ceará",
  "fortaleza-ce": "Fortaleza",
  "bahia-ba": "Bahia",
  "vitoria-ba": "Vitória",
  "sport-pe": "Sport Recife",
  "nautico-pe": "Náutico",
  "santa-cruz-pe": "Santa Cruz",
  "abc-rn": "ABC",
  "asa-al": "ASA",
  "csa-al": "CSA",
  "crb-al": "CRB",
  "confianca-se": "Confiança",
  "sampaio-correa-ma": "Sampaio Corrêa",
  "moto-club-ma": "Moto Club",
  "remo-pa": "Remo",
  "paysandu-pa": "Paysandu",
  "goias-go": "Goiás",
  "atletico-go": "Atlético Goianiense",
  "vila-nova-go": "Vila Nova",
  "brasiliense-df": "Brasiliense",
  "cuiaba-mt": "Cuiabá",
  "flamengo-pi": "Flamengo-PI",
  "botafogo-sp": "Botafogo-SP",
  "botafogo-pb": "Botafogo-PB",
  "guarani-de-juazeiro-ce": "Guarani de Juazeiro",
  "sao-jose-rs": "São José-RS",
  "4-de-julho-pi": "4 de Julho",
  "river-pi": "Ríver-PI",
  "globo-rn": "Globo-RN",
  "fast-clube-am": "Fast Clube",
  "treze-pb": "Treze",
  "campinense-pb": "Campinense",
  "ipatinga-mg": "Ipatinga",
  "gama-df": "Gama",
  // Foreign clubs
  "boca-juniors": "Boca Juniors",
  "river-plate": "River Plate",
  "river-plate-uru": "River Plate-URU",
  "libertad-par": "Libertad",
  "olimpia-par": "Olimpia",
  "cerro-porteno": "Cerro Porteño",
  "nacional-par": "Nacional-PAR",
  "nacional-uru": "Nacional-URU",
  "guarani-par": "Guaraní-PAR",
  penarol: "Peñarol",
  nacional: "Nacional",
  "barcelona-equ": "Barcelona-EQU",
  "emelec": "Emelec",
  "ldu-quito": "LDU Quito",
  "delfin-equ": "Delfín",
  "independiente-del-valle": "Independiente del Valle",
  "colo-colo": "Colo-Colo",
  "universidad-de-chile": "Universidad de Chile",
  "universidad-catolica": "Universidad Católica",
  "deportes-tolima": "Deportes Tolima",
  "atletico-nacional": "Atlético Nacional",
  "independiente-santa-fe": "Independiente Santa Fe",
  "millonarios": "Millonarios",
  "america-de-cali": "América de Cali",
  "universitario-per": "Universitario-PER",
  "alianza-lima": "Alianza Lima",
  "sporting-cristal": "Sporting Cristal",
  "the-strongest": "The Strongest",
  bolivar: "Bolívar",
  "jorge-wilstermann": "Jorge Wilstermann",
  "san-lorenzo": "San Lorenzo",
  "racing-club": "Racing Club",
  "velez-sarsfield": "Vélez Sarsfield",
  estudiantes: "Estudiantes",
  "argentinos-juniors": "Argentinos Juniors",
  lanus: "Lanús",
  "newells-old-boys": "Newell's Old Boys",
  "rosario-central": "Rosario Central",
};

/** Title-case fallback display name for keys without a curated name. */
function fallbackDisplay(key: string): string {
  return key
    .split("-")
    .map((w) => (w.length <= 3 && /^[a-z]{2,3}$/.test(w) && BR_STATES.has(w.toUpperCase()) ? w.toUpperCase() : w[0].toUpperCase() + w.slice(1)))
    .join(" ");
}

/* ------------------------------------------------------------------ */
/* Public API                                                          */
/* ------------------------------------------------------------------ */

export interface ParsedTeamName {
  base: string;
  state: string | null;
}

/**
 * Split a raw team name into its base name and state/country suffix.
 * Handles "-SP", " - RJ", "(PAR)", "Botafogo PB", "Aguia Negra-MS", ...
 */
export function parseTeamName(raw: string): ParsedTeamName {
  let s = raw.trim().replace(/\s+/g, " ");
  // Drop parentheticals that are NOT 2-3 letter codes, e.g.
  // "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ".
  s = s.replace(/\((?![A-Za-z]{2,3}\))[^)]*\)/g, " ").replace(/\s+/g, " ").trim();

  if (!FOREIGN_CLUB_BASES.has(normalizeBase(s))) {
    const m = s.match(/(?:[-–]\s*|\(\s*|\s+)([A-Za-z]{2,3})\s*\)?\s*$/);
    if (m && ALL_CODES.has(m[1].toUpperCase())) {
      const state = m[1].toUpperCase();
      const base = s.slice(0, m.index).replace(/[-–(\s]+$/, "").trim();
      const nb = normalizeBase(base);
      if (nb) return { base: nb, state };
    }
  }
  return { base: normalizeBase(s) || normalizeBase(raw), state: null };
}

/** Resolve a raw team name to its canonical key. */
export function canonicalTeamKey(raw: string): string {
  const { base, state } = parseTeamName(raw);
  const baseSlug = slug(base);
  const fullKey = state ? `${baseSlug}-${state.toLowerCase()}` : baseSlug;
  if (TEAM_ALIASES[fullKey]) return TEAM_ALIASES[fullKey];
  if (state) {
    // Try base-only alias (e.g. "Athletico Paranaense - PR" -> athletico-pr)
    const viaBase = TEAM_ALIASES[baseSlug];
    if (viaBase) {
      // Only apply when the alias target is consistent with the state (or target is foreign-free)
      const targetState = viaBase.split("-").pop() ?? "";
      if (!BR_STATES.has(state) || targetState.toUpperCase() === state) return viaBase;
      // Conflicting explicit state: keep the explicit-state key unless alias known.
      return viaBase.endsWith(`-${state.toLowerCase()}`) ? viaBase : fullKey;
    }
    return fullKey;
  }
  return TEAM_ALIASES[baseSlug] ?? baseSlug;
}

/** Display name for a canonical key. */
export function teamDisplayName(key: string): string {
  return DISPLAY_NAMES[key] ?? fallbackDisplay(key);
}

/**
 * Canonical keys that belong to foreign (non-Brazilian) clubs even though
 * the slug happens to end in a Brazilian state code (e.g. "portimonense-sc"
 * where SC = Sporting Clube, not Santa Catarina).
 */
const FOREIGN_TEAM_KEYS = new Set([...FOREIGN_CLUB_BASES].map(slug));

/** True when the canonical key belongs to a Brazilian club. */
export function isBrazilianTeamKey(key: string): boolean {
  if (FOREIGN_TEAM_KEYS.has(key)) return false;
  const suffix = key.split("-").pop()?.toUpperCase() ?? "";
  return BR_STATES.has(suffix);
}

/** Build a TeamRef from a raw source name. */
export function teamRef(raw: string): TeamRef {
  const key = canonicalTeamKey(raw);
  return { key, name: teamDisplayName(key), raw };
}

/**
 * Resolve a user-supplied team query (e.g. "Flamengo", "flamengo-rj",
 * "Sport Club Corinthians Paulista") to a canonical key.
 */
export function resolveTeamQuery(query: string): string {
  return canonicalTeamKey(query);
}

/** Loose substring match of a user query against a raw team name. */
export function teamNameMatches(query: string, rawName: string): boolean {
  const q = loose(query);
  if (!q) return false;
  if (loose(rawName).includes(q)) return true;
  const key = canonicalTeamKey(rawName);
  if (key.includes(q.replace(/\s+/g, "-"))) return true;
  const display = teamDisplayName(key);
  return loose(display).includes(q);
}

/* ------------------------------------------------------------------ */
/* Dates                                                               */
/* ------------------------------------------------------------------ */

/**
 * Parse the date formats used across the datasets:
 *  - "2023-09-24"              (ISO)
 *  - "2012-05-19 18:30:00"     (ISO datetime)
 *  - "29/03/2003"              (Brazilian DD/MM/YYYY)
 * Returns an ISO yyyy-mm-dd string, or null when unparseable.
 */
export function parseDate(raw: string | null | undefined): string | null {
  if (!raw) return null;
  const s = raw.trim();
  let m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return `${m[1]}-${m[2]}-${m[3]}`;
  m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (m) {
    const [, d, mo, y] = m;
    return `${y}-${mo.padStart(2, "0")}-${d.padStart(2, "0")}`;
  }
  return null;
}

/* ------------------------------------------------------------------ */
/* Competitions                                                        */
/* ------------------------------------------------------------------ */

const COMPETITION_ALIASES: Record<string, CompetitionLabel> = {
  "brasileirao": "Brasileirão Série A",
  "brasileirao serie a": "Brasileirão Série A",
  "serie a": "Brasileirão Série A",
  "campeonato brasileiro": "Brasileirão Série A",
  "campeonato brasileiro serie a": "Brasileirão Série A",
  "brasileirao serie b": "Brasileirão Série B",
  "serie b": "Brasileirão Série B",
  "brasileirao serie c": "Brasileirão Série C",
  "serie c": "Brasileirão Série C",
  "copa do brasil": "Copa do Brasil",
  "brazilian cup": "Copa do Brasil",
  "libertadores": "Copa Libertadores",
  "copa libertadores": "Copa Libertadores",
  "copa conmebol libertadores": "Copa Libertadores",
};

/** Resolve a user-supplied competition query to a canonical label (null if unknown). */
export function resolveCompetition(query: string): CompetitionLabel | null {
  const q = loose(query);
  if (!q) return null;
  if (COMPETITION_ALIASES[q]) return COMPETITION_ALIASES[q];
  for (const [alias, label] of Object.entries(COMPETITION_ALIASES)) {
    if (q.includes(alias) || loose(label) === q) return label;
  }
  return null;
}

/** Map a BR-Football-Dataset tournament value to a canonical label. */
export function competitionFromTournament(tournament: string): CompetitionLabel | null {
  return resolveCompetition(tournament);
}
