/**
 * CSV loaders for every dataset required by the specification.
 *
 * Each loader reads one Kaggle file and turns it into the common Match / Player
 * shapes used by the in-memory store. Row-level quirks (accents, float goals,
 * Brazilian dates, state suffixes, missing IDs) are handled here.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { parse } from "csv-parse/sync";
import type { Match, Player } from "./types.js";
import {
  normalizeCompetition,
  parseDate,
  parseGoal,
  parseSeason,
  teamDisplay,
  teamKey,
} from "./normalize.js";

export interface LoadOptions {
  dataDir?: string;
}

function readCsv(path: string): Record<string, string>[] {
  const content = readFileSync(path, "utf-8");
  return parse(content, {
    columns: (header: string[]) => header.map((h) => (h ?? "").trim()),
    skip_empty_lines: true,
    trim: true,
    bom: true,
    cast: false,
  }) as Record<string, string>[];
}

function parseMatchDate(
  dateValue: string | undefined,
  timeValue: string | undefined,
  datetimeValue: string | undefined
): Date | null {
  if (datetimeValue) return parseDate(datetimeValue);
  if (dateValue && timeValue) return parseDate(`${dateValue} ${timeValue}`);
  if (dateValue) return parseDate(dateValue);
  return null;
}

function buildMatch(
  base: Omit<Match, "homeKey" | "awayKey" | "homeTeam" | "awayTeam">,
  home: string,
  away: string
): Match {
  const homeKey = teamKey(home);
  const awayKey = teamKey(away);
  return {
    ...base,
    homeTeam: teamDisplay(home, homeKey),
    awayTeam: teamDisplay(away, awayKey),
    homeKey,
    awayKey,
  };
}

export function loadBrasileirao(dataDir: string): Match[] {
  const rows = readCsv(join(dataDir, "Brasileirao_Matches.csv"));
  return rows.map((row) => {
    const home = row["home_team"] ?? "";
    const away = row["away_team"] ?? "";
    return buildMatch(
      {
        source: "Brasileirao_Matches",
        competition: "Brasileirão",
        season: parseSeason(row["season"]),
        date: parseMatchDate(undefined, undefined, row["datetime"]),
        homeGoals: parseGoal(row["home_goal"]),
        awayGoals: parseGoal(row["away_goal"]),
        round: row["round"] || null,
      },
      home,
      away
    );
  });
}

export function loadCopaDoBrasil(dataDir: string): Match[] {
  const rows = readCsv(join(dataDir, "Brazilian_Cup_Matches.csv"));
  return rows.map((row) => {
    const home = row["home_team"] ?? "";
    const away = row["away_team"] ?? "";
    return buildMatch(
      {
        source: "Brazilian_Cup_Matches",
        competition: "Copa do Brasil",
        season: parseSeason(row["season"]),
        date: parseMatchDate(undefined, undefined, row["datetime"]),
        homeGoals: parseGoal(row["home_goal"]),
        awayGoals: parseGoal(row["away_goal"]),
        round: row["round"] || null,
      },
      home,
      away
    );
  });
}

export function loadLibertadores(dataDir: string): Match[] {
  const rows = readCsv(join(dataDir, "Libertadores_Matches.csv"));
  return rows.map((row) => {
    const home = row["home_team"] ?? "";
    const away = row["away_team"] ?? "";
    return buildMatch(
      {
        source: "Libertadores_Matches",
        competition: "Copa Libertadores",
        season: parseSeason(row["season"]),
        date: parseMatchDate(undefined, undefined, row["datetime"]),
        homeGoals: parseGoal(row["home_goal"]),
        awayGoals: parseGoal(row["away_goal"]),
        round: row["stage"] || null,
      },
      home,
      away
    );
  });
}

export function loadBrFootball(dataDir: string): Match[] {
  const rows = readCsv(join(dataDir, "BR-Football-Dataset.csv"));
  return rows.map((row) => {
    const home = row["home"] ?? "";
    const away = row["away"] ?? "";
    return buildMatch(
      {
        source: "BR-Football-Dataset",
        competition: normalizeCompetition(row["tournament"] ?? ""),
        season: parseSeason(row["date"] ? row["date"].slice(0, 4) : ""),
        date: parseMatchDate(row["date"], row["time"], undefined),
        homeGoals: parseGoal(row["home_goal"]),
        awayGoals: parseGoal(row["away_goal"]),
        round: null,
      },
      home,
      away
    );
  });
}

export function loadNovoCampeonato(dataDir: string): Match[] {
  const rows = readCsv(join(dataDir, "novo_campeonato_brasileiro.csv"));
  return rows.map((row) => {
    const home = row["Equipe_mandante"] ?? "";
    const away = row["Equipe_visitante"] ?? "";
    return buildMatch(
      {
        source: "novo_campeonato_brasileiro",
        competition: "Brasileirão",
        season: parseSeason(row["Ano"]),
        date: parseMatchDate(row["Data"], undefined, undefined),
        homeGoals: parseGoal(row["Gols_mandante"]),
        awayGoals: parseGoal(row["Gols_visitante"]),
        round: row["Rodada"] || null,
        stadium: row["Arena"] || null,
      },
      home,
      away
    );
  });
}

export function loadFifaPlayers(dataDir: string): Player[] {
  const rows = readCsv(join(dataDir, "fifa_data.csv"));
  return rows.map((row) => {
    const club = row["Club"] || null;
    const clubKey = club ? teamKey(club) : null;
    return {
      id: parseGoal(row["ID"]),
      name: row["Name"] || "Unknown",
      age: parseGoal(row["Age"]),
      nationality: row["Nationality"] || null,
      overall: parseGoal(row["Overall"]),
      potential: parseGoal(row["Potential"]),
      club,
      clubKey,
      position: row["Position"] || null,
      jerseyNumber: parseGoal(row["Jersey Number"]),
    };
  });
}

export async function loadAllData(dataDir: string): Promise<{
  matches: Match[];
  players: Player[];
}> {
  const matches = [
    ...loadBrasileirao(dataDir),
    ...loadCopaDoBrasil(dataDir),
    ...loadLibertadores(dataDir),
    ...loadBrFootball(dataDir),
    ...loadNovoCampeonato(dataDir),
  ];

  // De-duplicate identical rows across overlapping datasets, allowing a one-day
  // date difference because some sources store UTC dates while others store
  // local Brazilian calendar dates.
  const fuzzy = new Map<string, Match[]>();
  const deduped: Match[] = [];
  for (const m of matches) {
    const baseKey = [
      m.competition,
      m.season,
      m.homeKey,
      m.awayKey,
      m.homeGoals ?? "",
      m.awayGoals ?? "",
    ].join("|");
    const siblings = fuzzy.get(baseKey) ?? [];
    let isDuplicate = false;
    if (m.date) {
      for (const sibling of siblings) {
        if (sibling.date && Math.abs(m.date.getTime() - sibling.date.getTime()) <= 86_400_000) {
          isDuplicate = true;
          break;
        }
      }
    } else if (siblings.some((s) => !s.date)) {
      isDuplicate = true;
    }
    if (isDuplicate) continue;
    siblings.push(m);
    fuzzy.set(baseKey, siblings);
    deduped.push(m);
  }

  const players = loadFifaPlayers(dataDir);
  return { matches: deduped, players };
}
