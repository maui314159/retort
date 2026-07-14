import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { parse } from "csv-parse/sync";
import type { Match, Player } from "./types.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.resolve(__dirname, "../data/kaggle");

// Strip state suffix like "Palmeiras-SP" → "Palmeiras"
function normalizeTeamName(raw: string): string {
  if (!raw) return raw;
  return raw.replace(/\s*-\s*[A-Z]{2}$/, "").trim();
}

// Parse multiple date formats → ISO YYYY-MM-DD
function parseDate(raw: string): string {
  if (!raw) return "";
  const s = raw.trim();
  // Brazilian DD/MM/YYYY
  const br = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (br) return `${br[3]}-${br[2].padStart(2, "0")}-${br[1].padStart(2, "0")}`;
  // ISO with optional time
  const iso = s.match(/^(\d{4}-\d{2}-\d{2})/);
  if (iso) return iso[1];
  return s.substring(0, 10);
}

function toInt(v: unknown): number {
  const n = parseInt(String(v), 10);
  return isNaN(n) ? 0 : n;
}

function toFloat(v: unknown): number {
  const n = parseFloat(String(v));
  return isNaN(n) ? 0 : n;
}

function readCsv(filename: string): Record<string, string>[] {
  const file = path.join(DATA_DIR, filename);
  const content = fs.readFileSync(file);
  return parse(content, {
    columns: true,
    skip_empty_lines: true,
    relax_quotes: true,
    trim: true,
    bom: true,
  }) as Record<string, string>[];
}

function loadBrasileirao(): Match[] {
  const rows = readCsv("Brasileirao_Matches.csv");
  return rows.map((r) => ({
    date: parseDate(r.datetime),
    competition: "Brasileirao" as const,
    season: toInt(r.season),
    round: String(r.round),
    homeTeam: normalizeTeamName(r.home_team),
    awayTeam: normalizeTeamName(r.away_team),
    homeGoals: toInt(r.home_goal),
    awayGoals: toInt(r.away_goal),
    homeState: r.home_team_state,
    awayState: r.away_team_state,
  }));
}

function loadCopaDoBrasil(): Match[] {
  const rows = readCsv("Brazilian_Cup_Matches.csv");
  return rows.map((r) => ({
    date: parseDate(r.datetime),
    competition: "Copa do Brasil" as const,
    season: toInt(r.season),
    round: String(r.round),
    homeTeam: normalizeTeamName(r.home_team),
    awayTeam: normalizeTeamName(r.away_team),
    homeGoals: toInt(r.home_goal),
    awayGoals: toInt(r.away_goal),
  }));
}

function loadLibertadores(): Match[] {
  const rows = readCsv("Libertadores_Matches.csv");
  return rows.map((r) => ({
    date: parseDate(r.datetime),
    competition: "Libertadores" as const,
    season: toInt(r.season),
    stage: r.stage,
    homeTeam: normalizeTeamName(r.home_team),
    awayTeam: normalizeTeamName(r.away_team),
    homeGoals: toInt(r.home_goal),
    awayGoals: toInt(r.away_goal),
  }));
}

function loadExtended(): Match[] {
  const rows = readCsv("BR-Football-Dataset.csv");
  return rows.map((r) => ({
    date: parseDate(r.date),
    competition: "Extended" as const,
    season: r.date ? toInt(r.date.split("-")[0]) : 0,
    round: r.tournament,
    homeTeam: normalizeTeamName(r.home),
    awayTeam: normalizeTeamName(r.away),
    homeGoals: toFloat(r.home_goal),
    awayGoals: toFloat(r.away_goal),
    homeCorners: toFloat(r.home_corner),
    awayCorners: toFloat(r.away_corner),
    homeShots: toFloat(r.home_shots),
    awayShots: toFloat(r.away_shots),
  }));
}

function loadHistorical(): Match[] {
  const rows = readCsv("novo_campeonato_brasileiro.csv");
  return rows.map((r) => ({
    date: parseDate(r.Data),
    competition: "Brasileirao" as const,
    season: toInt(r.Ano),
    round: String(r.Rodada),
    homeTeam: normalizeTeamName(r.Equipe_mandante),
    awayTeam: normalizeTeamName(r.Equipe_visitante),
    homeGoals: toInt(r.Gols_mandante),
    awayGoals: toInt(r.Gols_visitante),
    homeState: r.Mandante_UF,
    awayState: r.Visitante_UF,
    arena: r.Arena,
  }));
}

function loadPlayers(): Player[] {
  const rows = readCsv("fifa_data.csv");
  return rows.map((r) => ({
    id: toInt(r.ID),
    name: r.Name?.trim() ?? "",
    age: toInt(r.Age),
    nationality: r.Nationality?.trim() ?? "",
    overall: toInt(r.Overall),
    potential: toInt(r.Potential),
    club: r.Club?.trim() ?? "",
    position: r.Position?.trim() ?? "",
    jerseyNumber: r["Jersey Number"] ? toInt(r["Jersey Number"]) : undefined,
    height: r.Height?.trim(),
    weight: r.Weight?.trim(),
    crossing: r.Crossing ? toInt(r.Crossing) : undefined,
    finishing: r.Finishing ? toInt(r.Finishing) : undefined,
    dribbling: r.Dribbling ? toInt(r.Dribbling) : undefined,
    shortPassing: r.ShortPassing ? toInt(r.ShortPassing) : undefined,
    longPassing: r.LongPassing ? toInt(r.LongPassing) : undefined,
    ballControl: r.BallControl ? toInt(r.BallControl) : undefined,
    acceleration: r.Acceleration ? toInt(r.Acceleration) : undefined,
    sprintSpeed: r.SprintSpeed ? toInt(r.SprintSpeed) : undefined,
    stamina: r.Stamina ? toInt(r.Stamina) : undefined,
    strength: r.Strength ? toInt(r.Strength) : undefined,
    reactions: r.Reactions ? toInt(r.Reactions) : undefined,
    composure: r.Composure ? toInt(r.Composure) : undefined,
    gkDiving: r.GKDiving ? toInt(r.GKDiving) : undefined,
    gkHandling: r.GKHandling ? toInt(r.GKHandling) : undefined,
    gkKicking: r.GKKicking ? toInt(r.GKKicking) : undefined,
    gkPositioning: r.GKPositioning ? toInt(r.GKPositioning) : undefined,
    gkReflexes: r.GKReflexes ? toInt(r.GKReflexes) : undefined,
  }));
}

// Singleton cache — loaded once on first access
let _matches: Match[] | null = null;
let _players: Player[] | null = null;

export function getAllMatches(): Match[] {
  if (_matches) return _matches;
  _matches = [
    ...loadBrasileirao(),
    ...loadCopaDoBrasil(),
    ...loadLibertadores(),
    ...loadExtended(),
    ...loadHistorical(),
  ];
  return _matches;
}

export function getAllPlayers(): Player[] {
  if (_players) return _players;
  _players = loadPlayers();
  return _players;
}

// For tests: inject mock data
export function _setMatchesForTest(matches: Match[]): void {
  _matches = matches;
}
export function _setPlayersForTest(players: Player[]): void {
  _players = players;
}
export function _resetCache(): void {
  _matches = null;
  _players = null;
}
