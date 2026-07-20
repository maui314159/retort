/**
 * Text normalization utilities.
 *
 * The six source CSVs use conflicting conventions for team names and dates:
 *   - "Palmeiras-SP" (state suffix, no spaces)
 *   - "América - MG" (state suffix, spaced dash)
 *   - "America MG" / "Atletico Mineiro" / "EC Bahia" (BR-Football style)
 *   - "Nacional (URU)" / "Barcelona-EQU" (country tags)
 *   - "Sport Club Corinthians Paulista" (full legal name)
 * plus three date formats: ISO, ISO-with-time, and DD/MM/YYYY.
 *
 * Because the same real-world club (and match) appears in several files,
 * every raw name is mapped to a canonical club key via (a) a generic
 * surface normalization and (b) a curated alias table for Brazilian
 * league clubs whose surface forms diverge across files. Canonical keys
 * drive grouping, joining and cross-file deduplication; display names
 * keep their original UTF-8 characters for output.
 */

/** Strip diacritics: "São Paulo" -> "Sao Paulo", "Grêmio" -> "Gremio". */
export function foldAccents(s: string): string {
  return s.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

/**
 * Surface key: fold accents, lowercase, drop parenthetical tags and
 * legal-form words/tokens, collapse to alphanumerics. Trailing state /
 * country codes ("-SP", " - MG", "-EQU") are KEPT in the key at this
 * stage so that "Atlético-MG" and "Atlético-GO" do not collide; the
 * alias table below resolves them to stable club ids.
 */
function surfaceKey(raw: string): string {
  let s = foldAccents(raw).toLowerCase().trim();
  s = s.replace(/\([^)]*\)/g, " ");
  s = s.replace(
    /\b(esporte clube|sport club|futebol clube|clube de regatas|sociedade esportiva|foot[\s-]?ball club)\b/g,
    " ",
  );
  // Standalone short legal tokens: "EC Bahia", "Fortaleza FC", "Santa Cruz FC".
  s = s.replace(/\b(ec|fc|afc|cf)\b/g, " ");
  s = s.replace(/[^a-z0-9]+/g, "");
  return s;
}

/**
 * Curated alias table mapping surface keys to canonical club ids for
 * Brazilian clubs whose names diverge across the six source files.
 * Club ids are short human-readable slugs; unlisted surface forms fall
 * back to their surface key (state/country codes stripped, see below).
 */
