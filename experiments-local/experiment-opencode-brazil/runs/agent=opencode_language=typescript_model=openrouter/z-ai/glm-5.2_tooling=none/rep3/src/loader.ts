/**
 * Brazilian Soccer MCP Server - Data Loader
 * -----------------------------------------
 * Context: This module reads the six Kaggle CSV datasets from disk and
 * normalizes them into the canonical `Match` / `Player` domain types defined
 * in `types.ts`. It is the single ingress point for raw data into the server.
 *
 * The loader is lazy: datasets are parsed once on first access and cached
 * for the lifetime of the process. All public functions are synchronous
 * after the initial parse so the query layer can stay side-effect free.
 *
 * Files loaded:
 *   data/kaggle/Brasileirao_Matches.csv         -> brasileirao
 *   data/kaggle/Brazilian_Cup_Matches.csv        -> copa-do-brasil
 *   data/kaggle/Libertadores_Matches.csv         -> libertadores
 *   data/kaggle/BR-Football-Dataset.csv          -> ext-stats
 *   data/kaggle/novo_campeonato_brasileiro.csv   -> brasileirao-historico
 *   data/kaggle/fifa_data.csv                    -> players
 */

import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parse } from "csv-parse/sync";
import type {
  Competition,
  Match,
  Player,
} from "./types.js";
import {
  displayTeamName,
  normalizeTeamName,
  parseDate,
  parseNumber,
} from "./normalize.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

/** Root of the project (two levels up from dist/ or src/). */
const PROJECT_ROOT = resolve(__dirname, "..");

/** Default data directory; overridable via BRAZILIAN_SOCCER_DATA env var. */
const DATA_DIR = process.env.BRAZILIAN_SOCCER_DATA
  ? resolve(process.env.BRAZILIAN_SOCCER_DATA)
  : join(PROJECT_ROOT, "data", "kaggle");

/** Result of loading all datasets. */
export interface SoccerData {
  matches: Match[];
  players: Player[];
  /** All normalized team keys that appear in any match dataset. */
  teams: string[];
  /** Map from normalized team key -> canonical display name. */
  teamDisplay: Map<string, string>;
  /** All seasons present in match data, sorted ascending. */
  seasons: number[];
  /** All distinct competitions present. */
  competitions: Competition[];
}

let cached: SoccerData | null = null;

/** Return the loaded datasets, loading from disk on first call. */
export function loadData(): SoccerData {
  if (cached) return cached;
  cached = loadAll();
  return cached;
}

/** Force a reload (used in tests with alternate data dirs). */
export function reload(dataDir?: string): SoccerData {
  cached = null;
  if (dataDir) {
    process.env.BRAZILIAN_SOCCER_DATA = dataDir;
  }
  return loadData();
}

function loadAll(): SoccerData {
  const matches: Match[] = [];
  matches.push(...loadBrasileirao());
  matches.push(...loadCup());
  matches.push(...loadLibertadores());
  matches.push(...loadExtStats());
  matches.push(...loadHistorical());

  const players = loadPlayers();

  // Build team index.
  const teamDisplay = new Map<string, string>();
  const teamSet = new Set<string>();
  for (const m of matches) {
    teamSet.add(m.homeTeam);
    teamSet.add(m.awayTeam);
    if (!teamDisplay.has(m.homeTeam)) teamDisplay.set(m.homeTeam, m.homeTeamRaw);
    if (!teamDisplay.has(m.awayTeam)) teamDisplay.set(m.awayTeam, m.awayTeamRaw);
  }
  // Prefer display names with accents preserved.
  for (const m of matches) {
    const hd = displayTeamName(m.homeTeamRaw);
    const ad = displayTeamName(m.awayTeamRaw);
    if (hd) teamDisplay.set(m.homeTeam, hd);
    if (ad) teamDisplay.set(m.awayTeam, ad);
  }

  const seasons = Array.from(
    new Set(matches.map((m) => m.season).filter((s) => Number.isFinite(s))),
  ).sort((a, b) => a - b);
  const competitions = Array.from(
    new Set(matches.map((m) => m.competition)),
  );

  return {
    matches,
    players,
    teams: Array.from(teamSet).sort(),
    teamDisplay,
    seasons,
    competitions,
  };
}

function readCsv(file: string): Record<string, string>[] {
  const path = join(DATA_DIR, file);
  const content = readFileSync(path, "utf-8");
  return parse(content, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    relax_column_count: true,
    bom: true,
  });
}

function winner(home: number, away: number): "home" | "away" | "draw" {
  if (home > away) return "home";
  if (away > home) return "away";
  return "draw";
}

function loadBrasileirao(): Match[] {
  const rows = readCsv("Brasileirao_Matches.csv");
  return rows.map((r) => {
    const homeGoal = parseNumber(r.home_goal) ?? 0;
    const awayGoal = parseNumber(r.away_goal) ?? 0;
    const season = parseNumber(r.season) ?? 0;
    return {
      date: parseDate(r.datetime) ?? "",
      homeTeamRaw: r.home_team,
      awayTeamRaw: r.away_team,
      homeTeam: normalizeTeamName(r.home_team),
      awayTeam: normalizeTeamName(r.away_team),
      homeState: r.home_team_state || null,
      awayState: r.away_team_state || null,
      homeGoal,
      awayGoal,
      season,
      competition: "brasileirao",
      competitionLabel: "Brasileirão Série A",
      round: r.round ? String(r.round) : null,
      stadium: null,
      winner: winner(homeGoal, awayGoal),
    };
  });
}

