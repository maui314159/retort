/**
 * CSV loader: parses the six Kaggle datasets into a single in-memory
 * {@link DatasetSnapshot}.
 *
 * Design notes:
 *   - csv-parse runs in synchronous mode (the files are small enough).
 *   - The FIFA file ships a UTF-8 BOM, so we pass `bom: true`.
 *   - Many numeric cells in the source files are the literal string
 *     "NA" or "N/A"; the helpers {@link parseIntSafe} /
 *     {@link parseDateSafe} coerce those to `null` rather than NaN.
 *   - The `Brasileirao_Matches.csv` rows in 2022 sometimes have the
 *     string "NA" for the goals of the last two rounds of the season
 *     (matches were not played when the dataset was published). Those
 *     rows are kept; downstream queries just treat them as draws of
 *     unknown score.
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { parse } from 'csv-parse/sync';
import type { Competition, DatasetSnapshot, Match, Player } from './types.js';
import { canonicalTeam, stripDiacritics } from './normalizer.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA_DIR = resolve(__dirname, '..', '..', 'data', 'kaggle');

export const DATA_PATHS = {
  brasileirao: resolve(DATA_DIR, 'Brasileirao_Matches.csv'),
  copa: resolve(DATA_DIR, 'Brazilian_Cup_Matches.csv'),
  libertadores: resolve(DATA_DIR, 'Libertadores_Matches.csv'),
  brFootball: resolve(DATA_DIR, 'BR-Football-Dataset.csv'),
  historical: resolve(DATA_DIR, 'novo_campeonato_brasileiro.csv'),
  fifa: resolve(DATA_DIR, 'fifa_data.csv')
} as const;

function readCsv(path: string, opts: Parameters<typeof parse>[1]): Record<string, string>[] {
  const text = readFileSync(path, 'utf8');
  return parse(text, { columns: true, skip_empty_lines: true, ...opts }) as Record<string, string>[];
}

export function parseIntSafe(v: string | undefined | null): number | null {
  if (v === undefined || v === null) return null;
  const s = v.trim();
  if (s === '' || s === 'NA' || s === 'N/A' || s === '-') return null;
  const n = Number(s);
  return Number.isFinite(n) ? Math.trunc(n) : null;
}

export function parseFloatSafe(v: string | undefined | null): number | null {
  if (v === undefined || v === null) return null;
  const s = v.trim();
  if (s === '' || s === 'NA' || s === 'N/A' || s === '-') return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

export function parseDateSafe(raw: string | undefined | null): { date: string; time: string } {
  const empty = { date: '', time: '' };
  if (!raw) return empty;
  const v = raw.trim();
  if (!v || v === 'NA' || v === 'N/A') return empty;

  // ISO with time: "2012-05-19 18:30:00"
  const iso = v.match(/^(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}:\d{2}(?::\d{2})?))?/);
  if (iso) return { date: iso[1], time: iso[2] ?? '' };

  // Brazilian DD/MM/YYYY
  const br = v.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (br) return { date: `${br[3]}-${br[2]}-${br[1]}`, time: '' };

  return empty;
}

function makeId(competition: Competition, season: number, date: string, home: string, away: string): string {
  return `${competition}|${season}|${date}|${home}|${away}`;
}

function winnerOf(homeGoal: number | null, awayGoal: number | null): 'home' | 'away' | 'draw' | undefined {
  if (homeGoal === null || awayGoal === null) return undefined;
  if (homeGoal > awayGoal) return 'home';
  if (homeGoal < awayGoal) return 'away';
  return 'draw';
}

function loadBrasileirao(): Match[] {
  const rows = readCsv(DATA_PATHS.brasileirao, {});
  return rows
    .filter(r => r.datetime && r.home_team)
    .map(r => {
      const { date, time } = parseDateSafe(r.datetime);
      const homeGoal = parseIntSafe(r.home_goal);
      const awayGoal = parseIntSafe(r.away_goal);
      const homeTeam = canonicalTeam(r.home_team);
      const awayTeam = canonicalTeam(r.away_team);
      return {
        id: makeId('brasileirao', Number(r.season), date, homeTeam, awayTeam),
        competition: 'brasileirao' as Competition,
        season: Number(r.season),
        round: r.round,
        date,
        time,
        homeTeam,
        awayTeam,
        homeGoal,
        awayGoal,
        homeState: r.home_team_state || undefined,
        awayState: r.away_team_state || undefined,
        winner: winnerOf(homeGoal, awayGoal)
      } satisfies Match;
    });
}

function loadCopa(): Match[] {
  const rows = readCsv(DATA_PATHS.copa, {});
  return rows
    .filter(r => r.datetime && r.home_team)
    .map(r => {
      const { date, time } = parseDateSafe(r.datetime);
      const homeGoal = parseIntSafe(r.home_goal);
      const awayGoal = parseIntSafe(r.away_goal);
      const homeTeam = canonicalTeam(r.home_team);
      const awayTeam = canonicalTeam(r.away_team);
      return {
        id: makeId('copa_do_brasil', Number(r.season), date, homeTeam, awayTeam),
        competition: 'copa_do_brasil',
        season: Number(r.season),
        round: (r.round ?? '').replace(/^"|"$/g, ''),
        date,
        time,
        homeTeam,
        awayTeam,
        homeGoal,
        awayGoal,
        winner: winnerOf(homeGoal, awayGoal)
      } satisfies Match;
    });
}

function loadLibertadores(): Match[] {
  const rows = readCsv(DATA_PATHS.libertadores, {});
  return rows
    .filter(r => r.datetime && r.home_team)
    .map(r => {
      const { date, time } = parseDateSafe(r.datetime);
      const homeGoal = parseIntSafe(r.home_goal);
      const awayGoal = parseIntSafe(r.away_goal);
      const homeTeam = canonicalTeam(r.home_team);
      const awayTeam = canonicalTeam(r.away_team);
      return {
        id: makeId('libertadores', Number(r.season), date, homeTeam, awayTeam),
        competition: 'libertadores',
        season: Number(r.season),
        round: r.stage ?? '',
        date,
        time,
        homeTeam,
        awayTeam,
        homeGoal,
        awayGoal,
        stage: r.stage || undefined,
        winner: winnerOf(homeGoal, awayGoal)
      } satisfies Match;
    });
}

/**
 * The BR-Football-Dataset row uses `tournament` to discriminate by
 * competition. We bucket rows into our competition ids based on it.
 */
