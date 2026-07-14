/**
 * Brazilian Soccer MCP Server - CSV Loader & Team Name Normalizer
 *
 * Loads all 6 CSV datasets into unified MatchRecord/PlayerRecord arrays.
 * Handles the diverse CSV schemas (different column names, date formats,
 * team name conventions with state suffixes) and normalizes them into
 * a consistent internal representation.
 *
 * Team name normalization strips state suffixes (e.g., "Palmeiras-SP" → "Palmeiras")
 * and trims parenthetical annotations so that lookups work across datasets that
 * use different naming conventions for the same club.
 */

import { readFileSync } from "node:fs";
import { parse } from "csv-parse/sync";
import { join, resolve } from "node:path";
import type { Competition, MatchRecord, PlayerRecord } from "./types.js";

// ── Team Name Normalization ──────────────────────────────────────────

/** Known team name aliases mapping variant forms to canonical name. */
const TEAM_ALIASES: Record<string, string> = {
  // Common alternate spellings / abbreviations across datasets
  "athletico paranaense": "Athletico-PR",
  "atletico paranaense": "Athletico-PR",
  "athletico-go": "Atlético-GO",
  "atletico-go": "Atlético-GO",
  "atletico goianiense": "Atlético-GO",
  "athletico goianiense": "Atlético-GO",
  "atletico mineiro": "Atlético-MG",
  "atletico-mg": "Atlético-MG",
  "america-mg": "América-MG",
  "america mineiro": "América-MG",
  "america-rn": "América-RN",
  "bahia de feira": "Bahia de Feira",
  "botafogo-rj": "Botafogo",
  "botafogo sp": "Botafogo-SP",
  "botafogo-sp": "Botafogo-SP",
  "coritiba fc": "Coritiba",
  "criciuma ec": "Criciúma",
  "csa alagoano": "CSA",
  "ceara sc": "Ceará",
  "chapecoense-sc": "Chapecoense",
  "fortaleza esporte clube": "Fortaleza",
  "goias ec": "Goiás",
  "guarani fc": "Guarani",
  "internacional-rs": "Internacional",
  "ipatinga fc": "Ipatinga",
  "nautico cap": "Náutico",
  "parana clube": "Paraná",
  "paysandu sc": "Paysandu",
  "portuguesa sp": "Portuguesa",
  "santa cruz fc": "Santa Cruz",
  "sao paulo": "São Paulo",
  "sport recife": "Sport",
  "sport club do recife": "Sport",
  "vasco da gama": "Vasco",
  "vila nova fc": "Vila Nova",
  "cuiaba ec": "Cuiabá",
  "cuiaba": "Cuiabá",
  "avai fc": "Avaí",
  "avai": "Avaí",
  "bragantino": "Red Bull Bragantino",
  "rb bragantino": "Red Bull Bragantino",
  "rb leipzig": "RB Leipzig",
};

/**
 * Normalize a team name to its canonical form.
 * 1. Strip state suffix (e.g. "-SP", " - RJ")
 * 2. Strip parenthetical annotations like "(antigo Esporte Clube Barreira)"
 * 3. Trim and lowercase for alias lookup
 * 4. Return title-cased canonical form
 */
export function normalizeTeamName(raw: string): string {
  if (!raw) return raw;

  let name = raw.trim();

  // Strip parenthetical annotations, e.g. "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"
  name = name.replace(/\s*\([^)]*\)\s*/g, " ").trim();

  // Strip state suffix: " - RJ", "-SP", " - SP"
  name = name.replace(/\s*-\s*[A-Z]{2}\s*$/, "").trim();

  const lower = name.toLowerCase();

  // Check alias map
  if (TEAM_ALIASES[lower]) {
    return TEAM_ALIASES[lower];
  }

  // Title-case the remaining name (preserve known accented forms)
  return toTitleCase(name);
}

/** Minimal title-case that preserves existing capitalization of accented chars. */
function toTitleCase(s: string): string {
  return s
    .split(/\s+/)
    .map((word) => {
      if (word.length === 0) return word;
      // Preserve acronyms like "FC", "SC", "EC"
      if (word === word.toUpperCase() && word.length <= 3) return word;
      return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
    })
    .join(" ");
}

