import { parse } from "csv-parse/sync";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import type {
  Competition,
  NormalizedMatch,
  PlayerRecord,
} from "./types.js";
import {
  normalizeTeamName,
  parseDate,
  toISODate,
  toNumber,
} from "./normalize.js";

const DEFAULT_DATA_DIR = "data/kaggle";

export interface LoadedData {
  matches: NormalizedMatch[];
  players: PlayerRecord[];
}

const readCSV = (filePath: string): Record<string, string>[] => {
  const content = readFileSync(filePath, "utf-8");
  const records = parse(content, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    bom: true,
    relax_column_count: true,
  }) as Record<string, string>[];
  return records.map((r) => {
    const out: Record<string, string> = {};
    for (const [k, v] of Object.entries(r)) {
      out[k.trim()] = v;
    }
    return out;
  });
};

const determineWinner = (
  homeGoals: number | null,
  awayGoals: number | null
): "home" | "away" | "draw" | null => {
  if (homeGoals == null || awayGoals == null) return null;
  if (homeGoals > awayGoals) return "home";
  if (homeGoals < awayGoals) return "away";
  return "draw";
};

const loadBrasileirao = (dir: string): NormalizedMatch[] => {
  const rows = readCSV(join(dir, "Brasileirao_Matches.csv"));
  return rows.map((r, i) => {
    const homeGoals = toNumber(r.home_goal);
    const awayGoals = toNumber(r.away_goal);
    return {
      id: `Brasileirao:${r.season}:${i}`,
      competition: "Brasileirao",
      competitionLabel: "Brasileirao Serie A",
      season: toNumber(r.season) ?? 0,
      date: toISODate(r.datetime),
      dateObj: parseDate(r.datetime),
      homeTeam: normalizeTeamName(r.home_team),
      awayTeam: normalizeTeamName(r.away_team),
      homeTeamRaw: r.home_team ?? "",
      awayTeamRaw: r.away_team ?? "",
      homeGoals,
      awayGoals,
      round: r.round,
      homeState: r.home_team_state,
      awayState: r.away_team_state,
      winner: determineWinner(homeGoals, awayGoals),
    } as NormalizedMatch;
  });
};

const loadCopaDoBrasil = (dir: string): NormalizedMatch[] => {
  const rows = readCSV(join(dir, "Brazilian_Cup_Matches.csv"));
  return rows.map((r, i) => {
    const homeGoals = toNumber(r.home_goal);
    const awayGoals = toNumber(r.away_goal);
    return {
      id: `CopaDoBrasil:${r.season}:${i}`,
      competition: "CopaDoBrasil",
      competitionLabel: "Copa do Brasil",
      season: toNumber(r.season) ?? 0,
      date: toISODate(r.datetime),
      dateObj: parseDate(r.datetime),
      homeTeam: normalizeTeamName(r.home_team),
      awayTeam: normalizeTeamName(r.away_team),
      homeTeamRaw: r.home_team ?? "",
      awayTeamRaw: r.away_team ?? "",
      homeGoals,
      awayGoals,
      round: r.round,
      winner: determineWinner(homeGoals, awayGoals),
    } as NormalizedMatch;
  });
};

const loadLibertadores = (dir: string): NormalizedMatch[] => {
  const rows = readCSV(join(dir, "Libertadores_Matches.csv"));
  return rows.map((r, i) => {
    const homeGoals = toNumber(r.home_goal);
    const awayGoals = toNumber(r.away_goal);
    return {
      id: `Libertadores:${r.season}:${i}`,
      competition: "Libertadores",
      competitionLabel: "Copa Libertadores",
      season: toNumber(r.season) ?? 0,
      date: toISODate(r.datetime),
      dateObj: parseDate(r.datetime),
      homeTeam: normalizeTeamName(r.home_team),
      awayTeam: normalizeTeamName(r.away_team),
      homeTeamRaw: r.home_team ?? "",
      awayTeamRaw: r.away_team ?? "",
      homeGoals,
      awayGoals,
      stage: r.stage,
      winner: determineWinner(homeGoals, awayGoals),
    } as NormalizedMatch;
  });
};

