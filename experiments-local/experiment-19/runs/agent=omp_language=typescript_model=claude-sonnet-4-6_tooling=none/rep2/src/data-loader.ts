import { parse } from 'csv-parse/sync';
import { readFileSync } from 'fs';
import { dirname, resolve } from 'path';
import { fileURLToPath } from 'url';

import { parseDate, parseGoals, stripStateSuffix } from './normalize.js';
import type { Competition, Database, Match, Player } from './types.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
// Works whether running from dist/ (compiled) or src/ (vitest), since both sit
// one level below the project root which contains data/kaggle/.
const DATA_DIR = resolve(__dirname, '..', 'data', 'kaggle');

function csvPath(filename: string): string {
  return resolve(DATA_DIR, filename);
}

function loadCsv(filename: string): Record<string, string>[] {
  const content = readFileSync(csvPath(filename));
  return parse(content, {
    columns: true,
    skip_empty_lines: true,
    bom: true,
    relax_column_count: true,
    trim: true,
  }) as Record<string, string>[];
}

// ---------------------------------------------------------------------------
// Individual loaders
// ---------------------------------------------------------------------------

function loadBrasileiraoMatches(): Match[] {
  const rows = loadCsv('Brasileirao_Matches.csv');
  return rows.map((r) => {
    const homeTeam = r['home_team'] ?? '';
    const awayTeam = r['away_team'] ?? '';
    return {
      date: parseDate(r['datetime'] ?? ''),
      homeTeam,
      homeTeamNormalized: stripStateSuffix(homeTeam),
      awayTeam,
      awayTeamNormalized: stripStateSuffix(awayTeam),
      homeGoals: parseGoals(r['home_goal']),
      awayGoals: parseGoals(r['away_goal']),
      season: parseInt(r['season'] ?? '0', 10),
      competition: 'Brasileirão Serie A' as Competition,
      round: r['round'] ?? undefined,
      source: 'brasileirao',
    };
  });
}

function loadCopaBrasilMatches(): Match[] {
  const rows = loadCsv('Brazilian_Cup_Matches.csv');
  return rows.map((r) => {
    const homeTeam = r['home_team'] ?? '';
    const awayTeam = r['away_team'] ?? '';
    return {
      date: parseDate(r['datetime'] ?? ''),
      homeTeam,
      homeTeamNormalized: stripStateSuffix(homeTeam),
      awayTeam,
      awayTeamNormalized: stripStateSuffix(awayTeam),
      homeGoals: parseGoals(r['home_goal']),
      awayGoals: parseGoals(r['away_goal']),
      season: parseInt(r['season'] ?? '0', 10),
      competition: 'Copa do Brasil' as Competition,
      round: r['round'] ?? undefined,
      source: 'copa_brasil',
    };
  });
}

function loadLibertadoresMatches(): Match[] {
  const rows = loadCsv('Libertadores_Matches.csv');
  return rows.map((r) => {
    const homeTeam = r['home_team'] ?? '';
    const awayTeam = r['away_team'] ?? '';
    const rawSeason = r['season'] ?? '0';
    const season = rawSeason === 'NA' ? 0 : parseInt(rawSeason, 10);
    return {
      date: parseDate(r['datetime'] ?? ''),
      homeTeam,
      homeTeamNormalized: stripStateSuffix(homeTeam),
      awayTeam,
      awayTeamNormalized: stripStateSuffix(awayTeam),
      homeGoals: parseGoals(r['home_goal']),
      awayGoals: parseGoals(r['away_goal']),
      season,
      competition: 'Copa Libertadores' as Competition,
      stage: r['stage'] ?? undefined,
      source: 'libertadores',
    };
  });
}

/** Map tournament string from BR-Football-Dataset to Competition type. */
function mapBrFootballCompetition(t: string): Competition {
  const lower = t.toLowerCase();
  if (lower.includes('serie a')) return 'Brasileirão Serie A';
  if (lower.includes('serie b')) return 'Serie B';
  if (lower.includes('serie c')) return 'Serie C';
  if (lower.includes('copa do brasil')) return 'Copa do Brasil';
  return 'Unknown';
}

