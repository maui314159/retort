/**
 * Brazilian Soccer MCP Server - CSV Data Loader
 *
 * Loads and caches all CSV dataset files from data/kaggle/.
 * Handles character encoding (UTF-8), multiple date formats,
 * and team name variations across datasets.
 */

import { parse } from "csv-parse/sync";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

// --- Types ---

export interface BrasileiraoMatch {
  datetime: string;
  home_team: string;
  home_team_state: string;
  away_team: string;
  away_team_state: string;
  home_goal: number;
  away_goal: number;
  season: number;
  round: number;
  competition: "Brasileirão";
}

export interface BrazilianCupMatch {
  round: string;
  datetime: string;
  home_team: string;
  away_team: string;
  home_goal: number;
  away_goal: number;
  season: number;
  competition: "Copa do Brasil";
}

export interface LibertadoresMatch {
  datetime: string;
  home_team: string;
  away_team: string;
  home_goal: number;
  away_goal: number;
  season: number;
  stage: string;
  competition: "Libertadores";
}

export interface BRFootballMatch {
  tournament: string;
  home: string;
  away: string;
  home_goal: number;
  away_goal: number;
  home_corner: number;
  away_corner: number;
  home_attack: number;
  away_attack: number;
  home_shots: number;
  away_shots: number;
  time: string;
  date: string;
  ht_result: string;
  at_result: string;
  total_corners: number;
  competition: string;
}

export interface NovoBrasileiraoMatch {
  id: string;
  data: string;
  ano: number;
  rodada: number;
  equipe_mandante: string;
  equipe_visitante: string;
  gols_mandante: number;
  gols_visitante: number;
  mandante_uf: string;
  visitante_uf: string;
  vencedor: string;
  arena: string;
  competition: "Brasileirão (Histórico)";
}

export interface FIFAPlayer {
  id: number;
  name: string;
  age: number;
  nationality: string;
  overall: number;
  potential: number;
  club: string;
  position: string;
  jersey_number: number;
  height: string;
  weight: string;
  preferred_foot: string;
  weak_foot: number;
  skill_moves: number;
  work_rate: string;
  value: string;
  wage: string;
  crossing: number;
  finishing: number;
  heading_accuracy: number;
  short_passing: number;
  volleys: number;
  dribbling: number;
  curve: number;
  fk_accuracy: number;
  long_passing: number;
  ball_control: number;
  acceleration: number;
  sprint_speed: number;
  agility: number;
  reactions: number;
  balance: number;
  shot_power: number;
  jumping: number;
  stamina: number;
  strength: number;
  long_shots: number;
  aggression: number;
  interceptions: number;
  positioning: number;
  vision: number;
  penalties: number;
  composure: number;
  marking: number;
  standing_tackle: number;
  sliding_tackle: number;
}

// Unified match type for cross-competition queries
export interface UnifiedMatch {
  date: string;
  home_team: string;
  away_team: string;
  home_goal: number;
  away_goal: number;
  season: number;
  competition: string;
  round?: string | number;
  stage?: string;
  home_team_state?: string;
  away_team_state?: string;
}

// --- Data directory ---

const DATA_DIR = resolve("data/kaggle");

// --- CSV Parsing ---

function loadCSV<T>(filename: string, mapRow: (row: Record<string, string>) => T): T[] {
  const content = readFileSync(resolve(DATA_DIR, filename), "utf-8");
  const records = parse(content, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    bom: true,
    relax_column_count: true,
  }) as Record<string, string>[];
  return records.map(mapRow);
}

function parseFloatSafe(v: string | undefined): number {
  if (!v) return 0;
  const n = parseFloat(v);
  return isNaN(n) ? 0 : n;
}

function parseIntSafe(v: string | undefined): number {
  if (!v) return 0;
  const n = parseInt(v, 10);
  return isNaN(n) ? 0 : n;
}

// --- Dataset Loaders ---

export function loadBrasileiraoMatches(): BrasileiraoMatch[] {
  return loadCSV<BrasileiraoMatch>("Brasileirao_Matches.csv", (row) => ({
    datetime: row.datetime,
    home_team: row.home_team,
    home_team_state: row.home_team_state,
    away_team: row.away_team,
    away_team_state: row.away_team_state,
    home_goal: parseIntSafe(row.home_goal),
    away_goal: parseIntSafe(row.away_goal),
    season: parseIntSafe(row.season),
    round: parseIntSafe(row.round),
    competition: "Brasileirão",
  }));
}

export function loadBrazilianCupMatches(): BrazilianCupMatch[] {
  return loadCSV<BrazilianCupMatch>("Brazilian_Cup_Matches.csv", (row) => ({
    round: row.round,
    datetime: row.datetime,
    home_team: row.home_team,
    away_team: row.away_team,
    home_goal: parseIntSafe(row.home_goal),
    away_goal: parseIntSafe(row.away_goal),
    season: parseIntSafe(row.season),
    competition: "Copa do Brasil",
  }));
}

