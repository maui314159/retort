/**
 * Normalization helpers: team-name keys, date parsing, competition labels.
 *
 * The source datasets disagree on naming ("Palmeiras-SP" vs "Palmeiras",
 * "Gremio-RS" vs "Grêmio") and on date formats ("2023-09-24",
 * "2012-05-19 18:30:00", "29/03/2003"). All lookups in the knowledge graph
 * go through these normalizers so cross-file queries join correctly.
 */

/** Strip diacritics: "Grêmio" -> "Gremio", "São Paulo" -> "Sao Paulo". */
export function stripAccents(input: string): string {
  // Remove combining diacritical marks (U+0300–U+036F) after NFD split.
  return input.normalize("NFD").replace(/[̀-ͯ]/g, "");
}

/** Brazilian state abbreviations used as suffixes in team names. */
const STATE_CODES = new Set([
  "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
  "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
  "SP", "SE", "TO",
]);

/** Noise words removed when building loose-matching aliases. */
const NOISE_WORDS = new Set([
  "club", "clube", "de", "do", "da", "dos", "das", "e", "fc", "ec", "sc",
  "ca", "cr", "se", "regatas", "football", "futebol", "antigo",
  "sociedade", "associacao",
]);

/**
 * Canonical lookup key for a team name.
 * "Palmeiras-SP" -> "palmeiras", "América - MG" -> "america",
 * "Grêmio" -> "gremio".
 */
export function normalizeTeamName(name: string): string {
  if (!name) return "";
  let s = stripAccents(name).trim().toLowerCase();

  // Cut parenthetical qualifiers: "Barcelona (EQU)" -> "Barcelona"
  s = s.replace(/[([].*?[)\]]/g, " ");

  // Drop trailing state suffix: "-SP", "- MG", "/RJ" ...
  const tokens = s.split(/[\s\-/|]+/).filter(Boolean);
  while (tokens.length > 1 && STATE_CODES.has(tokens[tokens.length - 1].toUpperCase())) {
    tokens.pop();
  }
  s = tokens.join(" ");

  // Collapse anything that is not a letter/digit into single spaces.
  s = s.replace(/[^a-z0-9]+/g, " ").trim();
  return s;
}

/**
 * Loose alias key with club-noise words removed, used as a fallback so that
 * "Sport Club Corinthians Paulista" and "Corinthians" still match.
 */
export function teamAliasKey(name: string): string {
  const key = normalizeTeamName(name);
  const tokens = key.split(" ").filter((t) => !NOISE_WORDS.has(t));
  return tokens.join(" ");
}

/**
 * Return true when two team names plausibly refer to the same club:
 * exact normalized key, exact alias key, or one alias containing the other
 * (guarded so single generic tokens like "america" do not over-match).
 */
export function teamNamesMatch(a: string, b: string): boolean {
  const ka = normalizeTeamName(a);
  const kb = normalizeTeamName(b);
  if (!ka || !kb) return false;
  if (ka === kb) return true;

  const aa = teamAliasKey(a);
  const ab = teamAliasKey(b);
  if (!aa || !ab) return false;
  if (aa === ab) return true;

  const shorter = aa.length <= ab.length ? aa : ab;
  const longer = aa.length <= ab.length ? ab : aa;
  // Substring match only when the shorter alias has >= 5 chars or 2+ tokens,
  // avoiding false positives like "america" ~ "america mineiro" being kept
  // intentional (they are treated as the same club family in these datasets
  // anyway since state suffixes were stripped before aliasing).
  if (longer.includes(shorter) && (shorter.length >= 5 || shorter.includes(" "))) {
    return true;
  }
  return false;
}

/**
 * Parse the date formats present in the datasets into ISO YYYY-MM-DD:
 *  - "2023-09-24"
 *  - "2012-05-19 18:30:00"
 *  - "29/03/2003" (Brazilian DD/MM/YYYY)
 * Returns null when unparseable.
 */
export function parseDate(raw: string | null | undefined): string | null {
  if (!raw) return null;
  const s = raw.trim();
  if (!s) return null;

  // ISO-like: YYYY-MM-DD optionally followed by time.
  let m = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
  if (m) {
    return `${m[1]}-${m[2].padStart(2, "0")}-${m[3].padStart(2, "0")}`;
  }
  // Brazilian: DD/MM/YYYY
  m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (m) {
    return `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}`;
  }
  return null;
}

/** Safe integer parse that tolerates floats ("1.0") and junk. */
export function parseScore(raw: unknown): number | null {
  if (raw === null || raw === undefined) return null;
  const s = String(raw).trim();
  if (!s) return null;
  const n = Number(s);
  if (!Number.isFinite(n)) return null;
  return Math.trunc(n);
}

/** Map a raw competition/tournament label to a canonical label. */
export function normalizeCompetition(raw: string, sourceFile: string): string {
  const s = stripAccents(raw).toLowerCase().trim();
  if (sourceFile === "Brasileirao_Matches.csv" || sourceFile === "novo_campeonato_brasileiro.csv") {
    return "Brasileirão Série A";
  }
  if (sourceFile === "Brazilian_Cup_Matches.csv") return "Copa do Brasil";
  if (sourceFile === "Libertadores_Matches.csv") return "Copa Libertadores";
  // BR-Football-Dataset.csv uses its `tournament` column.
  if (s === "serie a") return "Brasileirão Série A";
  if (s === "serie b") return "Brasileirão Série B";
  if (s === "serie c") return "Brasileirão Série C";
  if (s.includes("copa do brasil")) return "Copa do Brasil";
  if (s.includes("libertadores")) return "Copa Libertadores";
  return raw.trim();
}

/**
 * Canonical competition key for comparison: reduces labels like
 * "Brasileirão Série A", "Serie A" and "Campeonato Brasileiro" to the same
 * key, while keeping "Série B" / "Série C" strictly distinct.
 */
function competitionKey(raw: string): string {
  const s = stripAccents(raw).toLowerCase().trim();
  if (s.includes("libertadores")) return "libertadores";
  if (s.includes("copa do brasil") || s.includes("brazilian cup")) return "copa do brasil";
  if (s.includes("serie b")) return "serie b";
  if (s.includes("serie c")) return "serie c";
  if (s.includes("serie a") || s.includes("brasileirao") || s.includes("campeonato brasileiro")) {
    return "serie a";
  }
  return s;
}

/** Fuzzy competition match for query filters. */
export function competitionMatches(filter: string, competition: string): boolean {
  const f = stripAccents(filter).toLowerCase().trim();
  const c = stripAccents(competition).toLowerCase().trim();
  if (!f) return true;
  if (c === f || c.includes(f) || f.includes(c)) return true;
  const kf = competitionKey(filter);
  const kc = competitionKey(competition);
  if (kf === kc) return true;
  // Alias family: "brasileirao" ~ "serie a", "libertadores" ~ "copa libertadores".
  if (kf.length >= 5 && kc.length >= 5 && (kf.includes(kc) || kc.includes(kf))) return true;
  return false;
}
