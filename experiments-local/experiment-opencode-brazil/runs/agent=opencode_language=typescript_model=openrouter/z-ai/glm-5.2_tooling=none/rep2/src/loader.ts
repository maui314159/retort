/**
 * CSV dataset loader.
 *
 * Reads the six Kaggle CSV files from `data/kaggle/` and produces a unified
 * {@link Dataset} of normalized {@link Match} and {@link Player} records.
 * All file/format-specific logic lives here so the rest of the codebase can
 * work against a single schema.
 *
 * Loading is a two-pass process:
 *   1. Parse every CSV row into an intermediate raw record (preserving the
 *      original team-name strings and any state/UF columns).
 *   2. Build a {@link TeamNameRegistry} from those raw names so that the
 *      state suffix is kept only for ambiguous base names (e.g. "Atletico-MG"
 *      vs "Atletico-PR"), then emit canonical {@link Match} records.
 */

import fs from 'node:fs';
import path from 'node:path';
import Papa from 'papaparse';
import type {
  Dataset,
  Match,
  Player,
  PlayerSkills,
  MatchStats,
  Competition,
} from './types.js';
import {
  TeamNameRegistry,
  parseDate,
  parseGoals,
  parseSeason,
} from './normalize.js';

const DEFAULT_DATA_DIR = path.resolve(process.cwd(), 'data/kaggle');

/** Read & parse a CSV file into an array of row objects. */
function readCsv(filePath: string): Record<string, string>[] {
  const content = fs.readFileSync(filePath, 'utf8');
  const result = Papa.parse<Record<string, string>>(content, {
    header: true,
    skipEmptyLines: true,
    dynamicTyping: false,
    transformHeader: (h) => h.trim(),
  });
  return (result.data as Record<string, string>[]).filter(
    (r) => r && Object.keys(r).length > 0,
  );
}

function num(v: string | undefined): number | undefined {
  if (v == null || v === '') return undefined;
  const n = Number(v);
  return Number.isFinite(n) ? n : undefined;
}

/** Intermediate raw match record (pre-normalization). */
interface RawMatch {
  competition: Competition;
  stage?: string;
  rawDate: string;
  homeRaw: string;
  awayRaw: string;
  homeState?: string;
  awayState?: string;
  homeGoal: number | null;
  awayGoal: number | null;
  season?: number;
  round?: string | number;
  arena?: string;
  stats?: MatchStats;
}

function parseBrasileirao(rows: Record<string, string>[]): RawMatch[] {
  return rows.map((r): RawMatch => ({
    competition: 'Brasileirao',
    rawDate: r['datetime'] ?? '',
    homeRaw: r['home_team'] ?? '',
    awayRaw: r['away_team'] ?? '',
    homeState: r['home_team_state'] || undefined,
    awayState: r['away_team_state'] || undefined,
    homeGoal: parseGoals(r['home_goal']),
    awayGoal: parseGoals(r['away_goal']),
    season: parseSeason(r['season']),
    round: num(r['round']),
  }));
}

function parseCopaDoBrasil(rows: Record<string, string>[]): RawMatch[] {
  return rows.map((r): RawMatch => ({
    competition: 'Copa do Brasil',
    stage: r['round'] || undefined,
    rawDate: r['datetime'] ?? '',
    homeRaw: r['home_team'] ?? '',
    awayRaw: r['away_team'] ?? '',
    homeGoal: parseGoals(r['home_goal']),
    awayGoal: parseGoals(r['away_goal']),
    season: parseSeason(r['season']),
  }));
}

function parseLibertadores(rows: Record<string, string>[]): RawMatch[] {
  return rows.map((r): RawMatch => ({
    competition: 'Libertadores',
    stage: r['stage'] || undefined,
    rawDate: r['datetime'] ?? '',
    homeRaw: r['home_team'] ?? '',
    awayRaw: r['away_team'] ?? '',
    homeGoal: parseGoals(r['home_goal']),
    awayGoal: parseGoals(r['away_goal']),
    season: parseSeason(r['season']),
  }));
}

function parseBRFootball(rows: Record<string, string>[]): RawMatch[] {
  return rows.map((r): RawMatch => {
    const stats: MatchStats = {
      homeCorner: num(r['home_corner']),
      awayCorner: num(r['away_corner']),
      homeAttack: num(r['home_attack']),
      awayAttack: num(r['away_attack']),
      homeShots: num(r['home_shots']),
      awayShots: num(r['away_shots']),
      totalCorners: num(r['total_corners']),
      htResult: r['ht_result'] || undefined,
      atResult: r['at_result'] || undefined,
      time: r['time'] || undefined,
    };
    const dateStr = r['date'] ?? '';
    const iso = parseDate(dateStr);
    return {
      competition: 'BR-Football',
      stage: r['tournament'] || undefined,
      rawDate: dateStr,
      homeRaw: r['home'] ?? '',
      awayRaw: r['away'] ?? '',
      homeGoal: parseGoals(r['home_goal']),
      awayGoal: parseGoals(r['away_goal']),
      season: iso ? parseInt(iso.slice(0, 4), 10) : undefined,
      stats,
    };
  });
}

