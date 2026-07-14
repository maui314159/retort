/**
 * Context
 * =======
 * CSV ingestion for the Brazilian Soccer MCP server.
 *
 * Reads the six Kaggle CSVs from data/kaggle/ and normalizes each into the flat
 * `Match` / `Player` shapes (see types.ts). All team names are canonicalized
 * once at load time so query-time matching is a cheap string compare. Files are
 * parsed with csv-parse in `columns: true` mode (header-driven records).
 *
 * The historical Brasileirão file (novo_campeonato_brasileiro.csv) overlaps in
 * years with the ricardomattos05 Brasileirão file (2012-2019). Both are loaded;
 * `dedupeMatches` removes exact duplicates (same competition/date/teams/score)
 * so head-to-head and standings counts are not inflated.
 *
 * Encoding: files are read as UTF-8; the FIFA file carries a BOM on its first
 * column header which csv-parse strips via `bom: true`.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { parse } from 'csv-parse/sync';
import {
  canonicalCompetition,
  canonicalTeam,
  displayTeam,
  parseDate,
  type Competition,
} from './normalize.js';
import type { Match, Player } from './types.js';

/** Default location of the bundled datasets relative to the project root. */
export const DEFAULT_DATA_DIR = 'data/kaggle';

interface LoadResult {
  matches: Match[];
  players: Player[];
}

function toInt(value: unknown): number | undefined {
  if (value === undefined || value === null) return undefined;
  const n = Number(String(value).trim());
  return Number.isFinite(n) ? Math.trunc(n) : undefined;
}

function readCsv(path: string): Record<string, string>[] {
  const text = readFileSync(path, 'utf8');
  return parse(text, {
    columns: true,
    bom: true,
    skip_empty_lines: true,
    relax_column_count: true,
    trim: true,
  }) as Record<string, string>[];
}

function buildMatch(
  competition: Competition,
  rawHome: string,
  rawAway: string,
  homeGoals: number | undefined,
  awayGoals: number | undefined,
  date: string | undefined,
  season: number | undefined,
  round: string | undefined,
  source: string,
): Match | undefined {
  const homeTeam = displayTeam(rawHome);
  const awayTeam = displayTeam(rawAway);
  if (!homeTeam || !awayTeam) return undefined;
  if (homeGoals === undefined || awayGoals === undefined) return undefined;
  return {
    competition,
    date,
    season,
    round,
    homeTeam,
    awayTeam,
    canonicalHome: canonicalTeam(rawHome),
    canonicalAway: canonicalTeam(rawAway),
    homeGoals,
    awayGoals,
    source,
  };
}

/** ricardomattos05 Brasileirão Série A (Brasileirao_Matches.csv). */
function loadBrasileirao(dir: string): Match[] {
  const rows = readCsv(join(dir, 'Brasileirao_Matches.csv'));
  const out: Match[] = [];
  for (const r of rows) {
    const m = buildMatch(
      'Brasileirão Série A',
      r.home_team,
      r.away_team,
      toInt(r.home_goal),
      toInt(r.away_goal),
      parseDate(r.datetime),
      toInt(r.season),
      r.round ? `Round ${r.round}` : undefined,
      'Brasileirao_Matches.csv',
    );
    if (m) out.push(m);
  }
  return out;
}

/** Copa do Brasil (Brazilian_Cup_Matches.csv). */
function loadCup(dir: string): Match[] {
  const rows = readCsv(join(dir, 'Brazilian_Cup_Matches.csv'));
  const out: Match[] = [];
  for (const r of rows) {
    const m = buildMatch(
      'Copa do Brasil',
      r.home_team,
      r.away_team,
      toInt(r.home_goal),
      toInt(r.away_goal),
      parseDate(r.datetime),
      toInt(r.season),
      r.round ? `Round ${r.round}` : undefined,
      'Brazilian_Cup_Matches.csv',
    );
    if (m) out.push(m);
  }
  return out;
}

/** Copa Libertadores (Libertadores_Matches.csv). */
function loadLibertadores(dir: string): Match[] {
  const rows = readCsv(join(dir, 'Libertadores_Matches.csv'));
  const out: Match[] = [];
  for (const r of rows) {
    const m = buildMatch(
      'Copa Libertadores',
      r.home_team,
      r.away_team,
      toInt(r.home_goal),
      toInt(r.away_goal),
      parseDate(r.datetime),
      toInt(r.season),
      r.stage,
      'Libertadores_Matches.csv',
    );
    if (m) out.push(m);
  }
  return out;
}

