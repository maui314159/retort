/**
 * Brazilian Soccer MCP Server — data loader
 * ==========================================
 * Context block:
 *   Loads the six Kaggle CSV files from `data/kaggle/` into normalized
 *   `MatchRecord[]` and `PlayerRecord[]` collections on first use. Each source
 *   file is mapped to the canonical record shape defined in `src/types.ts`
 *   using the helpers in `src/normalize.ts` (team normalization + date parsing).
 *
 *   Files handled:
 *     1. Brasileirao_Matches.csv        -> Brasileirão (Série A, 2012-2022)
 *     2. Brazilian_Cup_Matches.csv     -> Copa do Brasil
 *     3. Libertadores_Matches.csv       -> Libertadores
 *     4. BR-Football-Dataset.csv        -> Serie A/B/C + Copa do Brasil (stats)
 *     5. novo_campeonato_brasileiro.csv -> Historical Brasileirão (2003-2019)
 *     6. fifa_data.csv                  -> FIFA player database
 *
 *   Loading is cached per-process via a module-level singleton so repeated
 *   MCP tool invocations pay the parse cost only once.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { dirname } from 'node:path';
import { parse } from 'csv-parse/sync';

import {
  COMPETITIONS,
  normalizeTeam,
  parseDate,
  toInt,
  toNum,
} from './normalize.js';
import type { MatchRecord, PlayerRecord } from './types.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

/** Resolve the data directory relative to the project root. */
function dataDir(): string {
  // Compiled output lives at <root>/dist/src; data/ is at the project root.
  const root = join(__dirname, '..', '..');
  return join(root, 'data', 'kaggle');
}

function readCsv(path: string): Record<string, string>[] {
  const content = readFileSync(path, 'utf-8');
  return parse(content, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    bom: true,
    relax_column_count: true,
    relax_quotes: true,
  }) as Record<string, string>[];
}

/** Parse Brasileirao_Matches.csv (with state suffixes). */
function loadBrasileirao(dir: string): MatchRecord[] {
  const rows = readCsv(join(dir, 'Brasileirao_Matches.csv'));
  return rows.map((r): MatchRecord => {
    const home = normalizeTeam(r['home_team'] ?? '');
    const away = normalizeTeam(r['away_team'] ?? '');
    const { date, iso } = parseDate(r['datetime'] ?? '');
    return {
      dateStr: iso ?? r['datetime'] ?? '',
      date,
      home: home.display,
      away: away.display,
      homeKey: home.key,
      awayKey: away.key,
      homeState: home.state,
      awayState: away.state,
      homeGoal: toInt(r['home_goal']),
      awayGoal: toInt(r['away_goal']),
      season: toInt(r['season']),
      competition: COMPETITIONS.BRASILEIRAO,
      source: 'Brasileirao_Matches',
      round: r['round'] ?? undefined,
    };
  });
}

/** Parse Brazilian_Cup_Matches.csv. */
function loadCup(dir: string): MatchRecord[] {
  const rows = readCsv(join(dir, 'Brazilian_Cup_Matches.csv'));
  return rows.map((r): MatchRecord => {
    const home = normalizeTeam(r['home_team'] ?? '');
    const away = normalizeTeam(r['away_team'] ?? '');
    const { date, iso } = parseDate(r['datetime'] ?? '');
    return {
      dateStr: iso ?? r['datetime'] ?? '',
      date,
      home: home.display,
      away: away.display,
      homeKey: home.key,
      awayKey: away.key,
      homeState: home.state,
      awayState: away.state,
      homeGoal: toInt(r['home_goal']),
      awayGoal: toInt(r['away_goal']),
      season: toInt(r['season']),
      competition: COMPETITIONS.COPA_DO_BRASIL,
      source: 'Brazilian_Cup_Matches',
      round: r['round'] ?? undefined,
    };
  });
}

/** Parse Libertadores_Matches.csv. */
function loadLibertadores(dir: string): MatchRecord[] {
  const rows = readCsv(join(dir, 'Libertadores_Matches.csv'));
  return rows.map((r): MatchRecord => {
    const home = normalizeTeam(r['home_team'] ?? '');
    const away = normalizeTeam(r['away_team'] ?? '');
    const { date, iso } = parseDate(r['datetime'] ?? '');
    return {
      dateStr: iso ?? r['datetime'] ?? '',
      date,
      home: home.display,
      away: away.display,
      homeKey: home.key,
      awayKey: away.key,
      homeState: home.state,
      awayState: away.state,
      homeGoal: toInt(r['home_goal']),
      awayGoal: toInt(r['away_goal']),
      season: toInt(r['season']),
      competition: COMPETITIONS.LIBERTADORES,
      source: 'Libertadores_Matches',
      stage: r['stage'] ?? undefined,
    };
  });
}

