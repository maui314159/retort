/**
 * Brazilian Soccer MCP Server - Data Loader
 *
 * Loads all 6 CSV datasets, normalizes team names (strips state suffixes,
 * removes parenthetical annotations), unifies date formats, and maps each
 * row to the shared Match/Player types. Exposes a DataLoader class that
 * lazily parses on first access and caches results.
 */

import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { parse } from "csv-parse/sync";
import type { Match, Player, Competition } from "./types.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA_DIR = join(__dirname, "..", "data", "kaggle");

/**
 * Normalize a team name by:
 * 1. Removing state suffix like "-SP", "-RJ" (from Brasileirão data)
 * 2. Removing parenthetical annotations like " (antigo Esporte Clube Barreira)"
 * 3. Removing state suffix like " - MG" (from Copa do Brasil data)
 * 4. Trimming whitespace
 */
export function normalizeTeamName(raw: string): string {
  let name = raw.trim();
  // Remove parenthetical annotations
  name = name.replace(/\s*\(.*?\)\s*/g, "").trim();
  // Remove " - XX" state suffix (Copa do Brasil format)
  name = name.replace(/\s*-\s*[A-Z]{2}\s*$/, "").trim();
  // Remove "-XX" state suffix (Brasileirão format)
  name = name.replace(/-[A-Z]{2}$/, "").trim();
  return name;
}

/** Parse a date string from various formats into ISO YYYY-MM-DD */
export function parseDate(raw: string): string {
  const s = raw.trim();
  // ISO with time: "2012-05-19 18:30:00"
  const isoMatch = s.match(/^(\d{4}-\d{2}-\d{2})/);
  if (isoMatch) return isoMatch[1];
  // Brazilian format: "29/03/2003"
  const brMatch = s.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (brMatch) return `${brMatch[3]}-${brMatch[2]}-${brMatch[1]}`;
  return s;
}
/** Normalize competition names across datasets to a canonical form */
export function normalizeCompetition(raw: string): Competition {
  const s = raw.trim().toLowerCase();
  if (s === "serie a") return "Brasileirão";
  if (s === "serie b") return "Serie B";
  if (s === "serie c") return "Serie C";
  if (s === "copa do brasil") return "Copa do Brasil";
  if (s.includes("libertadores")) return "Copa Libertadores";
  if (s.includes("sudamericana")) return "Copa Sudamericana";
  return raw.trim();
}

function parseIntSafe(v: unknown): number {
  const n = parseInt(String(v ?? ""), 10);
  return Number.isNaN(n) ? 0 : n;
}

function parseFloatSafe(v: unknown): number {
  const n = parseFloat(String(v ?? ""));
  return Number.isNaN(n) ? 0 : n;
}

export class DataLoader {
  private _matches: Match[] | null = null;
  private _players: Player[] | null = null;

  get matches(): Match[] {
    if (!this._matches) this._matches = this.loadAllMatches();
    return this._matches;
  }

  get players(): Player[] {
    if (!this._players) this._players = this.loadPlayers();
    return this._players;
  }

  private loadAllMatches(): Match[] {
    return [
      ...this.loadBrasileirao(),
      ...this.loadCopaDoBrasil(),
      ...this.loadLibertadores(),
      ...this.loadBRFootball(),
      ...this.loadHistoricalBrasileirao(),
    ];
  }

  private readCsv(filename: string): Record<string, string>[] {
    const path = join(DATA_DIR, filename);
    const content = readFileSync(path, "utf-8");
    return parse(content, {
      columns: true,
      skip_empty_lines: true,
      bom: true,
      relax_quotes: true,
      trim: true,
    }) as Record<string, string>[];
  }

  private loadBrasileirao(): Match[] {
    return this.readCsv("Brasileirao_Matches.csv").map((r) => ({
      date: parseDate(r.datetime),
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

  private loadCopaDoBrasil(): Match[] {
    return this.readCsv("Brazilian_Cup_Matches.csv").map((r) => ({
      date: parseDate(r.datetime),
      homeTeam: normalizeTeamName(r.home_team),
      awayTeam: normalizeTeamName(r.away_team),
      homeGoals: parseIntSafe(r.home_goal),
      awayGoals: parseIntSafe(r.away_goal),
      season: parseIntSafe(r.season),
      competition: "Copa do Brasil" as Competition,
      round: r.round,
    }));
  }

  private loadLibertadores(): Match[] {
    return this.readCsv("Libertadores_Matches.csv").map((r) => ({
      date: parseDate(r.datetime),
      homeTeam: normalizeTeamName(r.home_team),
      awayTeam: normalizeTeamName(r.away_team),
      homeGoals: parseIntSafe(r.home_goal),
      awayGoals: parseIntSafe(r.away_goal),
      season: parseIntSafe(r.season),
      competition: "Copa Libertadores" as Competition,
      stage: r.stage,
    }));
  }

  private loadBRFootball(): Match[] {
    return this.readCsv("BR-Football-Dataset.csv").map((r) => ({
      date: parseDate(r.date),
      homeTeam: normalizeTeamName(r.home),
      awayTeam: normalizeTeamName(r.away),
      homeGoals: parseIntSafe(r.home_goal),
      awayGoals: parseIntSafe(r.away_goal),
      season: parseIntSafe(r.date?.slice(0, 4)),
      competition: normalizeCompetition(r.tournament || "Unknown"),
      homeCorners: parseFloatSafe(r.home_corner),
      awayCorners: parseFloatSafe(r.away_corner),
      homeAttacks: parseFloatSafe(r.home_attack),
      awayAttacks: parseFloatSafe(r.away_attack),
      homeShots: parseFloatSafe(r.home_shots),
      awayShots: parseFloatSafe(r.away_shots),
    }));
  }

  private loadHistoricalBrasileirao(): Match[] {
    return this.readCsv("novo_campeonato_brasileiro.csv").map((r) => ({
      date: parseDate(r.Data),
      homeTeam: normalizeTeamName(r.Equipe_mandante),
      awayTeam: normalizeTeamName(r.Equipe_visitante),
      homeGoals: parseIntSafe(r.Gols_mandante),
      awayGoals: parseIntSafe(r.Gols_visitante),
      season: parseIntSafe(r.Ano),
      competition: "Brasileirão" as Competition,
      round: r.Rodada,
      homeState: r.Mandante_UF,
      awayState: r.Visitante_UF,
      stadium: r.Arena,
    }));
  }

  private loadPlayers(): Player[] {
    return this.readCsv("fifa_data.csv").map((r) => ({
      id: parseIntSafe(r.ID),
      name: r.Name,
      age: parseIntSafe(r.Age),
      nationality: r.Nationality,
      overall: parseIntSafe(r.Overall),
      potential: parseIntSafe(r.Potential),
      club: r.Club,
      position: r.Position,
      jerseyNumber: parseIntSafe(r["Jersey Number"]),
      height: r.Height,
      weight: r.Weight,
      preferredFoot: r["Preferred Foot"],
      crossing: parseIntSafe(r.Crossing),
      finishing: parseIntSafe(r.Finishing),
      dribbling: parseIntSafe(r.Dribbling),
      shortPassing: parseIntSafe(r.ShortPassing),
      longPassing: parseIntSafe(r.LongPassing),
      ballControl: parseIntSafe(r.BallControl),
      acceleration: parseIntSafe(r.Acceleration),
      sprintSpeed: parseIntSafe(r.SprintSpeed),
      stamina: parseIntSafe(r.Stamina),
      strength: parseIntSafe(r.Strength),
      shotPower: parseIntSafe(r.ShotPower),
      vision: parseIntSafe(r.Vision),
    }));
  }
}