function loadCup(): Match[] {
  const rows = readCsv("Brazilian_Cup_Matches.csv");
  return rows.map((r) => {
    const homeGoal = parseNumber(r.home_goal) ?? 0;
    const awayGoal = parseNumber(r.away_goal) ?? 0;
    const season = parseNumber(r.season) ?? 0;
    return {
      date: parseDate(r.datetime) ?? "",
      homeTeamRaw: r.home_team,
      awayTeamRaw: r.away_team,
      homeTeam: normalizeTeamName(r.home_team),
      awayTeam: normalizeTeamName(r.away_team),
      homeState: null,
      awayState: null,
      homeGoal,
      awayGoal,
      season,
      competition: "copa-do-brasil",
      competitionLabel: "Copa do Brasil",
      round: r.round ? String(r.round) : null,
      stadium: null,
      winner: winner(homeGoal, awayGoal),
    };
  });
}

function loadLibertadores(): Match[] {
  const rows = readCsv("Libertadores_Matches.csv");
  return rows.map((r) => {
    const homeGoal = parseNumber(r.home_goal) ?? 0;
    const awayGoal = parseNumber(r.away_goal) ?? 0;
    const season = parseNumber(r.season) ?? 0;
    return {
      date: parseDate(r.datetime) ?? "",
      homeTeamRaw: r.home_team,
      awayTeamRaw: r.away_team,
      homeTeam: normalizeTeamName(r.home_team),
      awayTeam: normalizeTeamName(r.away_team),
      homeState: null,
      awayState: null,
      homeGoal,
      awayGoal,
      season,
      competition: "libertadores",
      competitionLabel: "Copa Libertadores",
      round: r.stage || null,
      stadium: null,
      winner: winner(homeGoal, awayGoal),
    };
  });
}

function loadExtStats(): Match[] {
  const rows = readCsv("BR-Football-Dataset.csv");
  return rows.map((r) => {
    const homeGoal = parseNumber(r.home_goal) ?? 0;
    const awayGoal = parseNumber(r.away_goal) ?? 0;
    // Date in this file is ISO YYYY-MM-DD already, sometimes with time elsewhere.
    const season = parseDate(r.date)?.slice(0, 4);
    return {
      date: parseDate(r.date) ?? "",
      homeTeamRaw: r.home,
      awayTeamRaw: r.away,
      homeTeam: normalizeTeamName(r.home),
      awayTeam: normalizeTeamName(r.away),
      homeState: null,
      awayState: null,
      homeGoal,
      awayGoal,
      season: season ? Number(season) : 0,
      competition: "ext-stats",
      competitionLabel: r.tournament || "Extended Stats",
      round: null,
      stadium: null,
      winner: winner(homeGoal, awayGoal),
      stats: {
        homeCorners: parseNumber(r.home_corner) ?? 0,
        awayCorners: parseNumber(r.away_corner) ?? 0,
        homeAttacks: parseNumber(r.home_attack) ?? 0,
        awayAttacks: parseNumber(r.away_attack) ?? 0,
        homeShots: parseNumber(r.home_shots) ?? 0,
        awayShots: parseNumber(r.away_shots) ?? 0,
        totalCorners: parseNumber(r.total_corners) ?? 0,
        htResult: r.ht_result || null,
        atResult: r.at_result || null,
        tournament: r.tournament || "",
      },
    };
  });
}

function loadHistorical(): Match[] {
  const rows = readCsv("novo_campeonato_brasileiro.csv");
  return rows.map((r) => {
    const homeGoal = parseNumber(r.Gols_mandante) ?? 0;
    const awayGoal = parseNumber(r.Gols_visitante) ?? 0;
    const season = parseNumber(r.Ano) ?? 0;
    const vencedor = (r.Vencedor || "").trim().toLowerCase();
    let w: "home" | "away" | "draw" = "draw";
    if (vencedor === "mandante" || vencedor === "home") w = "home";
    else if (vencedor === "visitante" || vencedor === "away") w = "away";
    else w = winner(homeGoal, awayGoal);
    return {
      date: parseDate(r.Data) ?? "",
      homeTeamRaw: r.Equipe_mandante,
      awayTeamRaw: r.Equipe_visitante,
      homeTeam: normalizeTeamName(r.Equipe_mandante),
      awayTeam: normalizeTeamName(r.Equipe_visitante),
      homeState: r.Mandante_UF || null,
      awayState: r.Visitante_UF || null,
      homeGoal,
      awayGoal,
      season,
      competition: "brasileirao-historico",
      competitionLabel: "Brasileirão (2003-2019)",
      round: r.Rodada ? String(r.Rodada) : null,
      stadium: r.Arena || null,
      winner: w,
    };
  });
}

function loadPlayers(): Player[] {
  const rows = readCsv("fifa_data.csv");
  const players: Player[] = [];
  for (const r of rows) {
    const id = parseNumber(r.ID);
    if (id === null) continue;
    players.push({
      id,
      name: r.Name || "",
      age: parseNumber(r.Age) ?? 0,
      nationality: r.Nationality || "",
      overall: parseNumber(r.Overall) ?? 0,
      potential: parseNumber(r.Potential) ?? 0,
      club: r.Club || "",
      position: r.Position || "",
      jerseyNumber: parseNumber(r["Jersey Number"]),
      height: r.Height || null,
      weight: r.Weight || null,
      preferredFoot: r["Preferred Foot"] || null,
    });
  }
  return players;
}
