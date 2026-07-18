/**
 * brazilian-soccer-mcp — CSV loaders
 *
 * Context block
 * ============
 * See src/types.ts for the top-level project context block.
 *
 * Each loader reads one of the six Kaggle CSVs and maps its source-specific
 * column names into the canonical `MatchRecord` / `PlayerRecord` shapes.
 * Loaders are independent and total: a malformed row is mapped to the best
 * effort (nulls where data is missing) rather than throwing, so one bad cell
 * never aborts a 10k-row dataset.
 *
 * All loaders resolve relative to a base data directory (default
 * `data/kaggle`) so the server can be relocated without code changes.
 */

import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { parse } from "csv-parse/sync";
import type { MatchRecord, MatchStats, PlayerRecord } from "./types.js";
import {
  normalizeDate,
  normalizeDateTime,
  normalizeTeam,
  parseScore,
  parseSeason,
} from "./normalize.js";

/** Synchronously parse a CSV file with header row. */
async function readCsv(path: string): Promise<Record<string, string>[]> {
  const buf = await readFile(path, "utf8");
  // Drop a UTF-8 BOM if present (fifa_data.csv ships with one).
  const text = buf.charCodeAt(0) === 0xfeff ? buf.slice(1) : buf;
  return parse(text, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    relax_quotes: true,
    relax_column_count: true,
  });
}

/** Build the default data directory relative to cwd. */
export function defaultDataDir(): string {
  return join(process.cwd(), "data", "kaggle");
}

/** Load Brasileirão Serie A matches. */
export async function loadBrasileirao(dir: string): Promise<MatchRecord[]> {
  const rows = await readCsv(join(dir, "Brasileirao_Matches.csv"));
  return rows.map((r): MatchRecord => {
    const homeRaw = r.home_team ?? "";
    const awayRaw = r.away_team ?? "";
    return {
      source: "brasileirao",
      competition: "Brasileirão",
      date: normalizeDate(r.datetime),
      datetime: normalizeDateTime(r.datetime),
      homeTeam: normalizeTeam(homeRaw),
      awayTeam: normalizeTeam(awayRaw),
      homeState: (r.home_team_state ?? null) || null,
      awayState: (r.away_team_state ?? null) || null,
      homeGoal: parseScore(r.home_goal),
      awayGoal: parseScore(r.away_goal),
      season: parseSeason(r.season),
      round: r.round ? String(r.round) : null,
      arena: null,
    };
  });
}

/** Load Copa do Brasil matches. */
export async function loadCopaDoBrasil(dir: string): Promise<MatchRecord[]> {
  const rows = await readCsv(join(dir, "Brazilian_Cup_Matches.csv"));
  return rows.map((r): MatchRecord => ({
    source: "copa_do_brasil",
    competition: "Copa do Brasil",
    date: normalizeDate(r.datetime),
    datetime: normalizeDateTime(r.datetime),
    homeTeam: normalizeTeam(r.home_team),
    awayTeam: normalizeTeam(r.away_team),
    homeState: null,
    awayState: null,
    homeGoal: parseScore(r.home_goal),
    awayGoal: parseScore(r.away_goal),
    season: parseSeason(r.season),
    round: r.round ? String(r.round) : null,
    arena: null,
  }));
}

/** Load Copa Libertadores matches. */
export async function loadLibertadores(dir: string): Promise<MatchRecord[]> {
  const rows = await readCsv(join(dir, "Libertadores_Matches.csv"));
  return rows.map((r): MatchRecord => ({
    source: "libertadores",
    competition: "Libertadores",
    date: normalizeDate(r.datetime),
    datetime: normalizeDateTime(r.datetime),
    homeTeam: normalizeTeam(r.home_team),
    awayTeam: normalizeTeam(r.away_team),
    homeState: null,
    awayState: null,
    homeGoal: parseScore(r.home_goal),
    awayGoal: parseScore(r.away_goal),
    season: parseSeason(r.season),
    round: r.stage ? String(r.stage) : null,
    arena: null,
  }));
}