const CLUB_ALIASES = new Map<string, string>([
  // --- Série A regulars ---
  ["palmeirassp", "palmeiras"], ["palmeiras", "palmeiras"],
  ["flamengorj", "flamengo"], ["flamengo", "flamengo"],
  ["fluminenserj", "fluminense"], ["fluminense", "fluminense"],
  ["corinthianssp", "corinthians"], ["corinthians", "corinthians"],
  ["corinthianspaulista", "corinthians"],
  ["saopaulosp", "saopaulo"], ["saopaulo", "saopaulo"],
  ["santossp", "santos"], ["santos", "santos"],
  ["gremiors", "gremio"], ["gremio", "gremio"],
  ["gremioportoalegrense", "gremio"],
  ["internacionalrs", "internacional"], ["internacional", "internacional"],
  ["cruzeiromg", "cruzeiro"], ["cruzeiro", "cruzeiro"],
  ["vascorj", "vasco"], ["vasco", "vasco"],
  ["vascodagamarj", "vasco"], ["vascodagama", "vasco"],
  ["botafogorj", "botafogo"], ["botafogo", "botafogo"],
  // --- Ambiguous "Atlético"/"America"/"Sport" family (state retained) ---
  ["atleticomg", "atletico-mg"], ["atleticomineiro", "atletico-mg"],
  ["atleticogo", "atletico-go"], ["atleticogoianiense", "atletico-go"],
  ["atleticopr", "athletico-pr"], ["athleticopr", "athletico-pr"],
  ["atleticoparanaense", "athletico-pr"], ["athleticoparanaense", "athletico-pr"],
  ["atleticoparanaensepr", "athletico-pr"], ["athleticoparanaensepr", "athletico-pr"],
  ["atleticomineiromg", "atletico-mg"], ["atleticogoianiensego", "atletico-go"],
  ["athletico", "athletico-pr"],
  ["americamg", "america-mg"], ["americaminasgerais", "america-mg"],
  ["americarn", "america-rn"],
  ["sportpe", "sport"], ["sport", "sport"], ["sportrecife", "sport"],
  ["sportdorecife", "sport"],
  // --- Other recurring national clubs ---
  ["bahiaba", "bahia"], ["bahia", "bahia"],
  ["vitoriaba", "vitoria"], ["vitoria", "vitoria"],
  ["fortalezace", "fortaleza"], ["fortaleza", "fortaleza"],
  ["cearace", "ceara"], ["ceara", "ceara"], ["cearasporting", "ceara"],
  ["chapecoensesc", "chapecoense"], ["chapecoense", "chapecoense"],
  ["goiasgo", "goias"], ["goias", "goias"],
  ["cuiabamt", "cuiaba"], ["cuiaba", "cuiaba"],
  ["coritibapr", "coritiba"], ["coritiba", "coritiba"],
  ["criciumasc", "criciuma"], ["criciuma", "criciuma"],
  ["figueirenscesc", "figueirense"], ["figueirense", "figueirense"],
  ["joinvillesc", "joinville"], ["joinville", "joinville"],
  ["avaisc", "avai"], ["avai", "avai"],
  ["pontepretasp", "pontepreta"], ["pontepreta", "pontepreta"],
  ["paranapr", "parana"], ["parana", "parana"],
  ["bragantinosp", "bragantino"], ["bragantino", "bragantino"],
  ["redbullbragantinosp", "bragantino"], ["redbullbragantino", "bragantino"],
  ["santacruzpe", "santacruz"], ["santacruz", "santacruz"],
  ["nauticope", "nautico"], ["nautico", "nautico"],
  ["guaranisp", "guarani"], ["guarani", "guarani"],
  ["portuguesasp", "portuguesa"], ["portuguesa", "portuguesa"],
  ["saocaetanosp", "saocaetano"], ["saocaetano", "saocaetano"],
  ["santoandresp", "santoandre"], ["santoandre", "santoandre"],
  ["juventuders", "juventude"], ["juventude", "juventude"],
  ["atleticoba", "atletico-ba"],
  ["gremiobaruerisp", "gremioprudente"], ["gremiobarueri", "gremioprudente"],
  ["gremioprudentesp", "gremioprudente"], ["gremioprudente", "gremioprudente"],
  ["ipatingamg", "ipatinga"], ["ipatinga", "ipatinga"],
  ["brasiliensedf", "brasiliense"], ["brasiliense", "brasiliense"],
  ["baruerisp", "barueri"], ["barueri", "barueri"],
  ["csaal", "csa"], ["csa", "csa"],
]);

/**
 * Canonical club key. Aliased clubs resolve to their club id; everything
 * else falls back to the surface key with trailing state/country codes
 * stripped (small state-league clubs, foreign clubs).
 */
export function canonicalTeamKey(raw: string): string {
  const surface = surfaceKey(raw);
  const aliased = CLUB_ALIASES.get(surface);
  if (aliased) return aliased;
  // Generic fallback: strip trailing "-XX" state/country tags.
  let s = foldAccents(raw).toLowerCase().trim();
  s = s.replace(/\([^)]*\)/g, " ");
  s = s.replace(
    /\b(esporte clube|sport club|futebol clube|clube de regatas|sociedade esportiva)\b/g,
    " ",
  );
  for (let i = 0; i < 3; i++) {
    s = s.replace(/\s*[-–—]\s*[a-z]{2,3}\s*$/i, "").trim();
  }
  s = s.replace(/\b(ec|fc|afc|cf)\b/g, " ");
  return s.replace(/[^a-z0-9]+/g, "");
}

/**
 * Produce a clean display name from a raw source name:
 * strips state/country suffixes and parenthetical tags but keeps accents.
 * "Palmeiras-SP" -> "Palmeiras", "Nacional (URU)" -> "Nacional".
 */
export function displayTeamName(raw: string): string {
  let s = raw.trim();
  s = s.replace(/\([^)]*\)/g, " ");
  for (let i = 0; i < 3; i++) {
    s = s.replace(/\s*[-–—]\s*[A-Z]{2,3}\s*$/, "").trim();
  }
  return s.replace(/\s+/g, " ").trim();
}

/**
 * Does `raw` refer to the team the user asked for (`query`)?
 * Matches on canonical key equality, or when one key contains the other
 * (so an unqualified "Remo" query still matches "Remo - PA").
 */