/**
 * Extended statistics dataset (BR-Football-Dataset.csv). Tournament column maps
 * to Série A/B/C and Copa do Brasil. Rows whose tournament does not map to a
 * known competition are skipped.
 *
 * This file has no explicit season column, so the season is derived from the
 * match date. The Brazilian league season is named for a calendar year but the
 * COVID-delayed 2020 edition ran into January/February 2021; fixtures played in
 * Jan/Feb therefore belong to the *previous* year's season. Applying that rule
 * aligns these rows with the authoritative season-stamped sources so the
 * season-fixture dedupe collapses the overlap instead of leaking phantom teams
 * into the following year's standings.
 */
function loadExtended(dir: string): Match[] {
  const rows = readCsv(join(dir, 'BR-Football-Dataset.csv'));
  const out: Match[] = [];
  for (const r of rows) {
    const competition = canonicalCompetition(r.tournament);
    if (!competition) continue;
    const date = parseDate(r.date);
    let season = date ? toInt(date.slice(0, 4)) : undefined;
    if (season !== undefined && date && Number(date.slice(5, 7)) <= 2) season -= 1;
    const m = buildMatch(
      competition,
      r.home,
      r.away,
      toInt(r.home_goal),
      toInt(r.away_goal),
      date,
      season,
      undefined,
      'BR-Football-Dataset.csv',
    );
    if (m) out.push(m);
  }
  return out;
}

/** Historical Brasileirão 2003-2019 (novo_campeonato_brasileiro.csv). */
function loadHistorical(dir: string): Match[] {
  const rows = readCsv(join(dir, 'novo_campeonato_brasileiro.csv'));
  const out: Match[] = [];
  for (const r of rows) {
    const m = buildMatch(
      'Brasileirão Série A',
      r.Equipe_mandante,
      r.Equipe_visitante,
      toInt(r.Gols_mandante),
      toInt(r.Gols_visitante),
      parseDate(r.Data),
      toInt(r.Ano),
      r.Rodada ? `Round ${r.Rodada}` : undefined,
      'novo_campeonato_brasileiro.csv',
    );
    if (m) out.push(m);
  }
  return out;
}

/** FIFA player database (fifa_data.csv). */
function loadPlayers(dir: string): Player[] {
  const rows = readCsv(join(dir, 'fifa_data.csv'));
  const out: Player[] = [];
  for (const r of rows) {
    const id = toInt(r.ID);
    const name = (r.Name ?? '').trim();
    if (id === undefined || !name) continue;
    const overall = toInt(r.Overall) ?? 0;
    const potential = toInt(r.Potential) ?? overall;
    const club = (r.Club ?? '').trim();
    out.push({
      id,
      name,
      age: toInt(r.Age),
      nationality: (r.Nationality ?? '').trim(),
      overall,
      potential,
      club,
      canonicalClub: canonicalTeam(club),
      position: (r.Position ?? '').trim() || undefined,
      jerseyNumber: toInt(r['Jersey Number']),
      height: (r.Height ?? '').trim() || undefined,
      weight: (r.Weight ?? '').trim() || undefined,
    });
  }
  return out;
}

/**
 * Remove duplicate matches that arise from overlapping datasets.
 *
 * The three Brasileirão-overlapping sources (Brasileirao_Matches,
 * BR-Football-Dataset, novo_campeonato_brasileiro) list the same fixtures with
 * differing dates and occasionally differing scores, so an exact date+score key
 * leaves duplicates that inflate standings and head-to-head counts. The real
 * invariant across all these competitions is: a given ordered (home, away) pair
 * plays at most once per competition per season (two-legged ties and group
 * stages swap home/away, yielding distinct ordered pairs). So when a season is
 * known we key on competition|season|home|away and keep the first occurrence —
 * load order makes the round-annotated Brasileirao_Matches.csv authoritative.
 * When season is absent we fall back to date+score to avoid collapsing genuinely
 * distinct undated rows.
 */
export function dedupeMatches(matches: Match[]): Match[] {
  const seen = new Set<string>();
  const out: Match[] = [];
  for (const m of matches) {
    const key =
      m.season !== undefined
        ? `${m.competition}|${m.season}|${m.canonicalHome}|${m.canonicalAway}`
        : `${m.competition}|${m.date ?? ''}|${m.canonicalHome}|${m.canonicalAway}|${m.homeGoals}-${m.awayGoals}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(m);
  }
  return out;
}

/**
 * Load and normalize all datasets from `dataDir`. Returns deduped matches and
 * the full player list. Throws if a required file is missing or unreadable.
 */
export function loadAll(dataDir: string = DEFAULT_DATA_DIR): LoadResult {
  const matches = dedupeMatches([
    ...loadBrasileirao(dataDir),
    ...loadCup(dataDir),
    ...loadLibertadores(dataDir),
    ...loadExtended(dataDir),
    ...loadHistorical(dataDir),
  ]);
  const players = loadPlayers(dataDir);
  return { matches, players };
}
