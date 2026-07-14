import fs from "fs";
import path from "path";
import { parse } from "csv-parse/sync";
import { Match, Player } from "./types.js";
import {
  parseDate,
  parseIntOrNaN,
  safeString,
  teamKey,
  normalizeTeamName,
} from "./normalize.js";

export interface Dataset {
  matches: Match[];
  players: Player[];
}

let defaultDataDir: string;
try {
  defaultDataDir = path.resolve("data/kaggle");
} catch {
  defaultDataDir = "data/kaggle";
}

function makeMatchId(source: string, index: number, raw?: string): string {
  return `${source}-${index}-${raw ?? index}`;
}

function readCsv(filePath: string): Record<string, string>[] {
  const content = fs.readFileSync(filePath, { encoding: "utf-8" });
  return parse(content, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    bom: true,
  });
}

function loadBrasileirao(dataDir: string): Match[] {
  const rows = readCsv(path.join(dataDir, "Brasileirao_Matches.csv"));
  return rows.map((row, idx) => {
    const rawHome = safeString(row.home_team);
    const rawAway = safeString(row.away_team);
    const date = parseDate(row.datetime) ?? "";
    return {
      id: makeMatchId("brasileirao", idx, row.datetime),
      date,
      datetime: safeString(row.datetime),
      season: parseIntOrNaN(row.season),
      competition: "Brasileirão",
      round: safeString(row.round),
      homeTeam: normalizeTeamName(rawHome),
      awayTeam: normalizeTeamName(rawAway),
      homeTeamState: safeString(row.home_team_state),
      awayTeamState: safeString(row.away_team_state),
      homeGoal: parseIntOrNaN(row.home_goal),
      awayGoal: parseIntOrNaN(row.away_goal),
      source: "Brasileirao_Matches.csv",
      rawHome,
      rawAway,
    };
  });
}

function loadBrazilianCup(dataDir: string): Match[] {
  const rows = readCsv(path.join(dataDir, "Brazilian_Cup_Matches.csv"));
  return rows.map((row, idx) => {
    const rawHome = safeString(row.home_team);
    const rawAway = safeString(row.away_team);
    const date = parseDate(row.datetime) ?? "";
    return {
      id: makeMatchId("copadobrasil", idx, row.datetime),
      date,
      datetime: safeString(row.datetime),
      season: parseIntOrNaN(row.season),
      competition: "Copa do Brasil",
      round: safeString(row.round),
      homeTeam: normalizeTeamName(rawHome),
      awayTeam: normalizeTeamName(rawAway),
      homeGoal: parseIntOrNaN(row.home_goal),
      awayGoal: parseIntOrNaN(row.away_goal),
      source: "Brazilian_Cup_Matches.csv",
      rawHome,
      rawAway,
    };
  });
}

function loadLibertadores(dataDir: string): Match[] {
  const rows = readCsv(path.join(dataDir, "Libertadores_Matches.csv"));
  return rows.map((row, idx) => {
    const rawHome = safeString(row.home_team);
    const rawAway = safeString(row.away_team);
    const date = parseDate(row.datetime) ?? "";
    return {
      id: makeMatchId("libertadores", idx, row.datetime),
      date,
      datetime: safeString(row.datetime),
      season: parseIntOrNaN(row.season),
      competition: "Copa Libertadores",
      stage: safeString(row.stage),
      homeTeam: normalizeTeamName(rawHome),
      awayTeam: normalizeTeamName(rawAway),
      homeGoal: parseIntOrNaN(row.home_goal),
      awayGoal: parseIntOrNaN(row.away_goal),
      source: "Libertadores_Matches.csv",
      rawHome,
      rawAway,
    };
  });
}

function loadExtended(dataDir: string): Match[] {
  const rows = readCsv(path.join(dataDir, "BR-Football-Dataset.csv"));
  const competitionMap: Record<string, string> = {
    "Copa do Brasil": "Copa do Brasil",
    "Brasileirao": "Brasileirão",
    "Serie A": "Brasileirão",
    "Serie B": "Brasileirão Série B",
    Libertadores: "Copa Libertadores",
  };
  return rows.map((row, idx) => {
    const rawHome = safeString(row.home);
    const rawAway = safeString(row.away);
    const rawComp = safeString(row.tournament);
    const date = parseDate(row.date) ?? "";
    return {
      id: makeMatchId("extended", idx, row.date),
      date,
      season: date ? parseIntOrNaN(date.slice(0, 4)) : NaN,
      competition: competitionMap[rawComp] ?? rawComp,
      homeTeam: normalizeTeamName(rawHome),
      awayTeam: normalizeTeamName(rawAway),
      homeGoal: parseIntOrNaN(row.home_goal),
      awayGoal: parseIntOrNaN(row.away_goal),
      source: "BR-Football-Dataset.csv",
      rawHome,
      rawAway,
    };
  });
}

function loadHistorical(dataDir: string): Match[] {
  const rows = readCsv(path.join(dataDir, "novo_campeonato_brasileiro.csv"));
  return rows.map((row, idx) => {
    const rawHome = safeString(row.Equipe_mandante);
    const rawAway = safeString(row.Equipe_visitante);
    const date = parseDate(row.Data) ?? "";
    return {
      id: makeMatchId("historical", idx, row.ID),
      date,
      season: parseIntOrNaN(row.Ano),
      competition: "Brasileirão",
      round: safeString(row.Rodada),
      homeTeam: normalizeTeamName(rawHome),
      awayTeam: normalizeTeamName(rawAway),
      homeTeamState: safeString(row.Mandante_UF),
      awayTeamState: safeString(row.Visitante_UF),
      homeGoal: parseIntOrNaN(row.Gols_mandante),
      awayGoal: parseIntOrNaN(row.Gols_visitante),
      stadium: safeString(row.Arena),
      source: "novo_campeonato_brasileiro.csv",
      rawHome,
      rawAway,
    };
  });
}

function loadPlayers(dataDir: string): Player[] {
  const rows = readCsv(path.join(dataDir, "fifa_data.csv"));
  return rows.map((row) => ({
    id: parseIntOrNaN(row.ID) ?? 0,
    name: safeString(row.Name),
    age: parseIntOrNaN(row.Age) ?? 0,
    nationality: safeString(row.Nationality),
    overall: parseIntOrNaN(row.Overall) ?? 0,
    potential: parseIntOrNaN(row.Potential) ?? 0,
    club: safeString(row.Club),
    position: safeString(row.Position),
    jerseyNumber: parseIntOrNaN(row["Jersey Number"]) || undefined,
    height: safeString(row.Height),
    weight: safeString(row.Weight),
  }));
}

export function loadDataset(dataDir: string = defaultDataDir): Dataset {
  const rawMatches = [
    ...loadBrasileirao(dataDir),
    ...loadBrazilianCup(dataDir),
    ...loadLibertadores(dataDir),
    ...loadExtended(dataDir),
    ...loadHistorical(dataDir),
  ];

  // Deduplicate matches that represent the same fixture across sources.
  // Prefer earlier sources in the order above.
  const seen = new Set<string>();
  const matches: Match[] = [];
  for (const m of rawMatches) {
    const key = `${m.date}|${teamKey(m.homeTeam)}|${teamKey(m.awayTeam)}|${m.competition}`;
    if (seen.has(key)) continue;
    seen.add(key);
    matches.push(m);
  }

  const players = loadPlayers(dataDir);
  return { matches, players };
}
