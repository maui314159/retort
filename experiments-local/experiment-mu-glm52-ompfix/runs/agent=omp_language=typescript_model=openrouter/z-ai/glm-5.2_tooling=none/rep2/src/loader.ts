/**
 * Brazilian Soccer MCP Server — CSV loader
 * -----------------------------------------
 * Context block:
 *   Loads all six Kaggle CSV files into the normalised in-memory record shapes
 *   defined in types.ts. Each loader is a small function that maps the raw
 *   columns of one file to Match/Player records, applying team-name and date
 *   normalisation. The top-level `loadAll` function resolves the data directory
 *   (default ../data/kaggle relative to this module) and returns a `Dataset`
 *   bundle consumed by the query tools and the MCP server entrypoint.
 *
 *   CSV parsing uses the streaming `csv-parse/sync` parser with `columns:true`
 *   so headers become object keys. Empty/`NA` numeric fields are coerced to
 *   null via parseNum. Team names pass through canonicalTeamKey/teamDisplay.
 */

import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parse } from "csv-parse/sync";

import type { Match, MatchSource, MatchStats, Player, PlayerSkills } from "./types.js";
import { canonicalTeamKey, teamDisplay } from "./normalizer.js";
import { parseDate, parseNum } from "./dates.js";

/** All loaded data. */
export interface Dataset {
  matches: Match[];
  players: Player[];
  /** Counts per source for a quick health check. */
  counts: { matchesBySource: Record<string, number>; players: number };
}

const __dirname = dirname(fileURLToPath(import.meta.url));

/** Read and parse a CSV file into an array of row objects. */
function readCsv(filePath: string): Record<string, string>[] {
  const content = readFileSync(filePath, "utf8");
  const records = parse(content, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    relax_quotes: true,
    relax_column_count: true,
    bom: true,
  }) as Record<string, string>[];
  return records;
}

interface LoadContext {
  source: MatchSource;
  competition: string;
  rows: Record<string, string>[];
}

/** Convert a batch of raw rows into normalised Match records. */
function toMatches(ctx: LoadContext, rows: Record<string, string>[]): Match[] {
  const out: Match[] = [];
  rows.forEach((row, i) => {
    const match = rowToMatch(ctx, row, i);
    if (match) out.push(match);
  });
  return out;
}

/** Map one raw row to a Match, dispatching on the source. */
function rowToMatch(
  ctx: LoadContext,
  row: Record<string, string>,
  index: number,
): Match | null {
  const base = {
    id: `${ctx.source}-${index}`,
    source: ctx.source,
    competition: ctx.competition,
  };
  switch (ctx.source) {
    case "brasileirao":
      return brasileiraoRow(base, row);
    case "copa_do_brasil":
      return cupRow(base, row);
    case "libertadores":
      return libertadoresRow(base, row);
    case "br_football":
      return brFootballRow(base, row);
    case "historico":
      return historicoRow(base, row);
    default:
      return null;
  }
}

function brasileiraoRow(base: { id: string; source: MatchSource; competition: string }, row: Record<string, string>): Match {
  const homeRaw = row["home_team"] ?? "";
  const awayRaw = row["away_team"] ?? "";
  return {
    ...base,
    homeTeam: canonicalTeamKey(homeRaw),
    homeTeamDisplay: teamDisplay(homeRaw),
    awayTeam: canonicalTeamKey(awayRaw),
    awayTeamDisplay: teamDisplay(awayRaw),
    homeGoal: parseNum(row["home_goal"]),
    awayGoal: parseNum(row["away_goal"]),
    season: parseNum(row["season"]),
    round: row["round"] ?? null,
    date: parseDate(row["datetime"]),
    rawDate: row["datetime"] ?? "",
  };
}

