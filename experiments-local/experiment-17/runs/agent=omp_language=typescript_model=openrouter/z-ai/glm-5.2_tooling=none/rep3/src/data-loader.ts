/**
 * brazilian-soccer-mcp / src/data-loader.ts
 *
 * CSV ingestion and normalization.
 *
 * Context block:
 * Loads the six Kaggle datasets from `data/kaggle/` and reduces each to the
 * normalized `Match` / `Player` shapes defined in types.ts. Handles the three
 * different date formats in the data (ISO with optional time, and Brazilian
 * DD/MM/YYYY), the team-name variations (cleaned via team-normalizer), the
 * BOM-prefixed FIFA CSV header, and the float-formatted goals in the extended
 * stats file. Loading is cached: the datasets are parsed once per process and
 * reused across all MCP tool calls.
 */

import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse } from 'csv-parse/sync';
import type { Match, Player } from './types.js';
import { cleanTeamName, teamKey, foldAccents } from './team-normalizer.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA_DIR = join(__dirname, '..', 'data', 'kaggle');

let cachedMatches: Match[] | null = null;
let cachedPlayers: Player[] | null = null;

/** Parse a date string in any of the dataset's formats; returns null if unparseable. */
export function parseDate(raw: string | null | undefined): Date | null {
  if (!raw) return null;
  const s = raw.trim();
  if (!s) return null;
  // ISO: 2023-09-24 or 2023-09-24 20:00:00
  const iso = s.match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?$/);
  if (iso) {
    const [, y, mo, d, h = '0', mi = '0', se = '0'] = iso;
    return new Date(Date.UTC(+y, +mo - 1, +d, +h, +mi, +se));
  }
  // Brazilian: 29/03/2003
  const br = s.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (br) {
    const [, d, mo, y] = br;
    return new Date(Date.UTC(+y, +mo - 1, +d));
  }
  return null;
}