// ── CSV Parsing Helpers ──────────────────────────────────────────────

function csvPath(filename: string): string {
  return resolve(process.env.DATA_DIR ?? join(process.cwd(), "data", "kaggle"), filename);
}

function readCsv(filename: string): Record<string, string>[] {
  const buf = readFileSync(csvPath(filename));
  return parse(buf, {
    columns: true,
    skip_empty_lines: true,
    bom: true,
    relax_column_count: true,
  });
}

function parseIntSafe(v: string | undefined): number {
  if (!v) return 0;
  const n = parseInt(v, 10);
  return Number.isNaN(n) ? 0 : n;
}

function parseFloatSafe(v: string | undefined): number {
  if (!v) return 0;
  const n = parseFloat(v);
  return Number.isNaN(n) ? 0 : n;
}

/** Parse date strings from various formats into ISO YYYY-MM-DD. */
function normalizeDate(raw: string | undefined): string {
  if (!raw) return "";
  const s = raw.trim();

  // ISO with time: "2012-05-19 18:30:00"
  const isoMatch = s.match(/^(\d{4}-\d{2}-\d{2})/);
  if (isoMatch) return isoMatch[1];

  // Brazilian format: "29/03/2003"
  const brMatch = s.match(/^(\d{2})\/(\d{2})\/(\d{4})/);
  if (brMatch) return `${brMatch[3]}-${brMatch[2]}-${brMatch[1]}`;

  return s;
}

// ── Dataset Loaders ──────────────────────────────────────────────────

function loadBrasileiraoMatches(): MatchRecord[] {
  return readCsv("Brasileirao_Matches.csv").map((r) => ({
    date: normalizeDate(r.datetime),
    homeTeam: normalizeTeamName(r.home_team),
    awayTeam: normalizeTeamName(r.away_team),
    homeGoals: parseIntSafe(r.home_goal),
    awayGoals: parseIntSafe(r.away_goal),
    season: parseIntSafe(r.season),
    competition: "Brasileirão" as Competition,
    round: r.round,
    homeState: r.home_team_state,
    awayState: r.away_team_state,
  }));
}

function loadCopaDoBrasilMatches(): MatchRecord[] {
  return readCsv("Brazilian_Cup_Matches.csv").map((r) => ({
    date: normalizeDate(r.datetime),
    homeTeam: normalizeTeamName(r.home_team),
    awayTeam: normalizeTeamName(r.away_team),
    homeGoals: parseIntSafe(r.home_goal),
    awayGoals: parseIntSafe(r.away_goal),
    season: parseIntSafe(r.season),
    competition: "Copa do Brasil" as Competition,
    round: r.round,
  }));
}

function loadLibertadoresMatches(): MatchRecord[] {
  return readCsv("Libertadores_Matches.csv").map((r) => ({
    date: normalizeDate(r.datetime),
    homeTeam: normalizeTeamName(r.home_team),
    awayTeam: normalizeTeamName(r.away_team),
    homeGoals: parseIntSafe(r.home_goal),
    awayGoals: parseIntSafe(r.away_goal),
    season: parseIntSafe(r.season),
    competition: "Libertadores" as Competition,
    stage: r.stage,
  }));
}

function loadBRFootballDataset(): MatchRecord[] {
  return readCsv("BR-Football-Dataset.csv").map((r) => {
    const tournament = (r.tournament || "").trim();
    let competition: Competition = "Other";
    if (/brasileir[oã]|s[eé]rie\s*a/i.test(tournament)) competition = "Brasileirão";
    else if (/copa do brasil/i.test(tournament)) competition = "Copa do Brasil";
    else if (/libertadores/i.test(tournament)) competition = "Libertadores";

    return {
      date: normalizeDate(r.date),
      homeTeam: normalizeTeamName(r.home),
      awayTeam: normalizeTeamName(r.away),
      homeGoals: parseFloatSafe(r.home_goal),
      awayGoals: parseFloatSafe(r.away_goal),
      season: normalizeDate(r.date) ? parseInt(normalizeDate(r.date).slice(0, 4)) : 0,
      competition,
      homeCorners: parseFloatSafe(r.home_corner),
      awayCorners: parseFloatSafe(r.away_corner),
      homeAttacks: parseFloatSafe(r.home_attack),
      awayAttacks: parseFloatSafe(r.away_attack),
      homeShots: parseFloatSafe(r.home_shots),
      awayShots: parseFloatSafe(r.away_shots),
    };
  });
}

