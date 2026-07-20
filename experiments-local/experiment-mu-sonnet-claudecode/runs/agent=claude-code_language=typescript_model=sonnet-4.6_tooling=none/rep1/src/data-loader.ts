import { parse } from "csv-parse/sync";
import { readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import type {
  BrasileiraoMatch,
  CupMatch,
  LibertadoresMatch,
  ExtendedMatch,
  HistoricalMatch,
  FifaPlayer,
  NormalizedMatch,
} from "./types.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA_DIR = join(__dirname, "..", "data", "kaggle");

function loadCsv(filename: string): Record<string, string>[] {
  const content = readFileSync(join(DATA_DIR, filename), "utf-8");
  // Remove BOM only (keep leading comma so column names stay aligned)
  const cleaned = content.replace(/^﻿/, "");
  return parse(cleaned, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    relax_quotes: true,
    relax_column_count: true,
  }) as Record<string, string>[];
}

function toInt(v: string | undefined): number {
  const n = parseInt(v ?? "0", 10);
  return isNaN(n) ? 0 : n;
}

function toFloat(v: string | undefined): number {
  const n = parseFloat(v ?? "0");
  return isNaN(n) ? 0 : n;
}

export function loadBrasileiraoMatches(): BrasileiraoMatch[] {
  return loadCsv("Brasileirao_Matches.csv").map((r) => ({
    datetime: r["datetime"] ?? "",
    home_team: r["home_team"] ?? "",
    home_team_state: r["home_team_state"] ?? "",
    away_team: r["away_team"] ?? "",
    away_team_state: r["away_team_state"] ?? "",
    home_goal: toInt(r["home_goal"]),
    away_goal: toInt(r["away_goal"]),
    season: toInt(r["season"]),
    round: toInt(r["round"]),
  }));
}

export function loadCupMatches(): CupMatch[] {
  return loadCsv("Brazilian_Cup_Matches.csv").map((r) => ({
    round: r["round"] ?? "",
    datetime: r["datetime"] ?? "",
    home_team: r["home_team"] ?? "",
    away_team: r["away_team"] ?? "",
    home_goal: toInt(r["home_goal"]),
    away_goal: toInt(r["away_goal"]),
    season: toInt(r["season"]),
  }));
}

export function loadLibertadoresMatches(): LibertadoresMatch[] {
  return loadCsv("Libertadores_Matches.csv").map((r) => ({
    datetime: r["datetime"] ?? "",
    home_team: r["home_team"] ?? "",
    away_team: r["away_team"] ?? "",
    home_goal: toInt(r["home_goal"]),
    away_goal: toInt(r["away_goal"]),
    season: toInt(r["season"]),
    stage: r["stage"] ?? "",
  }));
}

export function loadExtendedMatches(): ExtendedMatch[] {
  return loadCsv("BR-Football-Dataset.csv").map((r) => ({
    tournament: r["tournament"] ?? "",
    home: r["home"] ?? "",
    away: r["away"] ?? "",
    home_goal: toFloat(r["home_goal"]),
    away_goal: toFloat(r["away_goal"]),
    home_corner: toFloat(r["home_corner"]),
    away_corner: toFloat(r["away_corner"]),
    home_attack: toFloat(r["home_attack"]),
    away_attack: toFloat(r["away_attack"]),
    home_shots: toFloat(r["home_shots"]),
    away_shots: toFloat(r["away_shots"]),
    time: r["time"] ?? "",
    date: r["date"] ?? "",
    ht_result: r["ht_result"] ?? "",
    at_result: r["at_result"] ?? "",
    total_corners: toFloat(r["total_corners"]),
  }));
}

