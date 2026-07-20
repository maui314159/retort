/**
 * Canonical team registry.
 *
 * The datasets name the same club many different ways ("Vasco da Gama-RJ",
 * "Vasco", "Vasco Da Gama RJ"), while also containing genuinely distinct
 * clubs that share a base name (Botafogo-RJ vs Botafogo-PB vs Botafogo-SP;
 * Portuguesa-SP vs Portuguesa-RJ; four different "Operário" clubs).
 *
 * A curated alias table maps every known variant to a canonical key.
 * Unknown names fall back to: strip state suffix -> strip club-type
 * prefixes/suffixes (EC, FC, ...) -> re-attach state when the base name is
 * known to be state-ambiguous.
 */

import { stripAccents } from "./normalize.js";

/**
 * Alias table: canonical key -> every known variant (already lowercase,
 * accent-free, punctuation collapsed to spaces, state codes as tokens).
 */
const CANONICAL: Record<string, string[]> = {
  // --- Serie A staples (appear in 2-3 overlapping sources) ---
  "atletico mineiro": ["atletico mg", "clube atletico mineiro"],
  "athletico paranaense": [
    "atletico pr", "athletico pr", "atletico paranaense", "athletico",
    "clube atletico paranaense",
  ],
  "atletico goianiense": ["atletico go"],
  "vasco da gama": ["vasco", "vasco da gama rj", "cr vasco da gama"],
  "botafogo": ["botafogo rj"],
  "botafogo pb": [],
  "botafogo sp": ["botafogo fc"],
  "fortaleza": ["fortaleza ce", "fortaleza fc", "fortaleza ec"],
  "sport recife": ["sport", "sport pe", "sport club do recife"],
  "america mineiro": ["america mg"],
  "america rn": ["america de natal", "america de natal rn", "america fc natal"],
  "americano rj": ["americano"],
  "gremio": ["gremio rs", "gremio fbpa"],
  "internacional": ["internacional rs", "sc internacional"],
  "corinthians": ["corinthians sp", "sc corinthians", "sport club corinthians paulista"],
  "flamengo": ["flamengo rj", "cr flamengo"],
  "flamengo pi": ["flamengo do piaui", "flamengo do piaui pi"],
  "fluminense": ["fluminense rj", "fluminense fc"],
  "fluminense pi": [],
  "fluminense de feira": ["fluminense de feira ba"],
  "palmeiras": ["palmeiras sp", "se palmeiras"],
  "santos": ["santos sp", "santos fc"],
  "santos ap": [],
  "sao paulo": ["sao paulo sp", "sao paulo fc"],
  "cruzeiro": ["cruzeiro mg", "cruzeiro ec"],
  "bahia": ["bahia ba", "ec bahia", "esporte clube bahia"],
  "bahia de feira": ["bahia de feira ba"],
  "vitoria": ["vitoria ba", "ec vitoria", "vitoria ec"],
  "vitoria es": ["vitoria f c es", "vitoria fc es"],
  "vitoria da conquista": ["vitoria da conquista ba"],
  "goias": ["goias go", "goias ec"],
  "coritiba": ["coritiba pr", "coritiba fc"],
  "chapecoense": ["chapecoense sc", "chapecoense af"],
  "figueirense": ["figueirense sc", "figueirense fc"],
  "criciuma": ["criciuma sc", "criciuma ec"],
  "joinville": ["joinville sc", "joinville ec"],
  "juventude": ["juventude rs", "ec juventude"],
  "juventude ma": [],
  "nautico": ["nautico pe", "nautico capibaribe", "clube nautico capibaribe"],
  "nautico rr": [],
  "parana clube": ["parana", "parana pr", "ca parana"],
  "ponte preta": ["ponte preta sp", "aa ponte preta"],
  "portuguesa": ["portuguesa sp", "portuguesa desportos", "aa portuguesa"],
  "portuguesa rj": [],
  "bragantino": ["red bull bragantino", "red bull bragantino sp", "bragantino sp"],
  "bragantino pa": [],
  "red bull brasil": ["red bull brasil sp"],
  "santa cruz": ["santa cruz pe", "santa cruz fc"],
  "santa cruz rn": [],
  "santa cruz rs": [],
  "csa": ["csa al", "c s a al", "centro sportivo alagoano"],
  "cs alagoano": [],
  "cuiaba": ["cuiaba mt", "cuiaba ec"],
  "ceara": ["ceara ce", "ceara sc"],
  "guarani": ["guarani sp", "guarani fc"],
  "guarani de juazeiro": ["guarani ce", "guarani de juazeiro ce"],
  "guarany de sobral": ["guarany ce", "guarany de sobral ce"],
  "santo andre": ["santo andre sp", "ec santo andre"],
  "sao caetano": ["sao caetano sp"],
  "sao bento": ["sao bento sp"],
  "paysandu": ["paysandu pa", "paysandu sc"],
  "remo": ["remo pa", "clube do remo", "clube remo"],
  "brasiliense": ["brasiliense df"],
  "ipatinga": [],
  "gremio barueri": ["barueri", "gremio barueri sp", "gremio prudente"],
  // --- Copa do Brasil / Serie B-C clubs (overlap Brazilian_Cup vs BR-Football) ---
  "4 de julho": ["4 de julho pi", "4 de julho ec"],
  "abc": ["abc rn", "a b c rn", "abc fc"],
  "asa": ["asa al", "a s a al"],
  "crb": ["crb al", "c r b al", "clube de regatas brasil"],
  "sampaio correa": ["sampaio correa ma", "sampaio correa fc"],
  "vila nova": ["vila nova go", "vila nova fc"],
  "villa nova": ["villa nova mg"],
  "londrina": ["londrina pr", "londrina ec"],
  "tombense": ["tombense mg", "tombense fc"],
  "brasil de pelotas": ["brasil rs", "gremio esportivo brasil", "brasil"],
  "operario ferroviario": [
    "operario pr", "operario ferroviario esporte c pr", "operario ferroviario ec",
  ],
  "operario ms": ["operario fc ms"],
  "operario mt": [],
  "boavista rj": [
    "boavista", "boavista sc saquarema", "boavista sc",
    "boavista sport club antigo esporte clube barreira rj",
    "boavista sport club rj",
  ],
  "ferroviaria": ["ferroviaria sp"],
  "ferroviario": ["ferroviario ce"],
  "caxias": ["caxias rs", "ser caxias", "ser caxias rs"],
  "duque de caxias": ["duque de caxias rj", "duque de caxias fc"],
  "confianca": ["confianca se", "ad confianca"],
  "treze": ["treze pb"],
  "ituano": ["ituano sp", "ituano fc"],
  "novorizontino": ["novorizontino sp", "gremio novorizontino"],
  "mirassol": ["mirassol sp", "mirassol fc"],
  "tupi": ["tupi mg"],
  "uberlandia": ["uberlandia mg"],
  "urt": ["urt mg"],
  "volta redonda": ["volta redonda rj", "volta redonda fc"],
  "ypiranga rs": ["ypiranga"],
  "ypiranga ap": [],
  "altos": ["altos pi", "ae altos"],
  "afogados": ["afogados pe", "afogados da ingazeira", "afogados da ingazeira fc"],
  "aguia negra": ["aguia negra ms"],
  "aguia de maraba": ["aguia pa"],
  "anapolina": ["anapolina go"],
  "anapolis": ["anapolis go", "anapolis fc"],
  "gremio anapolis": [],
  "aparecidense": ["aparecidense go"],
  "aquidauanense": ["aquidauanense ms", "aquidauanense futebol clube ms"],
  "avenida": ["avenida rs"],
  "bangu": ["bangu rj"],
  "barbalha": ["barbalha ce"],
  "boa esporte": ["boa", "boa mg", "boa esporte clube"],
  "brasilia": ["brasilia df", "brasilia fc"],
  "brusque": ["brusque sc"],
  "cabofriense": ["cabofriense rj"],
  "caldense": ["caldense mg"],
  "campinense": ["campinense pb", "campinense clube"],
  "capivariano": ["capivariano sp"],
  "castanhal": ["castanhal pa"],
  "caucaia": ["caucaia ce"],
  "ceilandia": ["ceilandia df"],
  "cianorte": ["cianorte pr"],
  "comercial ms": [],
  "comercial pi": [],
  "cordino": ["cordino ma", "cordino ec"],
  "corumbaense": ["corumbaense ms"],
  "coruripe": ["coruripe al"],
  "estanciano": ["estanciano se"],
  "estrela do norte": ["estrela do norte es"],
  "fast clube": ["fast clube am"],
  "cascavel": ["fc cascavel", "fc cascavel pr"],
  "floresta": ["floresta ce", "floresta ec"],
  "foz do iguacu": ["foz do iguacu pr"],
  "friburguense": ["friburguense rj"],
  "galvez": ["galvez ac"],
  "gama": ["gama df", "se gama"],
  "globo": ["globo rn", "globo fc"],
  "goianesia": ["goianesia go"],
  "gurupi": ["gurupi to"],
  "horizonte": ["horizonte ce"],
  "icasa": ["icasa ce"],
  "imperatriz": ["imperatriz ma"],
  "independente pa": ["independente de tucurui", "independente de tucurui pa"],
  "inter de limeira": ["inter de limeira sp"],
  "itabaiana": ["itabaiana se"],
  "jacuipense": ["jacuipense ba"],
  "jaragua": ["jaragua go", "jaragua ec"],
  "juazeirense": ["juazeirense ba"],
  "juazeiro": ["juazeiro ba"],
  "lagarto": ["lagarto se"],
  "lajeadense": ["lajeadense rs"],
  "linense": ["linense sp"],
  "luverdense": ["luverdense mt"],
  "luziania": ["luziania df"],
  "madureira": ["madureira rj", "madureira ec"],
  "manaus": ["manaus am"],
  "marilia": ["marilia sp"],
  "maringa": ["maringa pr", "metropolitano maringa pr", "metropolitano maringa"],
  "mixto": ["mixto mt"],
  "moto club": ["moto club ma", "moto clube", "moto club de sao luis"],
  "murici": ["murici al"],
  "nacional am": [],
  "nova iguacu": ["nova iguacu rj"],
  "nova mutum": ["nova mutum mt", "nova mutum ec"],
  "novo hamburgo": ["novo hamburgo rs"],
  "oeste": ["oeste sp"],
  "palmas": ["palmas ltda", "palmas ltda to", "palmas fr"],
  "parauapebas": ["parauapebas pa"],
  "parnahyba": ["parnahyba pi", "parnahyba s c pi", "parnahyba sc pi"],
  "penarol am": [],
  "picos": ["picos pi"],
  "porto velho": ["porto velho ro", "porto velho ec"],
  "princesa do solimoes": ["princesa do solimoes am"],
  "pstc": ["pstc pr"],
  "real noroeste": ["real noroeste es", "real noroeste capixaba", "real noroeste capixaba es"],
  "resende": ["resende rj"],
  "real fc": [],
  "real rr": [],
  "retro": ["retro pe", "retro fc brasil", "retro fc"],
  "rio branco ac": ["rio branco"],
  "rio branco es": ["rio branco vn es", "rio branco vn"],
  "river pi": ["river"],
  "river ac": [],
  "river plate se": [],
  "salgueiro": ["salgueiro pe"],
  "santa rita": ["santa rita al"],
  "sao bernardo": ["sao bernardo sp"],
  "sao jose rs": ["sao jose poa"],
  "sao jose pa": [],
  "sao luiz": ["sao luiz rs"],
  "sao raimundo pa": [],
  "sao raimundo rr": [],
  "sao raimundo am": [],
  "sergipe": ["sergipe se", "cs sergipe"],
  "sinop": ["sinop mt", "sinop fc"],
  "sobradinho": ["sobradinho df"],
  "sousa": ["souza pb", "sousa ec"],
  "tocantinopolis": ["tocantinopolis to", "tocantinopolis ec"],
  "toledo": ["toledo pr", "toledo ec"],
  "trem": ["trem ap"],
  "tubarao": ["tubarao sc"],
  "uniao rondonopolis": ["uniao mt", "uniao de rondonopolis mt"],
  "uniclinic": ["uniclinic ce"],
  "vilhena": ["vilhena ro", "vilhenense", "vilhenense ro", "vilhenense ec"],
  "xv de piracicaba": ["xv de piracicaba sp", "xv piracicaba"],
  "audax": ["audax sp"],
  "aimore": ["aimore rs", "ce aimore"],
  "cene": ["cene ms"],
  "crac": ["crac go", "c r a c go"],
  "central": ["central pe", "central sc"],
  "esportivo": ["esportivo rs", "esportivo bento goncalves"],
  "dom bosco": ["dom bosco mt", "ce dom bosco"],
  "desportiva": ["desportiva es", "desportiva ferroviaria", "desportiva ferroviaria es"],
  "frei paulistano": ["frei paulistano se", "ad frei paulistano"],
  "genus": ["genus ro", "sc genus"],
  "sao francisco pa": ["s francisco pa", "sfrancisco pa"],
  "sao francisco ac": [],
  "sete de setembro": ["7 de setembro", "7 de setembro ms"],
  "amadense": ["amadense se", "amadense ec"],
  "atletico cearense": ["atletico cearense ce", "fc atletico cearense"],
  "atletico alagoinhas": ["atletico ba"],
  "atletico acreano": ["atletico ac"],
  "athletic club": ["athletic club mg"],
  "itabaiana fc": [],
  "macae": ["macae esporte", "macae esporte fc", "macae esporte rj"],
  "serra": ["serra f c es", "serra fc es"],
  "rondonopolis": ["rondonopolis mt"],
  "arapongas": ["arapongas esporte clube pr"],
  "votuporanguense": ["votuporanguense sp", "ca votuporanguense"],
  "tuntum": ["tuntum ec"],
  // --- Libertadores forms ---
  "delfin": ["delfin equ"],
  "universitario": ["universitario per"],
  "libertad": ["libertad par"],
  "nacional uru": [],
  "nacional par": [],
  "guarani par": [],
  "barcelona equ": [],
  "olimpia": ["olimpia par"],
  "cerro porteno": [],
  "river plate": [],
  "river plate uru": [],
};

