/**
 * Brazilian Soccer MCP Server — Data Loader
 *
 * Reads all 6 CSV files into normalized in-memory structures.
 * Team names are normalized on load for consistent querying.
 * Character encoding is handled as UTF-8.
 * Multiple date formats are parsed.
 */

import { parse } from "csv-parse/sync";
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import type {
  NormalizedMatch,
  Player,
  SoccerData,
  Competition,
} from "./types.js";
import { normalizeTeamName } from "./types.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA_DIR = resolve(__dirname, "..", "data", "kaggle");

function readCSV(filename: string): string {
  return readFileSync(resolve(DATA_DIR, filename), "utf-8");
}

/** Parse date strings in multiple formats to YYYY-MM-DD. */
function parseDate(raw: string): string {
  const trimmed = raw.trim();
  // Already ISO: "2012-05-19" or "2012-05-19 18:30:00"
  const isoMatch = trimmed.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (isoMatch) {
    return `${isoMatch[1]}-${isoMatch[2]}-${isoMatch[3]}`;
  }
  // Brazilian format: "29/03/2003"
  const brMatch = trimmed.match(/^(\d{2})\/(\d{2})\/(\d{4})/);
  if (brMatch) {
    return `${brMatch[3]}-${brMatch[2]}-${brMatch[1]}`;
  }
  return trimmed;
}

function loadBrasileirao(): NormalizedMatch[] {
  const csv = readCSV("Brasileirao_Matches.csv");
  const records = parse(csv, { columns: true, skip_empty_lines: true }) as any[];
  return records.map((r: any) => ({
    competition: "Brasileirão" as Competition,
    date: parseDate(r.datetime),
    time: r.datetime?.includes(" ") ? r.datetime.split(" ")[1] : undefined,
    homeTeam: normalizeTeamName(r.home_team),
    awayTeam: normalizeTeamName(r.away_team),
    homeGoal: parseInt(r.home_goal, 10),
    awayGoal: parseInt(r.away_goal, 10),
    season: parseInt(r.season, 10),
    round: `Round ${r.round}`,
    source: "Brasileirao_Matches.csv",
  }));
}

function loadCopaDoBrasil(): NormalizedMatch[] {
  const csv = readCSV("Brazilian_Cup_Matches.csv");
  const records = parse(csv, { columns: true, skip_empty_lines: true }) as any[];
  return records.map((r: any) => ({
    competition: "Copa do Brasil" as Competition,
    date: parseDate(r.datetime),
    time: r.datetime?.includes(" ") ? r.datetime.split(" ")[1] : undefined,
    homeTeam: normalizeTeamName(r.home_team),
    awayTeam: normalizeTeamName(r.away_team),
    homeGoal: parseInt(r.home_goal, 10),
    awayGoal: parseInt(r.away_goal, 10),
    season: parseInt(r.season, 10),
    round: `Round ${r.round}`,
    source: "Brazilian_Cup_Matches.csv",
  }));
}

function loadLibertadores(): NormalizedMatch[] {
  const csv = readCSV("Libertadores_Matches.csv");
  const records = parse(csv, { columns: true, skip_empty_lines: true }) as any[];
  return records.map((r: any) => ({
    competition: "Copa Libertadores" as Competition,
    date: parseDate(r.datetime),
    time: r.datetime?.includes(" ") ? r.datetime.split(" ")[1] : undefined,
    homeTeam: normalizeTeamName(r.home_team),
    awayTeam: normalizeTeamName(r.away_team),
    homeGoal: parseInt(r.home_goal, 10),
    awayGoal: parseInt(r.away_goal, 10),
    season: parseInt(r.season, 10),
    round: r.stage,
    source: "Libertadores_Matches.csv",
  }));
}

function loadBRFootball(): NormalizedMatch[] {
  const csv = readCSV("BR-Football-Dataset.csv");
  const records = parse(csv, { columns: true, skip_empty_lines: true }) as any[];
  // BR-Football dataset overlaps with Brasileirao/Copa do Brasil —
  // de-duplicate later by date+home+away if needed, but for now keep all.
  return records.map((r: any) => {
    const competition = r.tournament?.trim() || "";
    // Map tournament names
    let comp: Competition;
    const lower = competition.toLowerCase();
    if (lower.includes("brasileir") || lower.includes("série") || lower.includes("serie")) {
      comp = "Brasileirão";
    } else if (lower.includes("copa do brasil")) {
      comp = "Copa do Brasil";
    } else if (lower.includes("libertadores")) {
      comp = "Copa Libertadores";
    } else {
      comp = "Brasileirão"; // default
    }

    return {
      competition: comp,
      date: r.date || "",
      time: r.time || undefined,
      homeTeam: normalizeTeamName(r.home),
      awayTeam: normalizeTeamName(r.away),
      homeGoal: parseFloat(r.home_goal) || 0,
      awayGoal: parseFloat(r.away_goal) || 0,
      season: r.date ? parseInt(r.date.split("-")[0], 10) : 0,
      round: undefined,
      source: "BR-Football-Dataset.csv",
    };
  });
}

function loadHistorico(): NormalizedMatch[] {
  const csv = readCSV("novo_campeonato_brasileiro.csv");
  const records = parse(csv, {
    columns: true,
    skip_empty_lines: true,
    bom: true,
  }) as any[];
  return records.map((r: any) => ({
    competition: "Brasileirão (Histórico)" as Competition,
    date: parseDate(r.Data),
    homeTeam: normalizeTeamName(r.Equipe_mandante),
    awayTeam: normalizeTeamName(r.Equipe_visitante),
    homeGoal: parseInt(r.Gols_mandante, 10),
    awayGoal: parseInt(r.Gols_visitante, 10),
    season: parseInt(r.Ano, 10),
    round: `Round ${r.Rodada}`,
    source: "novo_campeonato_brasileiro.csv",
  }));
}

function loadFIFAPlayers(): Player[] {
  const csv = readCSV("fifa_data.csv");
  const records = parse(csv, {
    columns: true,
    skip_empty_lines: true,
    bom: true,
  }) as any[];
  return records.map((r: any) => ({
    id: parseInt(r.ID, 10),
    name: String(r.Name || "").trim(),
    age: parseInt(r.Age, 10) || 0,
    nationality: String(r.Nationality || "").trim(),
    overall: parseInt(r.Overall, 10) || 0,
    potential: parseInt(r.Potential, 10) || 0,
    club: String(r.Club || "").trim(),
    position: String(r.Position || "").trim(),
    jerseyNumber: r["Jersey Number"] ? parseInt(r["Jersey Number"], 10) : null,
    height: String(r.Height || "").trim(),
    weight: String(r.Weight || "").trim(),
    preferredFoot: String(r["Preferred Foot"] || "").trim(),
    skillMoves: parseInt(r["Skill Moves"], 10) || 0,
    weakFoot: parseInt(r["Weak Foot"], 10) || 0,
    workRate: String(r["Work Rate"] || "").trim(),
  }));
}

let cachedData: SoccerData | null = null;

/** Load all data from CSV files. Results are cached in memory. */
export function loadAllData(): SoccerData {
  if (cachedData) return cachedData;

  cachedData = {
    matches: [
      ...loadBrasileirao(),
      ...loadCopaDoBrasil(),
      ...loadLibertadores(),
      ...loadBRFootball(),
      ...loadHistorico(),
    ],
    players: loadFIFAPlayers(),
  };

  return cachedData;
}