export function loadHistoricalMatches(): HistoricalMatch[] {
  return loadCsv("novo_campeonato_brasileiro.csv").map((r) => ({
    ID: r["ID"] ?? "",
    Data: r["Data"] ?? "",
    Ano: toInt(r["Ano"]),
    Rodada: toInt(r["Rodada"]),
    Equipe_mandante: r["Equipe_mandante"] ?? "",
    Equipe_visitante: r["Equipe_visitante"] ?? "",
    Gols_mandante: toInt(r["Gols_mandante"]),
    Gols_visitante: toInt(r["Gols_visitante"]),
    Mandante_UF: r["Mandante_UF"] ?? "",
    Visitante_UF: r["Visitante_UF"] ?? "",
    Vencedor: r["Vencedor"] ?? "",
    Arena: r["Arena"] ?? "",
  }));
}

export function loadFifaPlayers(): FifaPlayer[] {
  return loadCsv("fifa_data.csv").map((r) => ({
    ID: toInt(r["ID"]),
    Name: r["Name"] ?? "",
    Age: toInt(r["Age"]),
    Nationality: r["Nationality"] ?? "",
    Overall: toInt(r["Overall"]),
    Potential: toInt(r["Potential"]),
    Club: r["Club"] ?? "",
    Position: r["Position"] ?? "",
    JerseyNumber: r["Jersey Number"] ?? "",
    Height: r["Height"] ?? "",
    Weight: r["Weight"] ?? "",
    Crossing: toInt(r["Crossing"]),
    Finishing: toInt(r["Finishing"]),
    Dribbling: toInt(r["Dribbling"]),
    Value: r["Value"] ?? "",
    Wage: r["Wage"] ?? "",
  }));
}

// Normalize team name: strip state suffix, lowercase, trim
export function normalizeTeam(name: string): string {
  return name
    .replace(/-[A-Z]{2}$/, "")  // strip "-SP", "-RJ" etc.
    .replace(/\s*\([^)]*\)\s*/g, "") // strip parenthetical notes
    .toLowerCase()
    .trim()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, ""); // strip diacritics
}

export function teamMatches(name: string, candidate: string): boolean {
  const n = normalizeTeam(name);
  const c = normalizeTeam(candidate);
  return c.includes(n) || n.includes(c);
}

// Convert all match sources into a unified NormalizedMatch list
export function buildNormalizedMatches(
  brasileirao: BrasileiraoMatch[],
  cup: CupMatch[],
  libertadores: LibertadoresMatch[],
  historical: HistoricalMatch[]
): NormalizedMatch[] {
  const results: NormalizedMatch[] = [];

  for (const m of brasileirao) {
    results.push({
      date: m.datetime.split(" ")[0],
      home_team: m.home_team,
      away_team: m.away_team,
      home_goal: m.home_goal,
      away_goal: m.away_goal,
      season: m.season,
      competition: "Brasileirão Série A",
      round: m.round,
    });
  }

  for (const m of cup) {
    results.push({
      date: m.datetime.split(" ")[0],
      home_team: m.home_team,
      away_team: m.away_team,
      home_goal: m.home_goal,
      away_goal: m.away_goal,
      season: m.season,
      competition: "Copa do Brasil",
      round: m.round,
    });
  }

  for (const m of libertadores) {
    results.push({
      date: m.datetime.split(" ")[0],
      home_team: m.home_team,
      away_team: m.away_team,
      home_goal: m.home_goal,
      away_goal: m.away_goal,
      season: m.season,
      competition: "Copa Libertadores",
      stage: m.stage,
    });
  }

  // Convert DD/MM/YYYY to YYYY-MM-DD
  function brDateToIso(d: string): string {
    const parts = d.split("/");
    if (parts.length === 3) return `${parts[2]}-${parts[1]}-${parts[0]}`;
    return d;
  }

  for (const m of historical) {
    results.push({
      date: brDateToIso(m.Data),
      home_team: m.Equipe_mandante,
      away_team: m.Equipe_visitante,
      home_goal: m.Gols_mandante,
      away_goal: m.Gols_visitante,
      season: m.Ano,
      competition: "Brasileirão Série A (historical)",
      round: m.Rodada,
      extra: { arena: m.Arena, winner: m.Vencedor },
    });
  }

  return results;
}