/** Parse BR-Football-Dataset.csv (extended stats, floats for goals). */
function loadBrFootball(dir: string): MatchRecord[] {
  const rows = readCsv(join(dir, 'BR-Football-Dataset.csv'));
  return rows.map((r): MatchRecord => {
    const home = normalizeTeam(r['home'] ?? '');
    const away = normalizeTeam(r['away'] ?? '');
    const { date, iso } = parseDate(r['date'] ?? '');
    let competition: string;
    const t = (r['tournament'] ?? '').toLowerCase();
    if (t.includes('copa')) competition = COMPETITIONS.COPA_DO_BRASIL;
    else if (t.includes('serie c') || t.includes('série c')) competition = COMPETITIONS.SERIE_C;
    else if (t.includes('serie b') || t.includes('série b')) competition = COMPETITIONS.SERIE_B;
    else competition = COMPETITIONS.BRASILEIRAO; // "Serie A" and anything else.
    return {
      dateStr: iso ?? r['date'] ?? '',
      date,
      home: home.display,
      away: away.display,
      homeKey: home.key,
      awayKey: away.key,
      homeState: home.state,
      awayState: away.state,
      homeGoal: toNum(r['home_goal']),
      awayGoal: toNum(r['away_goal']),
      season: date ? date.getUTCFullYear() : null,
      competition,
      source: 'BR-Football-Dataset',
      homeCorner: toNum(r['home_corner']),
      awayCorner: toNum(r['away_corner']),
      homeShots: toNum(r['home_shots']),
      awayShots: toNum(r['away_shots']),
      homeAttack: toNum(r['home_attack']),
      awayAttack: toNum(r['away_attack']),
      htResult: r['ht_result'] ?? undefined,
      atResult: r['at_result'] ?? undefined,
      totalCorners: toNum(r['total_corners']),
    };
  });
}

/** Parse novo_campeonato_brasileiro.csv (2003-2019, Portuguese columns). */
function loadHistorical(dir: string): MatchRecord[] {
  const rows = readCsv(join(dir, 'novo_campeonato_brasileiro.csv'));
  return rows.map((r): MatchRecord => {
    const home = normalizeTeam(r['Equipe_mandante'] ?? '');
    const away = normalizeTeam(r['Equipe_visitante'] ?? '');
    const { date, iso } = parseDate(r['Data'] ?? '');
    const winner = r['Vencedor'] ?? '';
    return {
      dateStr: iso ?? r['Data'] ?? '',
      date,
      home: home.display,
      away: away.display,
      homeKey: home.key,
      awayKey: away.key,
      homeState: r['Mandante_UF'] ?? home.state,
      awayState: r['Visitante_UF'] ?? away.state,
      homeGoal: toInt(r['Gols_mandante']),
      awayGoal: toInt(r['Gols_visitante']),
      season: toInt(r['Ano']),
      competition: COMPETITIONS.BRASILEIRAO,
      source: 'novo_campeonato_brasileiro',
      round: r['Rodada'] ?? undefined,
      arena: r['Arena'] ?? undefined,
      winner: winner || undefined,
    };
  });
}

/** Parse fifa_data.csv. The file ships with a BOM; csv-parse `bom:true` strips it. */
function loadPlayers(dir: string): PlayerRecord[] {
  const rows = readCsv(join(dir, 'fifa_data.csv'));
  return rows.map((r): PlayerRecord => ({
    id: r['ID'] ?? '',
    name: r['Name'] ?? '',
    age: toInt(r['Age']),
    nationality: r['Nationality'] ?? '',
    overall: toInt(r['Overall']),
    potential: toInt(r['Potential']),
    club: r['Club'] ?? '',
    position: r['Position'] ?? '',
    jerseyNumber: r['Jersey Number'] ?? '',
    height: r['Height'] ?? '',
    weight: r['Weight'] ?? '',
    preferredFoot: r['Preferred Foot'] ?? '',
    raw: r,
  }));
}

interface LoadedData {
  matches: MatchRecord[];
  players: PlayerRecord[];
}

let cached: LoadedData | null = null;

/** Load and cache all datasets. Subsequent calls return the cached result. */
export function loadData(dirOverride?: string): LoadedData {
  if (cached && !dirOverride) return cached;
  const dir = dirOverride ?? dataDir();
  const matches: MatchRecord[] = [
    ...loadBrasileirao(dir),
    ...loadCup(dir),
    ...loadLibertadores(dir),
    ...loadBrFootball(dir),
    ...loadHistorical(dir),
  ];
  const players = loadPlayers(dir);
  const result = { matches, players };
  if (!dirOverride) cached = result;
  return result;
}

/** Reset the cache — used by tests that load a fixture directory. */
export function resetCache(): void {
  cached = null;
}