function loadBrFootballMatches(): Match[] {
  const rows = loadCsv('BR-Football-Dataset.csv');
  return rows.map((r) => {
    const homeTeam = r['home'] ?? '';
    const awayTeam = r['away'] ?? '';
    return {
      date: parseDate(r['date'] ?? ''),
      homeTeam,
      homeTeamNormalized: stripStateSuffix(homeTeam),
      awayTeam,
      awayTeamNormalized: stripStateSuffix(awayTeam),
      homeGoals: parseGoals(r['home_goal']),
      awayGoals: parseGoals(r['away_goal']),
      season: r['date'] ? parseInt(r['date'].substring(0, 4), 10) : 0,
      competition: mapBrFootballCompetition(r['tournament'] ?? ''),
      homeCorners: r['home_corner'] ? parseGoals(r['home_corner']) : undefined,
      awayCorners: r['away_corner'] ? parseGoals(r['away_corner']) : undefined,
      homeShots: r['home_shots'] ? parseGoals(r['home_shots']) : undefined,
      awayShots: r['away_shots'] ? parseGoals(r['away_shots']) : undefined,
      source: 'br_football',
    };
  });
}

function loadHistoricoMatches(): Match[] {
  const rows = loadCsv('novo_campeonato_brasileiro.csv');
  return rows.map((r) => {
    const homeTeam = r['Equipe_mandante'] ?? '';
    const awayTeam = r['Equipe_visitante'] ?? '';
    return {
      date: parseDate(r['Data'] ?? ''),
      homeTeam,
      homeTeamNormalized: stripStateSuffix(homeTeam),
      awayTeam,
      awayTeamNormalized: stripStateSuffix(awayTeam),
      homeGoals: parseGoals(r['Gols_mandante']),
      awayGoals: parseGoals(r['Gols_visitante']),
      season: parseInt(r['Ano'] ?? '0', 10),
      competition: 'Brasileirão Serie A' as Competition,
      round: r['Rodada'] ?? undefined,
      arena: r['Arena'] ?? undefined,
      source: 'historico',
    };
  });
}

function loadPlayers(): Player[] {
  const rows = loadCsv('fifa_data.csv');
  return rows.map((r) => {
    const n = (col: string): number | undefined => {
      const v = parseFloat(r[col] ?? '');
      return isFinite(v) ? Math.round(v) : undefined;
    };
    return {
      id: r['ID'] ?? '',
      name: r['Name'] ?? '',
      age: n('Age'),
      nationality: r['Nationality'] ?? undefined,
      overall: n('Overall'),
      potential: n('Potential'),
      club: r['Club'] ?? undefined,
      position: r['Position'] ?? undefined,
      jerseyNumber: n('Jersey Number'),
      height: r['Height'] ?? undefined,
      weight: r['Weight'] ?? undefined,
      skills: {
        crossing: n('Crossing'),
        finishing: n('Finishing'),
        dribbling: n('Dribbling'),
        shortPassing: n('ShortPassing'),
        longPassing: n('LongPassing'),
        ballControl: n('BallControl'),
        acceleration: n('Acceleration'),
        sprintSpeed: n('SprintSpeed'),
        agility: n('Agility'),
        reactions: n('Reactions'),
        shotPower: n('ShotPower'),
        jumping: n('Jumping'),
        stamina: n('Stamina'),
        strength: n('Strength'),
        longShots: n('LongShots'),
        aggression: n('Aggression'),
        interceptions: n('Interceptions'),
        positioning: n('Positioning'),
        vision: n('Vision'),
        composure: n('Composure'),
        marking: n('Marking'),
        standingTackle: n('StandingTackle'),
        slidingTackle: n('SlidingTackle'),
        gkDiving: n('GKDiving'),
        gkHandling: n('GKHandling'),
        gkKicking: n('GKKicking'),
        gkReflexes: n('GKReflexes'),
      },
    };
  });
}

// ---------------------------------------------------------------------------
// Singleton database
// ---------------------------------------------------------------------------

let _db: Database | null = null;

/** Load and cache all CSV data. Safe to call multiple times. */
export function getDatabase(): Database {
  if (_db !== null) return _db;

  process.stderr.write('Loading Brazilian soccer datasets...\n');

  const matches: Match[] = [
    ...loadBrasileiraoMatches(),
    ...loadCopaBrasilMatches(),
    ...loadLibertadoresMatches(),
    ...loadBrFootballMatches(),
    ...loadHistoricoMatches(),
  ];

  const players = loadPlayers();

  process.stderr.write(
    `Loaded ${matches.length} matches and ${players.length} players.\n`
  );

  _db = { matches, players };
  return _db;
}

/** Reset the cached database (used in tests). */
export function resetDatabase(): void {
  _db = null;
}