function loadBrFootball(): Match[] {
  const rows = readCsv(DATA_PATHS.brFootball, {});
  const out: Match[] = [];
  for (const r of rows) {
    if (!r.home || !r.away || !r.date) continue;
    const { date, time } = parseDateSafe(r.date);
    if (!date) continue;
    const homeGoal = parseIntSafe(r.home_goal);
    const awayGoal = parseIntSafe(r.away_goal);
    const homeTeam = canonicalTeam(r.home);
    const awayTeam = canonicalTeam(r.away);
    const tournament = (r.tournament || '').toLowerCase();
    let competition: Competition;
    if (tournament.includes('libertadores')) competition = 'libertadores';
    else if (tournament.includes('copa do brasil')) competition = 'copa_do_brasil';
    else if (tournament.includes('serie a')) competition = 'brasileirao';
    else continue; // Serie B/C/lower divisions are kept in the source but not indexed as a competition.
    out.push({
      id: makeId('br_football', date.slice(0, 4) ? Number(date.slice(0, 4)) : 0, date, homeTeam, awayTeam),
      competition,
      season: date ? Number(date.slice(0, 4)) : 0,
      round: tournament,
      date,
      time,
      homeTeam,
      awayTeam,
      homeGoal,
      awayGoal,
      homeCorners: parseIntSafe(r.home_corner),
      awayCorners: parseIntSafe(r.away_corner),
      homeShots: parseIntSafe(r.home_shots),
      awayShots: parseIntSafe(r.away_shots),
      homeAttacks: parseIntSafe(r.home_attack),
      awayAttacks: parseIntSafe(r.away_attack),
      halfTimeHome: parseIntSafe(r.ht_result),
      halfTimeAway: parseIntSafe(r.at_result),
      winner: winnerOf(homeGoal, awayGoal)
    } satisfies Match);
  }
  return out;
}

