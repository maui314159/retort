/**
 * brazilian-soccer-mcp — Name and date normalization utilities.
 *
 * Context: The six CSV datasets use wildly inconsistent naming and date
 * conventions (state/country suffixes with dash or space, accents vs. ASCII,
 * full names like "Atlético Mineiro" vs. short "Atlético-MG", club affixes
 * "EC"/"FC" etc., ISO vs. DD/MM/YYYY, with/without time). The normalizers here
 * produce two outputs for each team name:
 *
 *   - `normalizeTeamName`: a human-readable display name with accents and
 *     whitespace preserved and the trailing "-UF"/" UF"/"(URU)" suffix
 *     stripped.
 *   - `teamKey`: a case- and accent-folded, punctuation-collapsed key used for
 *     tolerant matching across files. After the initial key is computed it is
 *     run through a `TEAM_ALIASES` table that collapses remaining mismatches
 *     ("atletico mineiro" and "atletico" both → "atletico mg").
 *
 * Dates are handled by `parseDate`, which accepts ISO (with optional time),
 * Brazilian DD/MM/YYYY, and the NA sentinel.
 */

/** Brazilian state abbreviations (for suffix stripping). */
const STATE_CODES: Set<string> = new Set([
  "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
  "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
  "SP", "SE", "TO",
]);

/** Common club affixes to strip from team names. */
const CLUB_PREFIXES: string[] = ["EC", "FC", "AC", "CE", "SC", "AA", "SE", "GR"];
const CLUB_SUFFIXES: string[] = ["EC", "FC", "AC", "CE", "SC", "AA", "SE", "GR", "MT", "PI", "RJ", "SP", "PR", "RS", "MG", "GO", "BA", "SC", "CE", "PE"];

/** Map of known ASCII→accented canonical team display names. */
const CANONICAL_DISPLAY: Record<string, string> = {
  "Sao Paulo": "São Paulo",
  Gremio: "Grêmio",
  "Atletico-MG": "Atlético-MG",
  "Atletico-GO": "Atlético-GO",
  "Atletico-PR": "Athletico-PR",
  "America-MG": "América-MG",
  "America-RN": "América-RN",
  Avai: "Avaí",
  Ceara: "Ceará",
  Nautico: "Náutico",
  Vitoria: "Vitória",
  Goias: "Goiás",
  Parana: "Paraná",
  Criciuma: "Criciúma",
  Cuiaba: "Cuiabá",
  Fortaleza: "Fortaleza",
  Chapecoense: "Chapecoense",
  Figueirense: "Figueirense",
  Portuguesa: "Portuguesa",
  Botafogo: "Botafogo",
  Flamengo: "Flamengo",
  Fluminense: "Fluminense",
  Corinthians: "Corinthians",
  Palmeiras: "Palmeiras",
  Santos: "Santos",
  Vasco: "Vasco",
  "Vasco da Gama": "Vasco da Gama",
  Internacional: "Internacional",
  Sport: "Sport",
  Cruzeiro: "Cruzeiro",
  Bahia: "Bahia",
  Coritiba: "Coritiba",
  "Atletico Mineiro": "Atlético-MG",
  "Athletico Paranaense": "Athletico-PR",
  "Atletico Paranaense": "Athletico-PR",
  "Atletico Goianiense": "Atlético-GO",
  "America MG": "América-MG",
  "America RN": "América-RN",
  "Botafogo RJ": "Botafogo",
  "Botafogo SP": "Botafogo-SP",
  "Botafogo PB": "Botafogo-PB",
  "EC Bahia": "Bahia",
  "EC Vitoria": "Vitória",
  "EC Juventude": "Juventude",
  "Fortaleza FC": "Fortaleza",
  "Fortaleza EC": "Fortaleza",
  "Coritiba PR": "Coritiba",
  "Cuiaba MT": "Cuiabá",
  "Criciuma SC": "Criciúma",
  "Bragantino": "Bragantino",
  "RB Bragantino": "Bragantino",
  "Sao Paulo SP": "São Paulo",
  "Fluminense RJ": "Fluminense",
  "Vasco da Gama RJ": "Vasco da Gama",
  "Gremio RS": "Grêmio",
  "Internacional RS": "Internacional",
  "Cruzeiro MG": "Cruzeiro",
  "Bahia BA": "Bahia",
  "Ceara CE": "Ceará",
  "Sport PE": "Sport",
  "Chapecoense SC": "Chapecoense",
  "Goias GO": "Goiás",
  "Avai SC": "Avaí",
  "Nautico PE": "Náutico",
  "Figueirense SC": "Figueirense",
  "Portuguesa SP": "Portuguesa",
  "Corinthians SP": "Corinthians",
  "Palmeiras SP": "Palmeiras",
  "Santos SP": "Santos",
  "Flamengo RJ": "Flamengo",
  "Atletico GO": "Atlético-GO",
  "Atletico MG": "Atlético-MG",
  "Atletico PR": "Athletico-PR",
  "Athletico PR": "Athletico-PR",
  "America FC": "América-MG",
  "America FC Natal": "América-RN",
  "Parana PR": "Paraná",
  "CSA": "CSA",
  "CSA AL": "CSA",
  "Operario PR": "Operário-PR",
  "Operario": "Operário-PR",
};