export function loadLibertadoresMatches(): LibertadoresMatch[] {
  return loadCSV<LibertadoresMatch>("Libertadores_Matches.csv", (row) => ({
    datetime: row.datetime,
    home_team: row.home_team,
    away_team: row.away_team,
    home_goal: parseIntSafe(row.home_goal),
    away_goal: parseIntSafe(row.away_goal),
    season: parseIntSafe(row.season),
    stage: row.stage || "",
    competition: "Libertadores",
  }));
}

export function loadBRFootballMatches(): BRFootballMatch[] {
  return loadCSV<BRFootballMatch>("BR-Football-Dataset.csv", (row) => ({
    tournament: row.tournament,
    home: row.home,
    away: row.away,
    home_goal: parseFloatSafe(row.home_goal),
    away_goal: parseFloatSafe(row.away_goal),
    home_corner: parseFloatSafe(row.home_corner),
    away_corner: parseFloatSafe(row.away_corner),
    home_attack: parseFloatSafe(row.home_attack),
    away_attack: parseFloatSafe(row.away_attack),
    home_shots: parseFloatSafe(row.home_shots),
    away_shots: parseFloatSafe(row.away_shots),
    time: row.time,
    date: row.date,
    ht_result: row.ht_result,
    at_result: row.at_result,
    total_corners: parseFloatSafe(row.total_corners),
    competition: row.tournament,
  }));
}

export function loadNovoBrasileiraoMatches(): NovoBrasileiraoMatch[] {
  return loadCSV<NovoBrasileiraoMatch>("novo_campeonato_brasileiro.csv", (row) => ({
    id: row.ID,
    data: row.Data,
    ano: parseIntSafe(row.Ano),
    rodada: parseIntSafe(row.Rodada),
    equipe_mandante: row.Equipe_mandante,
    equipe_visitante: row.Equipe_visitante,
    gols_mandante: parseIntSafe(row.Gols_mandante),
    gols_visitante: parseIntSafe(row.Gols_visitante),
    mandante_uf: row.Mandante_UF,
    visitante_uf: row.Visitante_UF,
    vencedor: row.Vencedor,
    arena: row.Arena,
    competition: "Brasileirão (Histórico)",
  }));
}

export function loadFIFAPlayers(): FIFAPlayer[] {
  return loadCSV<FIFAPlayer>("fifa_data.csv", (row) => ({
    id: parseIntSafe(row.ID),
    name: row.Name,
    age: parseIntSafe(row.Age),
    nationality: row.Nationality,
    overall: parseIntSafe(row.Overall),
    potential: parseIntSafe(row.Potential),
    club: row.Club,
    position: row.Position,
    jersey_number: parseIntSafe(row["Jersey Number"]),
    height: row.Height,
    weight: row.Weight,
    preferred_foot: row["Preferred Foot"],
    weak_foot: parseIntSafe(row["Weak Foot"]),
    skill_moves: parseIntSafe(row["Skill Moves"]),
    work_rate: row["Work Rate"],
    value: row.Value,
    wage: row.Wage,
    crossing: parseIntSafe(row.Crossing),
    finishing: parseIntSafe(row.Finishing),
    heading_accuracy: parseIntSafe(row.HeadingAccuracy),
    short_passing: parseIntSafe(row.ShortPassing),
    volleys: parseIntSafe(row.Volleys),
    dribbling: parseIntSafe(row.Dribbling),
    curve: parseIntSafe(row.Curve),
    fk_accuracy: parseIntSafe(row.FKAccuracy),
    long_passing: parseIntSafe(row.LongPassing),
    ball_control: parseIntSafe(row.BallControl),
    acceleration: parseIntSafe(row.Acceleration),
    sprint_speed: parseIntSafe(row.SprintSpeed),
    agility: parseIntSafe(row.Agility),
    reactions: parseIntSafe(row.Reactions),
    balance: parseIntSafe(row.Balance),
    shot_power: parseIntSafe(row.ShotPower),
    jumping: parseIntSafe(row.Jumping),
    stamina: parseIntSafe(row.Stamina),
    strength: parseIntSafe(row.Strength),
    long_shots: parseIntSafe(row.LongShots),
    aggression: parseIntSafe(row.Aggression),
    interceptions: parseIntSafe(row.Interceptions),
    positioning: parseIntSafe(row.Positioning),
    vision: parseIntSafe(row.Vision),
    penalties: parseIntSafe(row.Penalties),
    composure: parseIntSafe(row.Composure),
    marking: parseIntSafe(row.Marking),
    standing_tackle: parseIntSafe(row.StandingTackle),
    sliding_tackle: parseIntSafe(row.SlidingTackle),
  }));
}