/** variant -> canonical */
const ALIAS = new Map<string, string>();
for (const [canonical, variants] of Object.entries(CANONICAL)) {
  ALIAS.set(canonical, canonical);
  for (const v of variants) ALIAS.set(v, canonical);
}

const STATE_CODES = new Set([
  "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms",
  "mg", "pa", "pb", "pr", "pe", "pi", "rj", "rn", "rs", "ro", "rr", "sc",
  "sp", "se", "to",
]);

/** Club-type prefixes/suffixes stripped as a fallback step. */
const CLUB_PREFIXES = new Set([
  "ec", "fc", "sc", "cr", "ca", "aa", "se", "ad", "ae", "ce", "ge", "cs",
  "clube", "club", "esporte", "sporting",
]);

/**
 * Base names that are ambiguous without their state — never resolve these
 * to a bare base key (prevents merging e.g. Botafogo-PB into Botafogo-RJ).
 */
const STATE_AMBIGUOUS = new Set([
  "atletico", "america", "botafogo", "portuguesa", "nacional", "santa cruz",
  "juventude", "nautico", "operario", "guarani", "rio branco",
  "sao raimundo", "bragantino", "ypiranga", "vila nova", "flamengo",
  "santos", "sao jose", "guarany", "river plate", "barcelona", "comercial",
]);

