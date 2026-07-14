/*
 * Brazilian Soccer MCP Server - CSV data loader
 *
 * Loads the six provided Kaggle CSV files, normalizes team names and dates,
 * and merges their records into a single queryable in-memory dataset. The
 * loader also de-duplicates matches that appear in multiple sources.
 */

import { readFile } from 'fs/promises';
import { resolve } from 'path';
import { parse } from 'csv-parse/sync';
import {
  Match,
  ExtendedMatchStats,
  Player,
  CompetitionName
} from './types.js';
import {
  normalizeTeamName,
  normalizeCompetition,
  parseBrazilianDate,
  formatDateISO,
  parseNumber,
  parseIntSafe,
  parseYear,
  matchesSameFixture
} from './normalizer.js';

export interface DataStore {
  matches: Match[];
  players: Player[];
  extendedStats: ExtendedMatchStats[];
}

const DATA_FILES = {
  brasileirao: 'Brasileirao_Matches.csv',
  copaDoBrasil: 'Brazilian_Cup_Matches.csv',
  libertadores: 'Libertadores_Matches.csv',
  brFootball: 'BR-Football-Dataset.csv',
  historical: 'novo_campeonato_brasileiro.csv',
  fifa: 'fifa_data.csv'
};

export async function loadDataset(dataDir: string): Promise<DataStore> {
  const matches: Match[] = [];
  const extendedStats: ExtendedMatchStats[] = [];

  await loadBrasileirao(resolve(dataDir, DATA_FILES.brasileirao), matches);
  await loadCopaDoBrasil(resolve(dataDir, DATA_FILES.copaDoBrasil), matches);
  await loadLibertadores(resolve(dataDir, DATA_FILES.libertadores), matches);
  await loadBRFootball(resolve(dataDir, DATA_FILES.brFootball), matches, extendedStats);
  await loadHistorical(resolve(dataDir, DATA_FILES.historical), matches);

  const players = await loadFifaPlayers(resolve(dataDir, DATA_FILES.fifa));

  const deduplicatedMatches = deduplicateMatches(matches);

  return {
    matches: deduplicatedMatches,
    players,
    extendedStats
  };
}

async function readCsv(filePath: string): Promise<Record<string, string>[]> {
  const content = await readFile(filePath, 'utf-8');
  return parse(content, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    bom: true
  }) as Record<string, string>[];
}

function baseMatchFromRow(
  row: Record<string, string>,
  competition: CompetitionName,
  source: string,
  datetime: Date | null,
  season: number | null,
  overrides: Partial<Match> = {}
): Match {
  const date = datetime ? formatDateISO(datetime) : '';
  return {
    datetime: datetime ?? new Date(0),
    date,
    season: season ?? 0,
    competition: normalizeCompetition(competition),
    round: overrides.round,
    stage: overrides.stage,
    homeTeam: normalizeTeamName(row.home_team ?? row.home ?? row.Equipe_mandante ?? ''),
    homeTeamState: row.home_team_state ?? row.Mandante_UF ?? undefined,
    awayTeam: normalizeTeamName(row.away_team ?? row.away ?? row.Equipe_visitante ?? ''),
    awayTeamState: row.away_team_state ?? row.Visitante_UF ?? undefined,
    homeGoal: parseIntSafe(row.home_goal ?? row.Gols_mandante ?? row.home_goal),
    awayGoal: parseIntSafe(row.away_goal ?? row.Gols_visitante ?? row.away_goal),
    source,
    ...overrides
  };
}

async function loadBrasileirao(filePath: string, matches: Match[]): Promise<void> {
  const rows = await readCsv(filePath);
  for (const row of rows) {
    const datetime = parseBrazilianDate(row.datetime);
    const season = parseYear(row.season) ?? (datetime ? datetime.getFullYear() : null);
    matches.push(
      baseMatchFromRow(row, 'Brasileirão', 'Brasileirao_Matches.csv', datetime, season, {
        round: row.round
      })
    );
  }
}

async function loadCopaDoBrasil(filePath: string, matches: Match[]): Promise<void> {
  const rows = await readCsv(filePath);
  for (const row of rows) {
    const datetime = parseBrazilianDate(row.datetime);
    const season = parseYear(row.season) ?? (datetime ? datetime.getFullYear() : null);
    matches.push(
      baseMatchFromRow(row, 'Copa do Brasil', 'Brazilian_Cup_Matches.csv', datetime, season, {
        round: row.round
      })
    );
  }
}