/** Parse a possibly-empty numeric field (handles "1", "1.0", ""). */
function num(v: unknown): number | null {
  if (v === null || v === undefined) return null;
  const s = String(v).trim();
  if (s === '' || s === 'NaN') return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

function intOrNull(v: unknown): number | null {
  const n = num(v);
  return n === null ? null : Math.trunc(n);
}

/** Normalize a competition label to the canonical Portuguese form. */
function normalizeCompetition(label: string): string {
  const t = label.trim();
  const lower = t.toLowerCase();
  if (lower === 'serie a') return 'Brasileirão Série A';
  if (lower === 'serie b') return 'Brasileirão Série B';
  if (lower === 'serie c') return 'Brasileirão Série C';
  if (lower === 'copa do brasil') return 'Copa do Brasil';
  return t;
}

/** Competition key for partial matching. */
export function competitionKey(comp: string): string {
  return foldAccents(comp).toLowerCase().trim();
}

function readCsv(file: string): Record<string, string>[] {
  const path = join(DATA_DIR, file);
  const content = readFileSync(path, 'utf8');
  return parse(content, {
    columns: true,
    skip_empty_lines: true,
    bom: true,
    relax_column_count: true,
    trim: true,
  }) as Record<string, string>[];
}

function pick(rec: Record<string, string>, ...keys: string[]): string | undefined {
  for (const k of keys) {
    if (k in rec && rec[k] !== undefined && rec[k] !== '') return rec[k];
  }
  return undefined;
}

/** Load and normalize all match records from the five match CSV files. */
export function loadMatches(): Match[] {
  if (cachedMatches) return cachedMatches;
  const out: Match[] = [];
  let lineCounter = 0;

  const push = (
    source: string,
    competition: string,
    seasonRaw: string | undefined,
    dateRaw: string | undefined,
    homeRaw: string,
    awayRaw: string,
    hg: number | null,
    ag: number | null,
    round: string | null,
    stage: string | null,
    venue: string | null,
    ext?: Partial<Match>,
  ) => {
    lineCounter++;
    out.push({
      id: `${source}:${lineCounter}`,
      source,
      competition,
      season: seasonRaw ? intOrNull(seasonRaw) : null,
      date: parseDate(dateRaw),
      dateRaw: dateRaw ?? '',
      homeTeam: cleanTeamName(homeRaw),
      awayTeam: cleanTeamName(awayRaw),
      homeTeamKey: teamKey(homeRaw),
      awayTeamKey: teamKey(awayRaw),
      homeGoals: hg,
      awayGoals: ag,
      round,
      stage,
      venue,
      htHomeResult: ext?.htHomeResult ?? null,
      homeCorners: ext?.homeCorners ?? null,
      awayCorners: ext?.awayCorners ?? null,
      homeShots: ext?.homeShots ?? null,
      awayShots: ext?.awayShots ?? null,
      homeAttacks: ext?.homeAttacks ?? null,
      awayAttacks: ext?.awayAttacks ?? null,
    });
  };

  // 1. Brasileirão Serie A matches.
  for (const r of readCsv('Brasileirao_Matches.csv')) {
    push(
      'Brasileirao_Matches.csv',
      'Brasileirão',
      pick(r, 'season'),
      pick(r, 'datetime'),
      pick(r, 'home_team') ?? '',
      pick(r, 'away_team') ?? '',
      num(pick(r, 'home_goal')),
      num(pick(r, 'away_goal')),
      pick(r, 'round') ?? null,
      null,
      null,
    );
  }

  // 2. Copa do Brasil.
  for (const r of readCsv('Brazilian_Cup_Matches.csv')) {
    push(
      'Brazilian_Cup_Matches.csv',
      'Copa do Brasil',
      pick(r, 'season'),
      pick(r, 'datetime'),
      pick(r, 'home_team') ?? '',
      pick(r, 'away_team') ?? '',
      num(pick(r, 'home_goal')),
      num(pick(r, 'away_goal')),
      pick(r, 'round') ?? null,
      null,
      null,
    );
  }

  // 3. Copa Libertadores.
  for (const r of readCsv('Libertadores_Matches.csv')) {
    push(
      'Libertadores_Matches.csv',
      'Libertadores',
      pick(r, 'season'),
      pick(r, 'datetime'),
      pick(r, 'home_team') ?? '',
      pick(r, 'away_team') ?? '',
      num(pick(r, 'home_goal')),
      num(pick(r, 'away_goal')),
      null,
      pick(r, 'stage') ?? null,
      null,
    );
  }

  // 4. Extended statistics dataset (BR-Football-Dataset).
  for (const r of readCsv('BR-Football-Dataset.csv')) {
    push(
      'BR-Football-Dataset.csv',
      normalizeCompetition(pick(r, 'tournament') ?? ''),
      // Season derived from the date's year.
      pick(r, 'date')?.slice(0, 4),
      pick(r, 'date'),
      pick(r, 'home') ?? '',
      pick(r, 'away') ?? '',
      num(pick(r, 'home_goal')),
      num(pick(r, 'away_goal')),
      null,
      null,
      null,
      {
        homeCorners: num(pick(r, 'home_corner')),
        awayCorners: num(pick(r, 'away_corner')),
        homeShots: num(pick(r, 'home_shots')),
        awayShots: num(pick(r, 'away_shots')),
        homeAttacks: num(pick(r, 'home_attack')),
        awayAttacks: num(pick(r, 'away_attack')),
        htHomeResult: pick(r, 'ht_result') ?? null,
      },
    );
  }

  // 5. Historical Brasileirão 2003-2019.
  for (const r of readCsv('novo_campeonato_brasileiro.csv')) {
    push(
      'novo_campeonato_brasileiro.csv',
      'Brasileirão',
      pick(r, 'Ano'),
      pick(r, 'Data'),
      pick(r, 'Equipe_mandante') ?? '',
      pick(r, 'Equipe_visitante') ?? '',
      num(pick(r, 'Gols_mandante')),
      num(pick(r, 'Gols_visitante')),
      pick(r, 'Rodada') ?? null,
      null,
      pick(r, 'Arena') ?? null,
    );
  }

  cachedMatches = out;
  return out;
}

/** Load and normalize player records from the FIFA player CSV. */
export function loadPlayers(): Player[] {
  if (cachedPlayers) return cachedPlayers;
  const out: Player[] = [];
  for (const r of readCsv('fifa_data.csv')) {
    const name = pick(r, 'Name') ?? '';
    if (!name) continue;
    const club = pick(r, 'Club') ?? '';
    out.push({
      id: intOrNull(pick(r, 'ID')) ?? 0,
      name,
      age: intOrNull(pick(r, 'Age')),
      nationality: pick(r, 'Nationality') ?? '',
      overall: intOrNull(pick(r, 'Overall')),
      potential: intOrNull(pick(r, 'Potential')),
      club,
      position: pick(r, 'Position') ?? '',
      jerseyNumber: intOrNull(pick(r, 'Jersey Number')),
      height: pick(r, 'Height') ?? '',
      weight: pick(r, 'Weight') ?? '',
      preferredFoot: pick(r, 'Preferred Foot') ?? '',
      clubKey: club ? foldAccents(club).toLowerCase().trim() : '',
      nationalityKey: foldAccents(pick(r, 'Nationality') ?? '').toLowerCase().trim(),
      crossing: intOrNull(pick(r, 'Crossing')),
      finishing: intOrNull(pick(r, 'Finishing')),
      dribbling: intOrNull(pick(r, 'Dribbling')),
      shortPassing: intOrNull(pick(r, 'ShortPassing')),
      longShots: intOrNull(pick(r, 'LongShots')),
      shotPower: intOrNull(pick(r, 'ShotPower')),
      stamina: intOrNull(pick(r, 'Stamina')),
      aggression: intOrNull(pick(r, 'Aggression')),
    });
  }
  cachedPlayers = out;
  return out;
}

/** Reset the in-memory cache (useful for tests). */
export function resetCache(): void {
  cachedMatches = null;
  cachedPlayers = null;
}