/** Clean a raw team name into lookup form (keeps state tokens). */
export function cleanTeamName(name: string): string {
  if (!name) return "";
  let s = stripAccents(name).toLowerCase().trim();
  // Parenthetical content becomes tokens ("Guarani (PAR)" -> "guarani par").
  s = s.replace(/[()[\]]/g, " ");
  // Dotted abbreviations: "A.B.C." -> "abc"; keep word dots otherwise rare.
  s = s.replace(/\b(?:[a-z]\.){2,}/g, (m) => m.replace(/\./g, ""));
  s = s.replace(/\./g, " ");
  // Collapse all remaining non-alphanumerics to single spaces.
  s = s.replace(/[^a-z0-9]+/g, " ").trim();
  return s;
}

function stripClubAffixes(tokens: string[]): string[] {
  const out = [...tokens];
  while (out.length > 1 && CLUB_PREFIXES.has(out[0])) out.shift();
  while (out.length > 1 && (out[out.length - 1] === "fc" || out[out.length - 1] === "ec")) out.pop();
  return out;
}

/**
 * Canonical identity key for a team. All match indexing and team lookups
 * go through this function so cross-dataset joins work.
 */
export function canonicalTeamKey(name: string): string {
  const clean = cleanTeamName(name);
  if (!clean) return "";

  const direct = ALIAS.get(clean);
  if (direct) return direct;

  // Strip trailing state token(s) and retry.
  const tokens = clean.split(" ");
  let hadState = false;
  while (tokens.length > 1 && STATE_CODES.has(tokens[tokens.length - 1])) {
    tokens.pop();
    hadState = true;
  }
  const base = tokens.join(" ");
  const baseHit = ALIAS.get(base);
  if (baseHit) return baseHit;

  // Strip club-type prefixes/suffixes and retry (with and without state).
  const stripped = stripClubAffixes(tokens).join(" ");
  const strippedHit = ALIAS.get(stripped);
  if (strippedHit) return strippedHit;

  // Ambiguous base names keep their state to avoid cross-club merges.
  if (hadState && STATE_AMBIGUOUS.has(stripped)) {
    const state = clean.split(" ").filter((t) => STATE_CODES.has(t));
    return state.length ? `${stripped} ${state[state.length - 1]}` : stripped;
  }
  return stripped || base || clean;
}