function loadHistorical(): Match[] {
  const rows = readCsv(DATA_PATHS.historical, {});
  return rows
    .filter(r => r.Data && r.Equipe_mandante)
    .map(r => {
      const { date, time } = parseDateSafe(r.Data);
      const homeGoal = parseIntSafe(r.Gols_mandante);
      const awayGoal = parseIntSafe(r.Gols_visitante);
      const homeTeam = canonicalTeam(r.Equipe_mandante);
      const awayTeam = canonicalTeam(r.Equipe_visitante);
      const winnerRaw = (r.Vencedor || '').toLowerCase();
      const winner: 'home' | 'away' | 'draw' | undefined =
        winnerRaw === 'mandante' ? 'home' :
        winnerRaw === 'visitante' ? 'away' :
        winnerRaw === 'empate' ? 'draw' :
        winnerOf(homeGoal, awayGoal);
      return {
        id: makeId('brasileirao_historical', Number(r.Ano), date, homeTeam, awayTeam),
        competition: 'brasileirao_historical',
        season: Number(r.Ano),
        round: String(r.Rodada ?? ''),
        date,
        time,
        homeTeam,
        awayTeam,
        homeGoal,
        awayGoal,
        homeState: r.Mandante_UF || undefined,
        awayState: r.Visitante_UF || undefined,
        stadium: r.Arena || undefined,
        winner
      } satisfies Match;
    });
}

function loadFifa(): Player[] {
  const rows = readCsv(DATA_PATHS.fifa, { bom: true });
  const out: Player[] = [];
  for (const r of rows) {
    const id = parseIntSafe(r.ID);
    if (id === null) continue;
    out.push({
      id,
      name: r.Name ?? '',
      age: parseIntSafe(r.Age),
      nationality: r.Nationality ?? '',
      overall: parseIntSafe(r.Overall),
      potential: parseIntSafe(r.Potential),
      club: canonicalTeam(r.Club ?? ''),
      position: r.Position ?? '',
      jerseyNumber: parseIntSafe(r['Jersey Number']),
      height: r.Height ?? '',
      weight: r.Weight ?? '',
      preferredFoot: r['Preferred Foot'] ?? '',
      value: r.Value ?? '',
      wage: r.Wage ?? ''
    });
  }
  return out;
}

/**
 * Build the alias map: canonical name -> sorted unique raw variants.
 */
function buildTeamAliases(matches: Match[], players: Player[]): { teams: string[]; aliases: Map<string, string[]> } {
  const aliases = new Map<string, Set<string>>();
  for (const m of matches) {
    if (m.homeTeam) {
      if (!aliases.has(m.homeTeam)) aliases.set(m.homeTeam, new Set());
      aliases.get(m.homeTeam)!.add(m.homeTeam);
    }
    if (m.awayTeam) {
      if (!aliases.has(m.awayTeam)) aliases.set(m.awayTeam, new Set());
      aliases.get(m.awayTeam)!.add(m.awayTeam);
    }
  }
  for (const p of players) {
    if (!p.club) continue;
    const canon = stripDiacritics(p.club).toLowerCase();
    let resolved = '';
    for (const k of aliases.keys()) {
      if (stripDiacritics(k).toLowerCase() === canon) { resolved = k; break; }
    }
    if (!resolved) {
      aliases.set(p.club, new Set([p.club]));
      resolved = p.club;
    } else {
      aliases.get(resolved)!.add(p.club);
    }
  }
  const teams = [...aliases.keys()].sort();
  return { teams, aliases: new Map([...aliases.entries()].map(([k, v]) => [k, [...v].sort()])) };
}

let _cache: DatasetSnapshot | undefined;

/**
 * Load (and cache) the entire dataset. The CSVs are small enough that
 * we keep them in memory.
 */
export function loadDataset(): DatasetSnapshot {
  if (_cache) return _cache;
  const matches: Match[] = [
    ...loadBrasileirao(),
    ...loadCopa(),
    ...loadLibertadores(),
    ...loadBrFootball(),
    ...loadHistorical()
  ];
  const players = loadFifa();
  const { teams, aliases } = buildTeamAliases(matches, players);
  _cache = { matches, players, teams, teamAliases: aliases };
  return _cache;
}
