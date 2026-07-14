import { parse } from "csv-parse/sync";
import * as fs from "fs";
import * as path from "path";
import {
  BrasileiraoMatch,
  BrazilianCupMatch,
  LibertadoresMatch,
  BRFootballMatch,
  NovoCampeonatoMatch,
  FifaPlayer,
} from "./types.js";
import { parseNumber } from "./utils.js";

const DATA_DIR = path.join(process.cwd(), "data", "kaggle");

export interface LoadedData {
  brasileiraoMatches: BrasileiraoMatch[];
  cupMatches: BrazilianCupMatch[];
  libertadoresMatches: LibertadoresMatch[];
  brFootballMatches: BRFootballMatch[];
  novoCampeonatoMatches: NovoCampeonatoMatch[];
  fifaPlayers: FifaPlayer[];
}

let cachedData: LoadedData | null = null;

function readCsv<T>(filePath: string): T[] {
  if (!fs.existsSync(filePath)) {
    throw new Error(`File not found: ${filePath}`);
  }
  const content = fs.readFileSync(filePath, "utf-8");
  return parse(content, {
    columns: true,
    skip_empty_lines: true,
    cast: (value, context) => {
      if (context.column !== undefined && context.header) {
        // Attempt to parse numbers for known numeric columns
        const num = parseNumber(value);
        if (num !== null) return num;
      }
      return value;
    },
  }) as T[];
}

export function loadData(): LoadedData {
  if (cachedData) return cachedData;

  const brasileiraoPath = path.join(DATA_DIR, "Brasileirao_Matches.csv");
  const cupPath = path.join(DATA_DIR, "Brazilian_Cup_Matches.csv");
  const libertadoresPath = path.join(DATA_DIR, "Libertadores_Matches.csv");
  const brFootballPath = path.join(DATA_DIR, "BR-Football-Dataset.csv");
  const novoCampeonatoPath = path.join(DATA_DIR, "novo_campeonato_brasileiro.csv");
  const fifaPath = path.join(DATA_DIR, "fifa_data.csv");

  const brasileiraoRaw = readCsv<Record<string, string | number>>(brasileiraoPath);
  const brasileiraoMatches: BrasileiraoMatch[] = brasileiraoRaw.map((row) => ({
    datetime: String(row.datetime || ""),
    home_team: String(row.home_team || ""),
    home_team_state: String(row.home_team_state || ""),
    away_team: String(row.away_team || ""),
    away_team_state: String(row.away_team_state || ""),
    home_goal: Number(row.home_goal || 0),
    away_goal: Number(row.away_goal || 0),
    season: Number(row.season || 0),
    round: Number(row.round || 0),
    competition: "Brasileirão",
  }));

  const cupRaw = readCsv<Record<string, string | number>>(cupPath);
  const cupMatches: BrazilianCupMatch[] = cupRaw.map((row) => ({
    round: String(row.round || ""),
    datetime: String(row.datetime || ""),
    home_team: String(row.home_team || ""),
    away_team: String(row.away_team || ""),
    home_goal: Number(row.home_goal || 0),
    away_goal: Number(row.away_goal || 0),
    season: Number(row.season || 0),
    competition: "Copa do Brasil",
  }));

  const libertadoresRaw = readCsv<Record<string, string | number>>(libertadoresPath);
  const libertadoresMatches: LibertadoresMatch[] = libertadoresRaw.map((row) => ({
    datetime: String(row.datetime || ""),
    home_team: String(row.home_team || ""),
    away_team: String(row.away_team || ""),
    home_goal: Number(row.home_goal || 0),
    away_goal: Number(row.away_goal || 0),
    season: Number(row.season || 0),
    stage: String(row.stage || ""),
    competition: "Libertadores",
  }));

  const brFootballRaw = readCsv<Record<string, string | number>>(brFootballPath);
  const brFootballMatches: BRFootballMatch[] = brFootballRaw.map((row) => ({
    tournament: String(row.tournament || ""),
    home: String(row.home || ""),
    home_goal: Number(row.home_goal || 0),
    away_goal: Number(row.away_goal || 0),
    away: String(row.away || ""),
    home_corner: parseNumber(row.home_corner),
    away_corner: parseNumber(row.away_corner),
    home_attack: parseNumber(row.home_attack),
    away_attack: parseNumber(row.away_attack),
    home_shots: parseNumber(row.home_shots),
    away_shots: parseNumber(row.away_shots),
    time: String(row.time || ""),
    date: String(row.date || ""),
    ht_result: String(row.ht_result || ""),
    at_result: String(row.at_result || ""),
    total_corners: parseNumber(row.total_corners),
    competition: String(row.tournament || "Unknown"),
  }));

  const novoCampeonatoRaw = readCsv<Record<string, string | number>>(novoCampeonatoPath);
  const novoCampeonatoMatches: NovoCampeonatoMatch[] = novoCampeonatoRaw.map((row) => ({
    ID: String(row.ID || ""),
    Data: String(row.Data || ""),
    Ano: Number(row.Ano || 0),
    Rodada: Number(row.Rodada || 0),
    Equipe_mandante: String(row.Equipe_mandante || ""),
    Equipe_visitante: String(row.Equipe_visitante || ""),
    Gols_mandante: Number(row.Gols_mandante || 0),
    Gols_visitante: Number(row.Gols_visitante || 0),
    Mandante_UF: String(row.Mandante_UF || ""),
    Visitante_UF: String(row.Visitante_UF || ""),
    Vencedor: String(row.Vencedor || ""),
    Arena: String(row.Arena || ""),
    OBS: String(row.OBS || ""),
    competition: "Brasileirão Histórico",
  }));

  const fifaRaw = readCsv<Record<string, string | number>>(fifaPath);
  const fifaPlayers: FifaPlayer[] = fifaRaw.map((row) => ({
    ID: Number(row.ID || 0),
    Name: String(row.Name || ""),
    Age: Number(row.Age || 0),
    Nationality: String(row.Nationality || ""),
    Overall: Number(row.Overall || 0),
    Potential: Number(row.Potential || 0),
    Club: String(row.Club || ""),
    Position: String(row.Position || ""),
    Jersey_Number: row["Jersey Number"] ? String(row["Jersey Number"]) : null,
    Height: row.Height ? String(row.Height) : null,
    Weight: row.Weight ? String(row.Weight) : null,
  }));

  cachedData = {
    brasileiraoMatches,
    cupMatches,
    libertadoresMatches,
    brFootballMatches,
    novoCampeonatoMatches,
    fifaPlayers,
  };

  return cachedData;
}