/** Collapse whitespace and remove suffixes/affixes from a raw team name. */
export function normalizeTeamName(raw: string): string {
  let s = (raw ?? "").trim();
  // Collapse internal whitespace runs to single spaces.
  s = s.replace(/\s+/g, " ");

  // FIRST: check canonical display with the full name (including suffix).
  // This prevents ambiguity: "Atletico-PR" must not become "Atlético-MG".
  const canonFull = CANONICAL_DISPLAY[s];
  if (canonFull) return canonFull;

  // Strip trailing country code in parens: "Nacional (URU)"
  s = s.replace(/\s*\([A-Z]{2,4}\)$/, "");
  // Strip trailing state suffix: "Flamengo-RJ" or "Flamengo RJ" or "Flamengo - RJ"
  s = s.replace(/\s*-\s*([A-Z]{2})$/, (m, code) =>
    STATE_CODES.has(code) ? "" : m,
  );
  s = s.replace(/\s+([A-Z]{2})$/, (m, code) =>
    STATE_CODES.has(code) ? "" : m,
  );
  // Strip trailing country code after dash: "Barcelona-EQU"
  s = s.replace(/-[A-Z]{3,4}$/, "");
  s = s.trim();
  if (!s) s = (raw ?? "").trim();

  // Strip common club prefixes: "EC Bahia" → "Bahia"
  for (const p of CLUB_PREFIXES) {
    const re = new RegExp(`^${p}\\s+`, "i");
    if (re.test(s)) {
      s = s.replace(re, "").trim();
      break;
    }
  }
  // Strip common club suffixes: "Fortaleza FC" → "Fortaleza"
  for (const suf of CLUB_SUFFIXES) {
    const re = new RegExp(`\\s+${suf}$`, "i");
    if (re.test(s)) {
      s = s.replace(re, "").trim();
      break;
    }
  }

  // SECOND: check canonical display with the stripped name.
  const canon = CANONICAL_DISPLAY[s];
  if (canon) return canon;
  return s;
}

/**
 * Alias table mapping computed team keys to canonical keys.
 * This collapses remaining mismatches after normalizeTeamName.
 * Keys are already lowercase, accent-folded.
 */
