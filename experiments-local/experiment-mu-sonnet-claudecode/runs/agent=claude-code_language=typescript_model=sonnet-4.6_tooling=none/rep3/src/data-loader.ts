import { parse } from "csv-parse/sync";
import { readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import type { Match, Player } from "./types.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA_DIR = join(__dirname, "..", "data", "kaggle");

const BRAZILIAN_STATES = new Set([
  "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG",
  "PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"
]);

export function normalizeTeamName(name: string): string {
  if (!name) return name;
  const cleaned = name.trim();
  // Remove state suffix like "-SP", "-RJ" at the end
  const match = cleaned.match(/^(.+)-([A-Z]{2})$/);
  if (match && BRAZILIAN_STATES.has(match[2])) {
    return match[1].trim();
  }
  return cleaned;
}

export function teamMatches(stored: string, query: string): boolean {
  const normalizedStored = normalizeTeamName(stored).toLowerCase();
  const normalizedQuery = query.toLowerCase().trim();
  return (
    normalizedStored === normalizedQuery ||
    normalizedStored.includes(normalizedQuery) ||
    normalizedQuery.includes(normalizedStored)
  );
}

function parseDate(dateStr: string): Date | null {
  if (!dateStr || dateStr.trim() === "") return null;
  const s = dateStr.trim();

  // ISO with time: "2012-05-19 18:30:00"
  if (/^\d{4}-\d{2}-\d{2}/.test(s)) {
    const d = new Date(s.replace(" ", "T"));
    return isNaN(d.getTime()) ? null : d;
  }

  // Brazilian format: "29/03/2003"
  const brMatch = s.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (brMatch) {
    const d = new Date(`${brMatch[3]}-${brMatch[2]}-${brMatch[1]}`);
    return isNaN(d.getTime()) ? null : d;
  }

  return null;
}

function safeInt(val: string | undefined): number {
  if (!val || val.trim() === "") return 0;
  const n = parseInt(val.trim(), 10);
  return isNaN(n) ? 0 : n;
}

function loadCsv(filename: string): Record<string, string>[] {
  const filePath = join(DATA_DIR, filename);
  const content = readFileSync(filePath, "utf-8");
  return parse(content, {
    columns: true,
    skip_empty_lines: true,
    bom: true,
    trim: true,
    relax_column_count: true,
  }) as Record<string, string>[];
}

function loadBrasileiraoMatches(): Match[] {
  const rows = loadCsv("Brasileirao_Matches.csv");
  return rows.map((r) => ({
    datetime: parseDate(r["datetime"]),
    homeTeam: normalizeTeamName(r["home_team"]),
    awayTeam: normalizeTeamName(r["away_team"]),
    homeGoals: safeInt(r["home_goal"]),
    awayGoals: safeInt(r["away_goal"]),
    season: safeInt(r["season"]),
    round: r["round"],
    homeState: r["home_team_state"],
    awayState: r["away_team_state"],
    competition: "brasileirao" as const,
  }));
}

function loadCupMatches(): Match[] {
  const rows = loadCsv("Brazilian_Cup_Matches.csv");
  return rows.map((r) => ({
    datetime: parseDate(r["datetime"]),
    homeTeam: normalizeTeamName(r["home_team"]),
    awayTeam: normalizeTeamName(r["away_team"]),
    homeGoals: safeInt(r["home_goal"]),
    awayGoals: safeInt(r["away_goal"]),
    season: safeInt(r["season"]),
    round: r["round"],
    competition: "copa_do_brasil" as const,
  }));
}

function loadLibertadoresMatches(): Match[] {
  const rows = loadCsv("Libertadores_Matches.csv");
  return rows.map((r) => ({
    datetime: parseDate(r["datetime"]),
    homeTeam: normalizeTeamName(r["home_team"]),
    awayTeam: normalizeTeamName(r["away_team"]),
    homeGoals: safeInt(r["home_goal"]),
    awayGoals: safeInt(r["away_goal"]),
    season: safeInt(r["season"]),
    stage: r["stage"],
    competition: "libertadores" as const,
  }));
}

function loadExtendedMatches(): Match[] {
  const rows = loadCsv("BR-Football-Dataset.csv");
  return rows.map((r) => ({
    datetime: parseDate(r["date"]),
    homeTeam: normalizeTeamName(r["home"]),
    awayTeam: normalizeTeamName(r["away"]),
    homeGoals: safeInt(r["home_goal"]),
    awayGoals: safeInt(r["away_goal"]),
    season: r["date"] ? new Date(r["date"]).getFullYear() : 0,
    tournament: r["tournament"],
    homeCorners: safeInt(r["home_corner"]),
    awayCorners: safeInt(r["away_corner"]),
    homeAttacks: safeInt(r["home_attack"]),
    awayAttacks: safeInt(r["away_attack"]),
    homeShots: safeInt(r["home_shots"]),
    awayShots: safeInt(r["away_shots"]),
    competition: "extended" as const,
  }));
}

function loadHistoricalMatches(): Match[] {
  const rows = loadCsv("novo_campeonato_brasileiro.csv");
  return rows.map((r) => ({
    datetime: parseDate(r["Data"]),
    homeTeam: normalizeTeamName(r["Equipe_mandante"]),
    awayTeam: normalizeTeamName(r["Equipe_visitante"]),
    homeGoals: safeInt(r["Gols_mandante"]),
    awayGoals: safeInt(r["Gols_visitante"]),
    season: safeInt(r["Ano"]),
    round: r["Rodada"],
    homeState: r["Mandante_UF"],
    awayState: r["Visitante_UF"],
    arena: r["Arena"],
    winner: r["Vencedor"],
    competition: "historical" as const,
  }));
}

function loadPlayers(): Player[] {
  const rows = loadCsv("fifa_data.csv");
  return rows.map((r) => ({
    id: safeInt(r["ID"]),
    name: r["Name"] || "",
    age: safeInt(r["Age"]),
    nationality: r["Nationality"] || "",
    overall: safeInt(r["Overall"]),
    potential: safeInt(r["Potential"]),
    club: r["Club"] || "",
    position: r["Position"] || "",
    jerseyNumber: r["Jersey Number"] ? safeInt(r["Jersey Number"]) : undefined,
    height: r["Height"],
    weight: r["Weight"],
    value: r["Value"],
    wage: r["Wage"],
    preferredFoot: r["Preferred Foot"],
    internationalReputation: r["International Reputation"] ? safeInt(r["International Reputation"]) : undefined,
    weakFoot: r["Weak Foot"] ? safeInt(r["Weak Foot"]) : undefined,
    skillMoves: r["Skill Moves"] ? safeInt(r["Skill Moves"]) : undefined,
    workRate: r["Work Rate"],
    crossing: r["Crossing"] ? safeInt(r["Crossing"]) : undefined,
    finishing: r["Finishing"] ? safeInt(r["Finishing"]) : undefined,
    dribbling: r["Dribbling"] ? safeInt(r["Dribbling"]) : undefined,
    passing: r["ShortPassing"] ? safeInt(r["ShortPassing"]) : undefined,
    shooting: r["ShotPower"] ? safeInt(r["ShotPower"]) : undefined,
    pace: r["Acceleration"] ? safeInt(r["Acceleration"]) : undefined,
    defending: r["StandingTackle"] ? safeInt(r["StandingTackle"]) : undefined,
    physical: r["Strength"] ? safeInt(r["Strength"]) : undefined,
  }));
}

export interface DataStore {
  matches: Match[];
  players: Player[];
}

let store: DataStore | null = null;

export function getDataStore(): DataStore {
  if (store) return store;

  const brasileirao = loadBrasileiraoMatches();
  const cup = loadCupMatches();
  const libertadores = loadLibertadoresMatches();
  const extended = loadExtendedMatches();
  const historical = loadHistoricalMatches();

  store = {
    matches: [...brasileirao, ...cup, ...libertadores, ...extended, ...historical],
    players: loadPlayers(),
  };

  return store;
}