function parseHistorical(rows: Record<string, string>[]): RawMatch[] {
  return rows.map((r): RawMatch => ({
    competition: 'Historical Brasileirao',
    rawDate: r['Data'] ?? '',
    homeRaw: r['Equipe_mandante'] ?? '',
    awayRaw: r['Equipe_visitante'] ?? '',
    homeState: r['Mandante_UF'] || undefined,
    awayState: r['Visitante_UF'] || undefined,
    homeGoal: parseGoals(r['Gols_mandante']),
    awayGoal: parseGoals(r['Gols_visitante']),
    season: parseSeason(r['Ano']),
    round: num(r['Rodada']),
    arena: r['Arena'] || undefined,
  }));
}

/** Build a team-name registry from all raw matches. */
function buildRegistry(raws: RawMatch[]): TeamNameRegistry {
  const reg = new TeamNameRegistry();
  for (const r of raws) {
    reg.register(r.homeRaw, r.homeState);
    reg.register(r.awayRaw, r.awayState);
  }
  reg.finalize();
  return reg;
}

/** Convert raw matches into normalized Matches using the registry. */
function finalizeMatches(raws: RawMatch[], reg: TeamNameRegistry): Match[] {
  return raws.map((r): Match => ({
    competition: r.competition,
    stage: r.stage,
    date: parseDate(r.rawDate),
    rawDate: r.rawDate,
    homeTeam: reg.canonical(r.homeRaw, r.homeState),
    awayTeam: reg.canonical(r.awayRaw, r.awayState),
    homeState: r.homeState,
    awayState: r.awayState,
    homeGoal: r.homeGoal,
    awayGoal: r.awayGoal,
    season: r.season,
    round: r.round,
    arena: r.arena,
    stats: r.stats,
  }));
}

/** Load FIFA player records. */
function loadPlayers(dir: string): Player[] {
  const rows = readCsv(path.join(dir, 'fifa_data.csv'));
  return rows.map((r): Player => {
    const skills: PlayerSkills = {
      crossing: num(r['Crossing']),
      finishing: num(r['Finishing']),
      dribbling: num(r['Dribbling']),
      shortPassing: num(r['ShortPassing']),
      longPassing: num(r['LongPassing']),
      ballControl: num(r['BallControl']),
      shotPower: num(r['ShotPower']),
      stamina: num(r['Stamina']),
      strength: num(r['Strength']),
      vision: num(r['Vision']),
      penalties: num(r['Penalties']),
      standingTackle: num(r['StandingTackle']),
      slidingTackle: num(r['SlidingTackle']),
    };
    return {
      id: num(r['ID']) ?? -1,
      name: (r['Name'] ?? '').trim(),
      age: num(r['Age']),
      nationality: (r['Nationality'] ?? '').trim() || undefined,
      overall: num(r['Overall']),
      potential: num(r['Potential']),
      club: (r['Club'] ?? '').trim() || undefined,
      position: (r['Position'] ?? '').trim() || undefined,
      jerseyNumber: num(r['Jersey Number']),
      height: (r['Height'] ?? '').trim() || undefined,
      weight: (r['Weight'] ?? '').trim() || undefined,
      preferredFoot: (r['Preferred Foot'] ?? '').trim() || undefined,
      skills,
    };
  });
}

/** Load the full dataset from `dir` (defaults to ./data/kaggle). */
export function loadDataset(dir: string = DEFAULT_DATA_DIR): Dataset {
  const raws: RawMatch[] = [
    ...parseBrasileirao(readCsv(path.join(dir, 'Brasileirao_Matches.csv'))),
    ...parseCopaDoBrasil(readCsv(path.join(dir, 'Brazilian_Cup_Matches.csv'))),
    ...parseLibertadores(readCsv(path.join(dir, 'Libertadores_Matches.csv'))),
    ...parseBRFootball(readCsv(path.join(dir, 'BR-Football-Dataset.csv'))),
    ...parseHistorical(readCsv(path.join(dir, 'novo_campeonato_brasileiro.csv'))),
  ];
  const reg = buildRegistry(raws);
  const matches = finalizeMatches(raws, reg);
  const players = loadPlayers(dir);
  return { matches, players };
}

/** Resolve the data directory, honoring the BR_SOCCER_DATA_DIR env var. */
export function resolveDataDir(override?: string): string {
  if (override) return path.resolve(override);
  const env = process.env.BR_SOCCER_DATA_DIR;
  return env ? path.resolve(env) : DEFAULT_DATA_DIR;
}