const TEAM_ALIASES: Record<string, string> = {
  // Atlético Mineiro variants → "atletico mg"
  "atletico mineiro": "atletico mg",
  "atletico mg": "atletico mg",
  "america fc": "america mg",
  "america fc minas gerais": "america mg",
  "america minas gerais": "america mg",
  // Athletico Paranaense variants → "atletico pr"
  "atletico paranaense": "atletico pr",
  "athletico paranaense": "atletico pr",
  "athletico pr": "atletico pr",
  "atletico pr": "atletico pr",
  "atletico goianiense": "atletico go",
  "atletico go": "atletico go",
  // Botafogo variants
  "botafogo rj": "botafogo",
  "botafogo sp": "botafogo sp",
  "botafogo pb": "botafogo pb",
  // Bahia
  "ec bahia": "bahia",
  "bahia ba": "bahia",
  // Vitória
  "ec vitoria": "vitoria",
  "vitoria ba": "vitoria",
  "vitoria es": "vitoria es",
  // Fortaleza
  "fortaleza fc": "fortaleza",
  "fortaleza ec": "fortaleza",
  "fortaleza ce": "fortaleza",
  // Coritiba
  "coritiba pr": "coritiba",
  // Cuiabá
  "cuiaba mt": "cuiaba",
  // Criciúma
  "criciuma sc": "criciuma",
  // Vasco
  "vasco da gama rj": "vasco da gama",
  "vasco rj": "vasco da gama",
  // Juventude
  "ec juven": "juventude",
  "ec juventude": "juventude",
  "juventude rs": "juventude",
  // Bragantino
  "rb bragantino": "bragantino",
  // Grêmio
  "gremio rs": "gremio",
  // Internacional
  "internacional rs": "internacional",
  "ec internacional sc": "internacional sc",
  // São Paulo
  "sao paulo sp": "sao paulo",
  // Fluminense
  "fluminense rj": "fluminense",
  // Sport
  "sport pe": "sport",
  "sport club do recife": "sport",
  // CSA
  "csa al": "csa",
  "cs alagoano": "csa",
  // Chapecoense
  "chapecoense sc": "chapecoense",
  // Goiás
  "goias go": "goias",
  // Avaí
  "avai sc": "avai",
  // Náutico
  "nautico pe": "nautico",
  // Figueirense
  "figueirense sc": "figueirense",
  // Portuguesa
  "portuguesa sp": "portuguesa",
  // Operário
  "operario pr": "operario pr",
  // Confiança
  "confianca se": "confianca",
  "ad confianca": "confianca",
  // CRB
  "crb al": "crb",
  // Ceará
  "ceara ce": "ceara",
  "ceara sporting club": "ceara",
  // Paraná
  "parana pr": "parana",
  // America RN
  "america rn": "america rn",
  "america fc natal": "america rn",
};

/** Fold a team name into a tolerant lookup key (lowercase, ASCII, no punctuation). */
export function teamKey(name: string): string {
  let key = (name ?? "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "") // strip combining diacritics
    .replace(/[^a-z0-9]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  // Apply alias mapping to collapse remaining mismatches.
  const aliased = TEAM_ALIASES[key];
  if (aliased) return aliased;
  return key;
}

/** Parse the heterogeneous date formats present in the datasets. */
export function parseDate(raw: string): Date | null {
  if (!raw) return null;
  const v = String(raw).trim();
  if (!v || /^na$/i.test(v)) return null;
  // ISO with optional time: 2023-09-24 or 2023-09-24 20:00:00
  let m = v.match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?$/);
  if (m) {
    const [, y, mo, d, hh, mm, ss] = m;
    return new Date(
      Date.UTC(+y, +mo - 1, +d, hh ? +hh : 0, mm ? +mm : 0, ss ? +ss : 0),
    );
  }
  // Brazilian DD/MM/YYYY (optionally with time): 29/03/2003
  m = v.match(/^(\d{2})\/(\d{2})\/(\d{4})(?:\s+(\d{2}):(\d{2})(?::(\d{2}))?)?$/);
  if (m) {
    const [, d, mo, y, hh, mm, ss] = m;
    return new Date(
      Date.UTC(+y, +mo - 1, +d, hh ? +hh : 0, mm ? +mm : 0, ss ? +ss : 0),
    );
  }
  // Fallback: let JS parse; if invalid, return null.
  const d = new Date(v);
  return isNaN(d.getTime()) ? null : d;
}

/** Format a Date (or null) as an ISO date string (YYYY-MM-DD). */
export function formatDate(date: Date | null): string {
  if (!date) return "unknown";
  return date.toISOString().slice(0, 10);
}

/** Parse a numeric value that may be empty, fractional, or quoted. */
export function parseNumber(raw: unknown): number | null {
  if (raw === null || raw === undefined) return null;
  const s = String(raw).trim();
  if (s === "") return null;
  const n = Number(s);
  return isNaN(n) ? null : n;
}

/** Extract the base integer from a "88+2" style FIFA skill rating. */
export function parseSkill(raw: unknown): number | null {
  const n = parseNumber(raw);
  return n === null ? null : Math.trunc(n);
}
