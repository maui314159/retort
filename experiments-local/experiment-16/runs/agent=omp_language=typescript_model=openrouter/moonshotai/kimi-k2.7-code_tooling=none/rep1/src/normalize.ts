/**
 * Normalization helpers for team names, dates, and numeric values.
 *
 * Brazilian soccer datasets are messy: state suffixes ("-SP"), full legal names,
 * accented characters, and multiple date formats all appear. This module
 * centralizes the cleanup so queries and data rows speak the same language.
 */

import { createHash } from "node:crypto";

const STOPWORDS = new Set([
  "futebol",
  "clube",
  "esporte",
  "club",
  "sociedade",
  "esportiva",
  "associação",
  "associacao",
  "desportiva",
  "desportos",
  "esportivo",
  "football",
]);

const STATE_SUFFIX_RE = /\s*-\s*([A-Za-z]{2})\s*$/;
const PARENS_RE = /\s*\([^)]*\)\s*$/;

function removeAccents(input: string): string {
  return input.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

/**
 * Turn a raw team name into normalized searchable text.
 *
 * Hyphenated state codes ("Flamengo-RJ") are converted to a trailing word
 * ("flamengo rj") so aliases can match both suffixed and unsuffixed forms.
 */
function cleanTokens(input: string): string {
  const lowered = removeAccents(input).toLowerCase();
  const withSpacedState = lowered.replace(STATE_SUFFIX_RE, " $1");
  const withoutParens = withSpacedState.replace(PARENS_RE, "");
  return withoutParens;
}

function tokenKey(input: string): string {
  return cleanTokens(input)
    .split(/\s+/)
    .filter((t) => t.length > 0 && !STOPWORDS.has(t))
    .sort()
    .join(" ");
}

interface ClubEntry {
  display: string;
  aliases: string[];
}

const CLUB_ALIASES: Record<string, ClubEntry> = {
  flamengo: { display: "Flamengo", aliases: ["flamengo", "crf", "clube de regatas do flamengo", "flamengo rj"] },
  palmeiras: { display: "Palmeiras", aliases: ["palmeiras", "sep", "sociedade esportiva palmeiras", "palmeiras sp"] },
  corinthians: { display: "Corinthians", aliases: ["corinthians", "sccp", "sport club corinthians paulista", "corinthians sp"] },
  "sao paulo": { display: "São Paulo", aliases: ["sao paulo", "spfc", "sao paulo fc", "são paulo", "sao paulo sp"] },
  santos: { display: "Santos", aliases: ["santos", "sfc", "santos sp"] },
  gremio: { display: "Grêmio", aliases: ["gremio", "gremio fbpa", "gremio rs"] },
  internacional: { display: "Internacional", aliases: ["internacional", "inter", "sport club internacional", "internacional rs"] },
  cruzeiro: { display: "Cruzeiro", aliases: ["cruzeiro", "cruzeiro esporte clube", "cruzeiro mg"] },
  "atletico mineiro": { display: "Atlético Mineiro", aliases: ["atletico mineiro", "atletico mg", "athletico mineiro", "galo", "clube atletico mineiro", "atletico mg"] },
  "atletico paranaense": { display: "Athletico Paranaense", aliases: ["atletico paranaense", "athletico paranaense", "atletico pr", "athletico pr", "furacao", "clube atletico paranaense", "atletico pr"] },
  fluminense: { display: "Fluminense", aliases: ["fluminense", "flu", "fluminense football club", "fluminense rj"] },
  botafogo: { display: "Botafogo", aliases: ["botafogo", "botafogo rj", "botafogo de futebol e regatas"] },
  vasco: { display: "Vasco da Gama", aliases: ["vasco", "vasco da gama", "vasco rj", "club de regatas vasco da gama", "vasco da gama rj"] },
  bahia: { display: "Bahia", aliases: ["bahia", "esporte clube bahia", "bahia ec", "ec bahia", "bahia ba"] },
  fortaleza: { display: "Fortaleza", aliases: ["fortaleza", "fortaleza esporte clube", "fortaleza fc", "fortaleza ce"] },
  ceara: { display: "Ceará", aliases: ["ceara", "ceara sporting club", "ceará", "ceara ce"] },
  sport: { display: "Sport Recife", aliases: ["sport", "sport recife", "sport club do recife", "sport pe"] },
  vitoria: { display: "Vitória", aliases: ["vitoria", "vitoria esporte clube", "vitória", "vitoria ba"] },
  goias: { display: "Goiás", aliases: ["goias", "goias esporte clube", "goiás", "goias go"] },
  coritiba: { display: "Coritiba", aliases: ["coritiba", "coritiba foot ball club", "coritiba pr"] },
  "ponte preta": { display: "Ponte Preta", aliases: ["ponte preta", "associacao atletica ponte preta", "ponte preta sp"] },
  nautico: { display: "Náutico", aliases: ["nautico", "nautico capibaribe", "náutico", "nautico pe"] },
  "america mineiro": { display: "América Mineiro", aliases: ["america mineiro", "america mg", "américa mineiro", "américa mg"] },
  chapecoense: { display: "Chapecoense", aliases: ["chapecoense", "associacao chapecoense de futebol", "chapecoense sc"] },
  avai: { display: "Avaí", aliases: ["avai", "avai fc", "avaí", "avai sc"] },
};

const ALIAS_TO_CANONICAL: Map<string, string> = new Map();
for (const [canonical, entry] of Object.entries(CLUB_ALIASES)) {
  ALIAS_TO_CANONICAL.set(canonical, canonical);
  for (const alias of entry.aliases) {
    ALIAS_TO_CANONICAL.set(tokenKey(alias), canonical);
  }
}

/**
 * Return the canonical key for a team name. If the name matches a known alias,
 * the alias map is used; otherwise a normalized token key is returned.
 */
export function teamKey(name: string | null | undefined): string {
  if (!name) return "";
  const trimmed = name.trim();

  // Try the full name with hyphenated state codes converted to words.
  const direct = ALIAS_TO_CANONICAL.get(tokenKey(trimmed));
  if (direct) return direct;

  // Fall back to the base name with the state suffix removed entirely.
  const base = trimmed.replace(STATE_SUFFIX_RE, "").trim();
  const baseAlias = ALIAS_TO_CANONICAL.get(tokenKey(base));
  if (baseAlias) return baseAlias;

  return tokenKey(base);
}

/**
 * Return a display name for a team key. Falls back to a cleaned version of the
 * raw name when no canonical alias exists.
 */
export function teamDisplay(name: string | null | undefined, key?: string): string {
  if (!name) return key ?? "Unknown";
  const k = key ?? teamKey(name);
  const canonical = CLUB_ALIASES[k];
  if (canonical) return canonical.display;
  let cleaned = cleanTokens(name)
    .replace(PARENS_RE, "")
    .replace(STATE_SUFFIX_RE, "")
    .replace(/\s+[a-z]{2}\s*$/, "")
    .trim();
  if (!cleaned) cleaned = name.trim();
  return cleaned
    .split(" ")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(" ");
}

/**
 * Normalize a competition name to a small set of categories.
 */
export function normalizeCompetition(name: string): string {
  const lower = removeAccents(name).toLowerCase().trim();
  if (lower.includes("libertadores")) return "Copa Libertadores";
  if (lower.includes("copa do brasil") || lower.includes("brazilian cup")) return "Copa do Brasil";
  if (lower.includes("brasileirao") || lower.includes("brasileirão") || lower.includes("serie a")) return "Brasileirão";
  return name.trim();
}

/**
 * Parse a goal value that may be integer, float, or empty.
 */
export function parseGoal(value: string | null | undefined): number | null {
  if (value === undefined || value === null || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? Math.trunc(n) : null;
}

/**
 * Parse dates in ISO, Brazilian (dd/mm/yyyy), or datetime formats.
 *
 * Returns a UTC Date set to midnight of the calendar date so that dates from
 * different datasets (some with times, some without) line up for deduplication.
 */
export function parseDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const trimmed = String(value).trim();
  if (!trimmed) return null;

  // ISO / SQL datetime: 2012-05-19 18:30:00 or 2023-09-24
  const isoMatch = trimmed.match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2}):(\d{2}))?/);
  if (isoMatch) {
    const year = Number(isoMatch[1]);
    const month = Number(isoMatch[2]) - 1;
    const day = Number(isoMatch[3]);
    if (day >= 1 && day <= 31 && month >= 0 && month < 12) {
      const d = new Date(Date.UTC(year, month, day));
      if (d.getUTCMonth() === month && d.getUTCDate() === day) return d;
    }
  }

  // Brazilian format: 29/03/2003
  const parts = trimmed.split("/");
  if (parts.length === 3) {
    const day = Number(parts[0]);
    const month = Number(parts[1]) - 1;
    const year = Number(parts[2]);
    if (year > 1900 && year < 2100 && month >= 0 && month < 12 && day >= 1 && day <= 31) {
      const d = new Date(Date.UTC(year, month, day));
      if (d.getUTCMonth() === month && d.getUTCDate() === day) return d;
    }
  }

  return null;
}

/**
 * Parse a season/year value from strings or numbers.
 */
export function parseSeason(value: string | number | null | undefined): number | null {
  if (value === undefined || value === null || value === "") return null;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) && n >= 1900 && n <= 2100 ? n : null;
}

/**
 * Deterministic short ID for a match row (used when no source ID exists).
 */
export function rowId(values: string[]): string {
  return createHash("sha256").update(values.join("|")).digest("hex").slice(0, 16);
}