export function teamMatches(raw: string, query: string): boolean {
  const a = canonicalTeamKey(raw);
  const b = canonicalTeamKey(query);
  if (!a || !b) return false;
  return a === b || a.includes(b) || b.includes(a);
}

/**
 * Canonical display names for aliased clubs — unambiguous and correctly
 * accented ("Atlético-MG" vs "Atlético-GO", which would both display as
 * "Atlético" if the state suffix were simply stripped).
 */
const CLUB_DISPLAY = new Map<string, string>([
  ["palmeiras", "Palmeiras"], ["flamengo", "Flamengo"],
  ["fluminense", "Fluminense"], ["corinthians", "Corinthians"],
  ["saopaulo", "São Paulo"], ["santos", "Santos"],
  ["gremio", "Grêmio"], ["internacional", "Internacional"],
  ["cruzeiro", "Cruzeiro"], ["vasco", "Vasco"],
  ["botafogo", "Botafogo"], ["atletico-mg", "Atlético-MG"],
  ["atletico-go", "Atlético-GO"], ["athletico-pr", "Athletico-PR"],
  ["america-mg", "América-MG"], ["america-rn", "América-RN"],
  ["sport", "Sport"], ["bahia", "Bahia"], ["vitoria", "Vitória"],
  ["fortaleza", "Fortaleza"], ["ceara", "Ceará"],
  ["chapecoense", "Chapecoense"], ["goias", "Goiás"],
  ["cuiaba", "Cuiabá"], ["coritiba", "Coritiba"],
  ["criciuma", "Criciúma"], ["figueirense", "Figueirense"],
  ["joinville", "Joinville"], ["avai", "Avaí"],
  ["pontepreta", "Ponte Preta"], ["parana", "Paraná"],
  ["bragantino", "Bragantino"], ["santacruz", "Santa Cruz"],
  ["nautico", "Náutico"], ["guarani", "Guarani"],
  ["portuguesa", "Portuguesa"], ["saocaetano", "São Caetano"],
  ["santoandre", "Santo André"], ["juventude", "Juventude"],
  ["atletico-ba", "Atlético-BA"], ["gremioprudente", "Grêmio Prudente"],
  ["ipatinga", "Ipatinga"], ["brasiliense", "Brasiliense"],
  ["barueri", "Barueri"], ["csa", "CSA"],
]);

/**
 * Display name for a raw team name: canonical display for aliased clubs,
 * suffix-stripped original (accents kept) for everything else.
 */
export function canonicalDisplay(raw: string): string {
  const key = canonicalTeamKey(raw);
  return CLUB_DISPLAY.get(key) ?? displayTeamName(raw);
}

/**
 * Parse a date in any of the source formats into ISO YYYY-MM-DD.
 * Supported: "2023-09-24", "2012-05-19 18:30:00", "29/03/2003".
 * Returns null for unparseable input.
 */
export function parseDate(raw: string | null | undefined): string | null {
  if (!raw) return null;
  const s = raw.trim();
  if (!s) return null;

  // Brazilian DD/MM/YYYY
  const br = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (br) {
    const [, d, m, y] = br;
    return `${y}-${m.padStart(2, "0")}-${d.padStart(2, "0")}`;
  }

  // ISO date or ISO datetime: take the leading YYYY-MM-DD
  const iso = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (iso) return `${iso[1]}-${iso[2]}-${iso[3]}`;

  return null;
}

/** Extract the year from any supported date string. */
export function parseYear(raw: string | null | undefined): number | null {
  const iso = parseDate(raw);
  if (iso) return Number(iso.slice(0, 4));
  const s = (raw ?? "").trim();
  const y = s.match(/(\d{4})/);
  return y ? Number(y[1]) : null;
}

/** Lenient integer parse: handles "1", "1.0", "\"2\"" — null-safe. */
export function toInt(raw: unknown): number | null {
  if (raw === null || raw === undefined) return null;
  const n = Number(String(raw).trim());
  return Number.isFinite(n) ? Math.trunc(n) : null;
}

/** Lenient float parse (BR-Football-Dataset stores goals as "1.0"). */
export function toFloat(raw: unknown): number | null {
  if (raw === null || raw === undefined) return null;
  const n = Number(String(raw).trim());
  return Number.isFinite(n) ? n : null;
}
