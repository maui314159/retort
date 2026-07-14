/**
 * CSV loader for all 6 Brazilian soccer datasets.
 *
 * Datasets loaded:
 *   1. Brasileirao_Matches.csv      — Brasileirao Serie A matches
 *   2. Brazilian_Cup_Matches.csv    — Copa do Brasil matches
 *   3. Libertadores_Matches.csv     — Copa Libertadores matches
 *   4. BR-Football-Dataset.csv      — Extended match statistics
 *   5. novo_campeonato_brasileiro.csv — Historical Brasileirao 2003-2019
 *   6. fifa_data.csv                — FIFA player database
 *
 * All matches are normalized to the common Match interface.
 * Data is loaded synchronously at startup and cached in memory.
 */

import { parse } from 'csv-parse/sync';
import { readFileSync } from 'fs';
import { join } from 'path';
import { parseDate, parseGoals, yearFromDate } from './normalize.js';
import type { DataStore, Match, Player } from './types.js';

let cache: DataStore | null = null;

function getDataDir(): string {
  return join(process.cwd(), 'data', 'kaggle');
}

function readCsv(filename: string): Record<string, string>[] {
  const filepath = join(getDataDir(), filename);
  // Strip BOM if present (fifa_data.csv has one)
  const raw = readFileSync(filepath, 'utf-8').replace(/^\uFEFF/, '');
  return parse(raw, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    relax_quotes: true,
    relax_column_count: true,
  }) as Record<string, string>[];
}

function loadBrasileiraoMatches(): Match[] {
  const rows = readCsv('Brasileirao_Matches.csv');
  return rows.map((row) => ({
    date: parseDate(row['datetime']),
    homeTeam: row['home_team'] ?? '',
    awayTeam: row['away_team'] ?? '',
    homeGoals: parseGoals(row['home_goal']),
    awayGoals: parseGoals(row['away_goal']),
    competition: 'brasileirao',
    season: parseInt(row['season']) || 0,
    round: row['round'],
  }));
}

function loadCopaBrasilMatches(): Match[] {
  const rows = readCsv('Brazilian_Cup_Matches.csv');
  return rows.map((row) => ({
    date: parseDate(row['datetime']),
    homeTeam: row['home_team'] ?? '',
    awayTeam: row['away_team'] ?? '',
    homeGoals: parseGoals(row['home_goal']),
    awayGoals: parseGoals(row['away_goal']),
    competition: 'copa_do_brasil',
    season: parseInt(row['season']) || 0,
    round: row['round'],
  }));
}

function loadLibertadoresMatches(): Match[] {
  const rows = readCsv('Libertadores_Matches.csv');
  return rows.map((row) => ({
    date: parseDate(row['datetime']),
    homeTeam: row['home_team'] ?? '',
    awayTeam: row['away_team'] ?? '',
    homeGoals: parseGoals(row['home_goal']),
    awayGoals: parseGoals(row['away_goal']),
    competition: 'libertadores',
    season: parseInt(row['season']) || 0,
    stage: row['stage'],
  }));
}

function loadExtendedMatches(): Match[] {
  const rows = readCsv('BR-Football-Dataset.csv');
  return rows.map((row) => {
    const date = parseDate(row['date']);
    return {
      date,
      homeTeam: row['home'] ?? '',
      awayTeam: row['away'] ?? '',
      homeGoals: parseGoals(row['home_goal']),
      awayGoals: parseGoals(row['away_goal']),
      competition: row['tournament'] ?? 'extended',
      season: yearFromDate(date),
      homeCorners: parseGoals(row['home_corner']) || undefined,
      awayCorners: parseGoals(row['away_corner']) || undefined,
      homeShots: parseGoals(row['home_shots']) || undefined,
      awayShots: parseGoals(row['away_shots']) || undefined,
      homeAttacks: parseGoals(row['home_attack']) || undefined,
      awayAttacks: parseGoals(row['away_attack']) || undefined,
    };
  });
}

function loadHistoricalMatches(): Match[] {
  const rows = readCsv('novo_campeonato_brasileiro.csv');
  return rows.map((row) => ({
    date: parseDate(row['Data']),
    homeTeam: row['Equipe_mandante'] ?? '',
    awayTeam: row['Equipe_visitante'] ?? '',
    homeGoals: parseGoals(row['Gols_mandante']),
    awayGoals: parseGoals(row['Gols_visitante']),
    competition: 'historico',
    season: parseInt(row['Ano']) || 0,
    round: row['Rodada'],
    arena: row['Arena'],
  }));
}

function loadPlayers(): Player[] {
  const rows = readCsv('fifa_data.csv');
  return rows.map((row, i) => ({
    id: parseInt(row['ID']) || i,
    name: row['Name'] ?? '',
    age: parseInt(row['Age']) || 0,
    nationality: row['Nationality'] ?? '',
    overall: parseInt(row['Overall']) || 0,
    potential: parseInt(row['Potential']) || 0,
    club: row['Club'] ?? '',
    position: row['Position'] ?? '',
    jerseyNumber: parseInt(row['Jersey Number']) || undefined,
    height: row['Height'] || undefined,
    weight: row['Weight'] || undefined,
    value: row['Value'] || undefined,
    wage: row['Wage'] || undefined,
  }));
}

/** Load all data from CSV files. Result is cached after first call. */
export function loadData(): DataStore {
  if (cache) return cache;
  const matches: Match[] = [
    ...loadBrasileiraoMatches(),
    ...loadCopaBrasilMatches(),
    ...loadLibertadoresMatches(),
    ...loadExtendedMatches(),
    ...loadHistoricalMatches(),
  ];
  const players = loadPlayers();
  cache = { matches, players };
  return cache;
}

/** Clear cache (useful in tests when running from different cwd). */
export function clearCache(): void {
  cache = null;
}