const loadBRFootball = (dir: string): NormalizedMatch[] => {
  const rows = readCSV(join(dir, "BR-Football-Dataset.csv"));
  return rows.map((r, i) => {
    const homeGoals = toNumber(r.home_goal);
    const awayGoals = toNumber(r.away_goal);
    const homeCorner = toNumber(r.home_corner);
    const awayCorner = toNumber(r.away_corner);
    const totalCorners = toNumber(r.total_corners);
    const homeShots = toNumber(r.home_shots);
    const awayShots = toNumber(r.away_shots);
    const homeAttack = toNumber(r.home_attack);
    const awayAttack = toNumber(r.away_attack);
    const htHome = r.ht_result === "WON" ? 1 : r.ht_result === "LOST" ? 0 : r.ht_result === "DRAW" ? 0 : null;
    const htAway = r.at_result === "WON" ? 1 : r.at_result === "LOST" ? 0 : r.at_result === "DRAW" ? 0 : null;
    const competitionLabel = r.tournament ?? "BR Football";
    const comp: Competition = "BRFootball";
    const seasonMatch = (r.date || "").match(/^(\d{4})/);
    return {
      id: `BRFootball:${i}`,
      competition: comp,
      competitionLabel,
      season: seasonMatch ? Number(seasonMatch[1]) : 0,
      date: toISODate(r.date),
      dateObj: parseDate(r.date),
      homeTeam: normalizeTeamName(r.home),
      awayTeam: normalizeTeamName(r.away),
      homeTeamRaw: r.home ?? "",
      awayTeamRaw: r.away ?? "",
      homeGoals,
      awayGoals,
      halfTimeHome: htHome,
      halfTimeAway: htAway,
      corners: { home: homeCorner, away: awayCorner, total: totalCorners },
      shots: { home: homeShots, away: awayShots },
      attacks: { home: homeAttack, away: awayAttack },
      winner: determineWinner(homeGoals, awayGoals),
    } as NormalizedMatch;
  });
};

const loadHistorico = (dir: string): NormalizedMatch[] => {
  const rows = readCSV(join(dir, "novo_campeonato_brasileiro.csv"));
  return rows.map((r, i) => {
    const homeGoals = toNumber(r.Gols_mandante);
    const awayGoals = toNumber(r.Gols_visitante);
    let winner: "home" | "away" | "draw" | null = null;
    const v = (r.Vencedor || "").trim().toLowerCase();
    if (v === "mandante") winner = "home";
    else if (v === "visitante") winner = "away";
    else if (v === "empate" || v === "-") winner = "draw";
    else winner = determineWinner(homeGoals, awayGoals);
    return {
      id: `BrasileiraoHistorico:${r.ID || i}`,
      competition: "BrasileiraoHistorico",
      competitionLabel: "Brasileirao (2003-2019)",
      season: toNumber(r.Ano) ?? 0,
      date: toISODate(r.Data),
      dateObj: parseDate(r.Data),
      homeTeam: normalizeTeamName(r.Equipe_mandante),
      awayTeam: normalizeTeamName(r.Equipe_visitante),
      homeTeamRaw: r.Equipe_mandante ?? "",
      awayTeamRaw: r.Equipe_visitante ?? "",
      homeGoals,
      awayGoals,
      round: r.Rodada,
      homeState: r.Mandante_UF,
      awayState: r.Visitante_UF,
      stadium: r.Arena,
      winner,
    } as NormalizedMatch;
  });
};

const SKILL_COLUMNS = [
  "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
  "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
  "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
  "ShotPower", "Jumping", "Stamina", "Strength", "LongShots",
  "Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
  "Composure", "Marking", "StandingTackle", "SlidingTackle",
  "GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes",
];

const loadPlayers = (dir: string): PlayerRecord[] => {
  const rows = readCSV(join(dir, "fifa_data.csv"));
  return rows.map((r) => {
    const skills: Record<string, number> = {};
    for (const col of SKILL_COLUMNS) {
      const n = toNumber(r[col]);
      if (n != null) skills[col] = n;
    }
    return {
      id: toNumber(r.ID) ?? 0,
      name: (r.Name || "").trim(),
      age: toNumber(r.Age),
      nationality: (r.Nationality || "").trim(),
      overall: toNumber(r.Overall),
      potential: toNumber(r.Potential),
      club: (r.Club || "").trim(),
      position: (r.Position || "").trim(),
      jerseyNumber: toNumber(r["Jersey Number"]),
      height: r.Height || null,
      weight: r.Weight || null,
      preferredFoot: r["Preferred Foot"] || null,
      value: r.Value || null,
      wage: r.Wage || null,
      skills,
    } as PlayerRecord;
  });
};

let cached: LoadedData | null = null;

export const loadData = (dataDir: string = DEFAULT_DATA_DIR): LoadedData => {
  if (cached) return cached;
  const matches: NormalizedMatch[] = [
    ...loadBrasileirao(dataDir),
    ...loadCopaDoBrasil(dataDir),
    ...loadLibertadores(dataDir),
    ...loadBRFootball(dataDir),
    ...loadHistorico(dataDir),
  ];
  const players = loadPlayers(dataDir);
  cached = { matches, players };
  return cached;
};

export const resetCache = (): void => {
  cached = null;
};
