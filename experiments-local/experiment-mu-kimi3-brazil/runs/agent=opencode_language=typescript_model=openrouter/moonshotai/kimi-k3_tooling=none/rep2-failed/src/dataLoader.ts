/**
 * CSV data loader: reads the six Kaggle datasets in `data/kaggle/` and
 * produces normalized Match and Player records for the knowledge graph.
 */

import { readFile } from "node:fs/promises";
import path from "node:path";
import { parse } from "csv-parse/sync";
import type { LoadedData, Match, Player } from "./types.js";
import {
  normalizeCompetition,
  parseDate,
  parseScore,
} from "./normalize.js";
import { canonicalTeamKey } from "./teams.js";

export const DATA_DIR = path.resolve(process.cwd(), "data", "kaggle");

type Row = Record<string, string>;

function readCsv(file: string): Promise<Row[]> {
  return readFile(path.join(DATA_DIR, file), "utf8").then((content) =>
    parse(content, {
      columns: true,
      skip_empty_lines: true,
      relax_quotes: true,
      relax_column_count: true,
      trim: true,
      bom: true,
    }) as Row[],
  );
}

function baseMatch(
  source: string,
  index: number,
  competitionRaw: string,
  home: string,
  away: string,
): Match {
  return {
    id: `${source}:${index}`,
    source,
    competition: normalizeCompetition(competitionRaw, source),
    competitionRaw,
    date: null,
    season: null,
    round: null,
    stage: null,
    homeTeam: home,
    awayTeam: away,
    homeKey: canonicalTeamKey(home),
    awayKey: canonicalTeamKey(away),
    homeGoals: null,
    awayGoals: null,
  };
}

async function loadBrasileirao(): Promise<Match[]> {
  const file = "Brasileirao_Matches.csv";
  const rows = await readCsv(file);
  const out: Match[] = [];
  rows.forEach((r, i) => {
    const m = baseMatch(file, i, "Brasileirão Série A", r.home_team, r.away_team);
    m.date = parseDate(r.datetime);
    m.season = parseScore(r.season);
    m.round = r.round ?? null;
    m.homeGoals = parseScore(r.home_goal);
    m.awayGoals = parseScore(r.away_goal);
    out.push(m);
  });
  return out;
}

async function loadBrazilianCup(): Promise<Match[]> {
  const file = "Brazilian_Cup_Matches.csv";
  const rows = await readCsv(file);
  const out: Match[] = [];
  rows.forEach((r, i) => {
    const m = baseMatch(file, i, "Copa do Brasil", r.home_team, r.away_team);
    m.date = parseDate(r.datetime);
    m.season = parseScore(r.season);
    m.round = r.round ?? null;
    m.homeGoals = parseScore(r.home_goal);
    m.awayGoals = parseScore(r.away_goal);
    out.push(m);
  });
  return out;
}

async function loadLibertadores(): Promise<Match[]> {
  const file = "Libertadores_Matches.csv";
  const rows = await readCsv(file);
  const out: Match[] = [];
  rows.forEach((r, i) => {
    const m = baseMatch(file, i, "Copa Libertadores", r.home_team, r.away_team);
    m.date = parseDate(r.datetime);
    m.season = parseScore(r.season);
    m.stage = r.stage ?? null;
    m.homeGoals = parseScore(r.home_goal);
    m.awayGoals = parseScore(r.away_goal);
    out.push(m);
  });
  return out;
}

async function loadBrFootball(): Promise<Match[]> {
  const file = "BR-Football-Dataset.csv";
  const rows = await readCsv(file);
  const out: Match[] = [];
  rows.forEach((r, i) => {
    const m = baseMatch(file, i, r.tournament ?? "", r.home, r.away);
    m.date = parseDate(r.date);
    m.season = m.date ? Number(m.date.slice(0, 4)) : null;
    m.homeGoals = parseScore(r.home_goal);
    m.awayGoals = parseScore(r.away_goal);
    out.push(m);
  });
  return out;
}

async function loadHistoricalBrasileirao(): Promise<Match[]> {
  const file = "novo_campeonato_brasileiro.csv";
  const rows = await readCsv(file);
  const out: Match[] = [];
  rows.forEach((r, i) => {
    const m = baseMatch(file, i, "Brasileirão Série A", r.Equipe_mandante, r.Equipe_visitante);
    m.date = parseDate(r.Data);
    m.season = parseScore(r.Ano);
    m.round = r.Rodada ?? null;
    m.homeGoals = parseScore(r.Gols_mandante);
    m.awayGoals = parseScore(r.Gols_visitante);
    out.push(m);
  });
  return out;
}

async function loadPlayers(): Promise<Player[]> {
  const rows = await readCsv("fifa_data.csv");
  const players: Player[] = [];
  for (const r of rows) {
    players.push({
      id: parseScore(r.ID) ?? 0,
      name: r.Name ?? "",
      age: parseScore(r.Age),
      nationality: r.Nationality ?? "",
      overall: parseScore(r.Overall),
      potential: parseScore(r.Potential),
      club: r.Club ?? "",
      position: r.Position ?? "",
      jerseyNumber: parseScore(r["Jersey Number"]),
    });
  }
  return players;
}

/** Load all six CSV files. Heavy enough to do once at startup, then cache. */
export async function loadAll(dataDir?: string): Promise<LoadedData> {
  void dataDir; // DATA_DIR is derived from cwd; override kept for future use.
  const [brasileirao, cup, libertadores, brFootball, historical, players] =
    await Promise.all([
      loadBrasileirao(),
      loadBrazilianCup(),
      loadLibertadores(),
      loadBrFootball(),
      loadHistoricalBrasileirao(),
      loadPlayers(),
    ]);
  return {
    matches: [
      ...brasileirao,
      ...cup,
      ...libertadores,
      ...brFootball,
      ...historical,
    ],
    players,
  };
}