async function loadLibertadores(filePath: string, matches: Match[]): Promise<void> {
  const rows = await readCsv(filePath);
  for (const row of rows) {
    const datetime = parseBrazilianDate(row.datetime);
    const season = parseYear(row.season) ?? (datetime ? datetime.getFullYear() : null);
    matches.push(
      baseMatchFromRow(row, 'Copa Libertadores', 'Libertadores_Matches.csv', datetime, season, {
        stage: row.stage
      })
    );
  }
}

async function loadBRFootball(
  filePath: string,
  matches: Match[],
  extendedStats: ExtendedMatchStats[]
): Promise<void> {
  const rows = await readCsv(filePath);
  for (const row of rows) {
    const datetime = parseBrazilianDate(`${row.date} ${row.time ?? ''}`.trim());
    const competition = row.tournament || 'Unknown';
    const season = datetime ? datetime.getFullYear() : null;
    const base = baseMatchFromRow(row, competition, 'BR-Football-Dataset.csv', datetime, season);

    const extended: ExtendedMatchStats = {
      ...base,
      homeCorner: parseNumber(row.home_corner ?? row.home_corner),
      awayCorner: parseNumber(row.away_corner ?? row.away_corner),
      homeAttack: parseNumber(row.home_attack ?? row.home_attack),
      awayAttack: parseNumber(row.away_attack ?? row.away_attack),
      homeShots: parseNumber(row.home_shots ?? row.home_shots),
      awayShots: parseNumber(row.away_shots ?? row.away_shots),
      halfTimeResult: row.ht_result ?? row.at_result,
      totalCorners: parseNumber(row.total_corners ?? row.total_corners)
    };

    matches.push(base);
    extendedStats.push(extended);
  }
}

async function loadHistorical(filePath: string, matches: Match[]): Promise<void> {
  const rows = await readCsv(filePath);
  for (const row of rows) {
    const datetime = parseBrazilianDate(row.Data);
    const season = parseYear(row.Ano) ?? (datetime ? datetime.getFullYear() : null);
    matches.push(
      baseMatchFromRow(row, 'Brasileirão', 'novo_campeonato_brasileiro.csv', datetime, season, {
        id: row.ID,
        round: row.Rodada,
        stadium: row.Arena
      })
    );
  }
}

async function loadFifaPlayers(filePath: string): Promise<Player[]> {
  const rows = await readCsv(filePath);
  return rows.map((row) => ({
    id: row.ID,
    name: row.Name,
    age: parseIntSafe(row.Age) ?? undefined,
    nationality: row.Nationality || '',
    overall: parseIntSafe(row.Overall) ?? undefined,
    potential: parseIntSafe(row.Potential) ?? undefined,
    club: row.Club || undefined,
    position: row.Position || undefined,
    jerseyNumber: row['Jersey Number'] || undefined,
    height: row.Height || undefined,
    weight: row.Weight || undefined,
    source: 'fifa_data.csv'
  }));
}

export function deduplicateMatches(matches: Match[]): Match[] {
  const seen = new Set<string>();
  const result: Match[] = [];

  // Sort by most reliable sources first, preferring richer records.
  const sourcePriority: Record<string, number> = {
    'Brasileirao_Matches.csv': 1,
    'novo_campeonato_brasileiro.csv': 1,
    'Brazilian_Cup_Matches.csv': 2,
    'Libertadores_Matches.csv': 2,
    'BR-Football-Dataset.csv': 3
  };

  const sorted = [...matches].sort((a, b) => {
    const pa = sourcePriority[a.source] ?? 99;
    const pb = sourcePriority[b.source] ?? 99;
    if (pa !== pb) return pa - pb;
    return b.datetime.getTime() - a.datetime.getTime();
  });

  for (const match of sorted) {
    const key = `${match.date}::${match.homeTeam.toLowerCase()}::${match.awayTeam.toLowerCase()}::${match.competition.toLowerCase()}`;
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(match);
  }

  return result.sort((a, b) => b.datetime.getTime() - a.datetime.getTime());
}