function cupRow(base: { id: string; source: MatchSource; competition: string }, row: Record<string, string>): Match {
  const homeRaw = row["home_team"] ?? "";
  const awayRaw = row["away_team"] ?? "";
  return {
    ...base,
    homeTeam: canonicalTeamKey(homeRaw),
    homeTeamDisplay: teamDisplay(homeRaw),
    awayTeam: canonicalTeamKey(awayRaw),
    awayTeamDisplay: teamDisplay(awayRaw),
    homeGoal: parseNum(row["home_goal"]),
    awayGoal: parseNum(row["away_goal"]),
    season: parseNum(row["season"]),
    round: row["round"] ?? null,
    date: parseDate(row["datetime"]),
    rawDate: row["datetime"] ?? "",
  };
}

function libertadoresRow(base: { id: string; source: MatchSource; competition: string }, row: Record<string, string>): Match {
  const homeRaw = row["home_team"] ?? "";
  const awayRaw = row["away_team"] ?? "";
  return {
    ...base,
    homeTeam: canonicalTeamKey(homeRaw),
    homeTeamDisplay: teamDisplay(homeRaw),
    awayTeam: canonicalTeamKey(awayRaw),
    awayTeamDisplay: teamDisplay(awayRaw),
    homeGoal: parseNum(row["home_goal"]),
    awayGoal: parseNum(row["away_goal"]),
    season: parseNum(row["season"]),
    round: null,
    stage: row["stage"] ?? null,
    date: parseDate(row["datetime"]),
    rawDate: row["datetime"] ?? "",
  };
}

function brFootballRow(base: { id: string; source: MatchSource; competition: string }, row: Record<string, string>): Match {
  const tournament = row["tournament"] ?? "";
  const homeRaw = row["home"] ?? "";
  const awayRaw = row["away"] ?? "";
  const stats: MatchStats = {
    homeCorner: parseNum(row["home_corner"]),
    awayCorner: parseNum(row["away_corner"]),
    homeAttack: parseNum(row["home_attack"]),
    awayAttack: parseNum(row["away_attack"]),
    homeShots: parseNum(row["home_shots"]),
    awayShots: parseNum(row["away_shots"]),
    homeHalf: parseNum(row["ht_result"]),
    awayHalf: parseNum(row["at_result"]),
    totalCorners: parseNum(row["total_corners"]),
  };
  return {
    ...base,
    competition: tournament || base.competition,
    homeTeam: canonicalTeamKey(homeRaw),
    homeTeamDisplay: teamDisplay(homeRaw),
    awayTeam: canonicalTeamKey(awayRaw),
    awayTeamDisplay: teamDisplay(awayRaw),
    homeGoal: parseNum(row["home_goal"]),
    awayGoal: parseNum(row["away_goal"]),
    season: parseSeasonFromDate(row["date"]),
    round: null,
    date: parseDate(row["date"]),
    rawDate: row["date"] ?? "",
    stats,
  };
}

function historicoRow(base: { id: string; source: MatchSource; competition: string }, row: Record<string, string>): Match {
  const homeRaw = row["Equipe_mandante"] ?? "";
  const awayRaw = row["Equipe_visitante"] ?? "";
  return {
    ...base,
    homeTeam: canonicalTeamKey(homeRaw),
    homeTeamDisplay: teamDisplay(homeRaw),
    awayTeam: canonicalTeamKey(awayRaw),
    awayTeamDisplay: teamDisplay(awayRaw),
    homeGoal: parseNum(row["Gols_mandante"]),
    awayGoal: parseNum(row["Gols_visitante"]),
    season: parseNum(row["Ano"]),
    round: row["Rodada"] ?? null,
    date: parseDate(row["Data"]),
    rawDate: row["Data"] ?? "",
    arena: row["Arena"] ?? null,
  };
}

/** Infer a season year from an ISO date string (YYYY-MM-DD → year). */
function parseSeasonFromDate(raw: string | undefined): number | null {
  const date = parseDate(raw);
  if (!date) return null;
  return date.getUTCFullYear();
}

/**
 * Load the FIFA player CSV. The file has a leading unnamed column (row index)
 * and many skill columns; we keep a curated subset of skills.
 */
