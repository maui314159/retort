/**
 * Team name normalization.
 *
 * Datasets use inconsistent team names: state suffixes ("Palmeiras-SP"),
 * legal names ("Sport Club Corinthians Paulista"), abbreviations
 * ("Athletico-PR" vs "Athletico Paranaense"), and case differences.
 *
 * The functions below map all of these to a canonical lower-cased token
 * stream that can be used for fuzzy matching and display.
 */

/**
 * Fold Brazilian Portuguese accents to ASCII lower-case.
 */
export function fold(str: string): string {
  return str
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9\s]/g, " ");
}

/**
 * Remove common noise from raw team names: state suffixes,
 * parenthetical legal asides, and extra whitespace.
 */
export function cleanTeamName(raw: string): string {
  let name = raw
    .replace(/\s*-\s*[A-Z]{2}\s*$/u, "")
    .replace(/\s*\(.*?\)\s*/gu, " ")
    .replace(/\s+/g, " ")
    .trim();

  // Strip UTF-8 BOM if present.
  name = name.replace(/^\uFEFF/, "");
  return name;
}

/**
 * Known canonical aliases. Maps a folded raw token to the preferred display.
 */
const ALIASES: Record<string, string> = {
  "athletico pr": "Athletico-PR",
  "athletico paranaense": "Athletico-PR",
  athletico: "Athletico-PR",
  atletico: "Atlético-MG",
  "atletico goianiense": "Atlético-GO",
  "atletico mg": "Atlético-MG",
  "atletico mineiro": "Atlético-MG",
  "america mg": "América-MG",
  "america mineiro": "América-MG",
  "america rn": "América-RN",
  america: "América-MG",
  bahia: "Bahia",
  "ec bahia": "Bahia",
  "esporte clube bahia": "Bahia",
  "sport recife": "Sport",
  "sport club recife": "Sport",
  "sao paulo": "São Paulo",
  "sao paulo fc": "São Paulo",
  gremio: "Grêmio",
  "gremio fbpa": "Grêmio",
  vasco: "Vasco da Gama",
  "vasco da gama": "Vasco da Gama",
  cruzeiro: "Cruzeiro",
  "cruzeiro esporte clube": "Cruzeiro",
  flamengo: "Flamengo",
  fluminense: "Fluminense",
  corinthians: "Corinthians",
  "sport club corinthians paulista": "Corinthians",
  palmeiras: "Palmeiras",
  "societatea sportiva palmeiras": "Palmeiras",
  santos: "Santos",
  "santos fc": "Santos",
  botafogo: "Botafogo",
  "botafogo fr": "Botafogo",
  internacional: "Internacional",
  "sport club internacional": "Internacional",
  coritiba: "Coritiba",
  fortaleza: "Fortaleza",
  "fortaleza esporte clube": "Fortaleza",
  ceara: "Ceará",
  "ceara sporting club": "Ceará",
  chapecoense: "Chapecoense",
  avai: "Avaí",
  goias: "Goiás",
  "ponte preta": "Ponte Preta",
  nauutico: "Náutico",
  nautico: "Náutico",
  figueirense: "Figueirense",
  vitoria: "Vitória",
  "esporte clube vitoria": "Vitória",
  juventude: "Juventude",
  cuiaba: "Cuiabá",
  brasiliense: "Brasiliense",
  parana: "Paraná",
  paraná: "Paraná",
  paysandu: "Paysandu",
  "sao caetano": "São Caetano",
  guarani: "Guarani",
  portuguesa: "Portuguesa",
  "botafogo sp": "Botafogo-SP",
  "santa cruz": "Santa Cruz",
  remo: "Remo",
};

/**
 * Return the canonical display name for a team if we know an alias,
 * otherwise return a cleaned version of the raw input.
 */
export function canonicalTeamName(raw: string): string {
  const cleaned = cleanTeamName(raw);
  const key = fold(cleaned).replace(/\s+/g, " ").trim();
  if (ALIASES[key]) {
    return ALIASES[key];
  }
  return cleaned.replace(/\s+/g, " ").trim();
}

/**
 * Produce a lower-cased, accent-folded, cleaned token string used for
 * fuzzy searches.
 */
export function normalizeTeamName(raw: string): string {
  return fold(canonicalTeamName(raw));
}

/**
 * True when `candidate` matches `query` using canonical team names.
 * Accepts substring matches after normalization (e.g. "Sao" matches
 * "São Paulo").
 */
export function teamMatches(query: string, candidate: string): boolean {
  const q = normalizeTeamName(query);
  const c = normalizeTeamName(candidate);
  if (!q || !c) return false;
  if (q === c) return true;
  return c.includes(q) || q.includes(c);
}