function loadHistoricalBrasileirao(): MatchRecord[] {
  return readCsv("novo_campeonato_brasileiro.csv").map((r) => ({
    date: normalizeDate(r.Data),
    homeTeam: normalizeTeamName(r.Equipe_mandante),
    awayTeam: normalizeTeamName(r.Equipe_visitante),
    homeGoals: parseIntSafe(r.Gols_mandante),
    awayGoals: parseIntSafe(r.Gols_visitante),
    season: parseIntSafe(r.Ano),
    competition: "Historical Brasileirão" as Competition,
    round: r.Rodada,
    stadium: r.Arena,
    homeState: r.Mandante_UF,
    awayState: r.Visitante_UF,
  }));
}

function loadFifaPlayers(): PlayerRecord[] {
  return readCsv("fifa_data.csv").map((r) => ({
    id: parseIntSafe(r.ID),
    name: (r.Name || "").trim(),
    age: parseIntSafe(r.Age),
    nationality: (r.Nationality || "").trim(),
    overall: parseIntSafe(r.Overall),
    potential: parseIntSafe(r.Potential),
    club: (r.Club || "").trim(),
    position: (r.Position || "").trim(),
    jerseyNumber: parseIntSafe(r["Jersey Number"]),
    height: (r.Height || "").trim(),
    weight: (r.Weight || "").trim(),
    preferredFoot: (r["Preferred Foot"] || "").trim(),
    crossing: parseIntSafe(r.Crossing),
    finishing: parseIntSafe(r.Finishing),
    headingAccuracy: parseIntSafe(r.HeadingAccuracy),
    shortPassing: parseIntSafe(r.ShortPassing),
    dribbling: parseIntSafe(r.Dribbling),
    curve: parseIntSafe(r.Curve),
    fkAccuracy: parseIntSafe(r.FKAccuracy),
    longPassing: parseIntSafe(r.LongPassing),
    ballControl: parseIntSafe(r.BallControl),
    acceleration: parseIntSafe(r.Acceleration),
    sprintSpeed: parseIntSafe(r.SprintSpeed),
    agility: parseIntSafe(r.Agility),
    reactions: parseIntSafe(r.Reactions),
    balance: parseIntSafe(r.Balance),
    shotPower: parseIntSafe(r.ShotPower),
    stamina: parseIntSafe(r.Stamina),
    strength: parseIntSafe(r.Strength),
    longShots: parseIntSafe(r.LongShots),
    aggression: parseIntSafe(r.Aggression),
    interceptions: parseIntSafe(r.Interceptions),
    positioning: parseIntSafe(r.Positioning),
    vision: parseIntSafe(r.Vision),
    penalties: parseIntSafe(r.Penalties),
    composure: parseIntSafe(r.Composure),
  }));
}

// ── Public Data Access ───────────────────────────────────────────────

export interface SoccerData {
  matches: MatchRecord[];
  players: PlayerRecord[];
}

let _cache: SoccerData | null = null;

/** Load all datasets (cached after first call). */
export function loadData(): SoccerData {
  if (_cache) return _cache;

  const matches: MatchRecord[] = [
    ...loadBrasileiraoMatches(),
    ...loadCopaDoBrasilMatches(),
    ...loadLibertadoresMatches(),
    ...loadBRFootballDataset(),
    ...loadHistoricalBrasileirao(),
  ];

  const players = loadFifaPlayers();

  _cache = { matches, players };
  return _cache;
}

/** Clear the data cache (useful for testing). */
export function clearCache(): void {
  _cache = null;
}