function loadPlayers(filePath: string): Player[] {
  const rows = readCsv(filePath);
  const players: Player[] = [];
  for (const row of rows) {
    const id = parseNum(row["ID"]);
    if (id === null) continue;
    players.push({
      id,
      name: row["Name"] ?? "",
      age: parseNum(row["Age"]),
      nationality: row["Nationality"] ?? "",
      overall: parseNum(row["Overall"]),
      potential: parseNum(row["Potential"]),
      club: row["Club"] ?? "",
      position: row["Position"] ?? "",
      jerseyNumber: parseNum(row["Jersey Number"]),
      height: row["Height"] ?? null,
      weight: row["Weight"] ?? null,
      skills: extractSkills(row),
    });
  }
  return players;
}

function extractSkills(row: Record<string, string>): PlayerSkills {
  return {
    crossing: parseNum(row["Crossing"]),
    finishing: parseNum(row["Finishing"]),
    dribbling: parseNum(row["Dribbling"]),
    shortPassing: parseNum(row["ShortPassing"]),
    longPassing: parseNum(row["LongPassing"]),
    shotPower: parseNum(row["ShotPower"]),
    stamina: parseNum(row["Stamina"]),
    strength: parseNum(row["Strength"]),
    interceptions: parseNum(row["Interceptions"]),
    positioning: parseNum(row["Positioning"]),
    vision: parseNum(row["Vision"]),
    composure: parseNum(row["Composure"]),
  };
}

/** Resolve the data directory. Defaults to ../data/kaggle relative to dist/. */
function defaultDataDir(): string {
  // From dist/ go up to project root then into data/kaggle.
  return resolve(__dirname, "..", "data", "kaggle");
}

/**
 * Load all datasets from the given directory (or the default location).
 * Missing files are skipped with a warning rather than throwing, so the server
 * still starts when a subset is present.
 */
export function loadAll(dataDir: string = defaultDataDir()): Dataset {
  const matches: Match[] = [];
  const counts: { matchesBySource: Record<string, number>; players: number } = {
    matchesBySource: {},
    players: 0,
  };

  const sources: { source: MatchSource; competition: string; file: string }[] = [
    { source: "brasileirao", competition: "Brasileirão", file: "Brasileirao_Matches.csv" },
    { source: "copa_do_brasil", competition: "Copa do Brasil", file: "Brazilian_Cup_Matches.csv" },
    { source: "libertadores", competition: "Copa Libertadores", file: "Libertadores_Matches.csv" },
    { source: "br_football", competition: "Brasileirão", file: "BR-Football-Dataset.csv" },
    { source: "historico", competition: "Brasileirão", file: "novo_campeonato_brasileiro.csv" },
  ];

  for (const { source, competition, file } of sources) {
    const filePath = join(dataDir, file);
    let rows: Record<string, string>[] = [];
    try {
      rows = readCsv(filePath);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      console.error(`[loader] skipping ${file}: ${message}`);
      continue;
    }
    const parsed = toMatches({ source, competition, rows }, rows);
    matches.push(...parsed);
    counts.matchesBySource[source] = parsed.length;
  }

  const fifaPath = join(dataDir, "fifa_data.csv");
  let players: Player[] = [];
  try {
    players = loadPlayers(fifaPath);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    console.error(`[loader] skipping fifa_data.csv: ${message}`);
  }
  const deduped = deduplicateMatches(matches);

  return { matches: deduped, players, counts };
}

/**
 * Remove duplicate matches (same date + same canonical teams). The brasileirao
 * (2012–2022) and historico (2003–2019) datasets overlap in 2012–2019, and
 * the BR-Football dataset can overlap with brasileirao for shared years.
 * Deduplicating keeps the first occurrence per (date, home, away) key so
 * standings and aggregates are not double-counted.
 */
function deduplicateMatches(matches: Match[]): Match[] {
  const seen = new Set<string>();
  const out: Match[] = [];
  for (const m of matches) {
    const ts = m.date ? m.date.getTime() : 0;
    const key = `${ts}|${m.homeTeam}|${m.awayTeam}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(m);
  }
  return out;
}