function parseNumOrNull(v: string | null | undefined): number | null {
  if (!v) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

/** Half-time result cell "1-0" → [1,0]. */
function parseHalfTime(
  ht: string | null | undefined,
): [number | null, number | null] {
  if (!ht) return [null, null];
  const m = ht.match(/(\d+)\s*-\s*(\d+)/);
  if (!m) return [null, null];
  return [Number(m[1]), Number(m[2])];
}

/** Load the extended-statistics BR-Football dataset. */
export async function loadBrFootball(dir: string): Promise<MatchRecord[]> {
  const rows = await readCsv(join(dir, "BR-Football-Dataset.csv"));
  return rows.map((r): MatchRecord => {
    const [htHome, htAway] = parseHalfTime(r.ht_result);
    const stats: MatchStats = {
      homeCorner: parseNumOrNull(r.home_corner),
      awayCorner: parseNumOrNull(r.away_corner),
      homeAttack: parseNumOrNull(r.home_attack),
      awayAttack: parseNumOrNull(r.away_attack),
      homeShots: parseNumOrNull(r.home_shots),
      awayShots: parseNumOrNull(r.away_shots),
      totalCorners: parseNumOrNull(r.total_corners),
      halfTimeHome: htHome,
      halfTimeAway: htAway,
    };
    return {
      source: "br_football",
      competition: r.tournament ?? "Unknown",
      date: normalizeDate(r.date),
      datetime: normalizeDateTime(r.date),
      homeTeam: normalizeTeam(r.home),
      awayTeam: normalizeTeam(r.away),
      homeState: null,
      awayState: null,
      homeGoal: parseScore(r.home_goal),
      awayGoal: parseScore(r.away_goal),
      season: parseSeason(r.date),
      round: null,
      arena: null,
      stats,
    };
  });
}

/** Load the historical Brasileirão (2003-2019) dataset. */
export async function loadHistoricalBrasileirao(
  dir: string,
): Promise<MatchRecord[]> {
  const rows = await readCsv(join(dir, "novo_campeonato_brasileiro.csv"));
  return rows.map((r): MatchRecord => ({
    source: "historical_brasileirao",
    competition: "Brasileirão (2003-2019)",
    date: normalizeDate(r.Data),
    datetime: normalizeDate(r.Data),
    homeTeam: normalizeTeam(r.Equipe_mandante),
    awayTeam: normalizeTeam(r.Equipe_visitante),
    homeState: (r.Mandante_UF ?? null) || null,
    awayState: (r.Visitante_UF ?? null) || null,
    homeGoal: parseScore(r.Gols_mandante),
    awayGoal: parseScore(r.Gols_visitante),
    season: parseSeason(r.Ano),
    round: r.Rodada ? String(r.Rodada) : null,
    arena: (r.Arena ?? null) || null,
  }));
}

/** Load the FIFA player database. */
export async function loadFifaPlayers(
  dir: string,
): Promise<PlayerRecord[]> {
  const rows = await readCsv(join(dir, "fifa_data.csv"));
  return rows.map((r): PlayerRecord => ({
    id: parseScore(r.ID) ?? 0,
    name: r.Name ?? "",
    age: parseScore(r.Age),
    nationality: r.Nationality ?? "",
    overall: parseScore(r.Overall),
    potential: parseScore(r.Potential),
    club: r.Club ?? "",
    position: r.Position ?? "",
    jerseyNumber: parseScore(r["Jersey Number"]),
    height: (r.Height ?? null) || null,
    weight: (r.Weight ?? null) || null,
    preferredFoot: (r["Preferred Foot"] ?? null) || null,
  }));
}

/** Load every match dataset and concatenate. */
export async function loadAllMatches(dir: string): Promise<MatchRecord[]> {
  const parts = await Promise.all([
    loadBrasileirao(dir).catch(() => [] as MatchRecord[]),
    loadCopaDoBrasil(dir).catch(() => [] as MatchRecord[]),
    loadLibertadores(dir).catch(() => [] as MatchRecord[]),
    loadBrFootball(dir).catch(() => [] as MatchRecord[]),
    loadHistoricalBrasileirao(dir).catch(() => [] as MatchRecord[]),
  ]);
  return parts.flat();
}
