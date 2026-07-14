/**
 * Context
 * -------
 * Loads the six Kaggle CSV files in `data/kaggle/` into the unified `Match`
 * and `Player` models and exposes them through a `Dataset` object.
 *
 * Responsibilities:
 *   - Map each file's columns onto the canonical shape.
 *   - Assign a canonical `Competition` label per row.
 *   - Deduplicate matches that appear in more than one source (Série A and
 *     Copa do Brasil are present both in the dedicated files and in
 *     BR-Football-Dataset.csv). The richer "extended statistics" source merges
 *     its corner/shot/half-time data into the already-loaded match instead of
 *     creating a duplicate.
 *
 * Loading is synchronous and one-shot; with ~33k matches + 18k players it
 * comfortably fits the spec's <2s simple / <5s aggregate latency budget.
 */

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { parseCsv } from "./csv.js";
import { parseDate, parseTeam } from "./normalize.js";
import type { Competition, Match, MatchStats, Player, SourceFile } from "./models.js";

const HERE = dirname(fileURLToPath(import.meta.url));
/** Default data directory: `<repo>/data/kaggle` regardless of cwd. */
export const DEFAULT_DATA_DIR = join(HERE, "..", "data", "kaggle");

export interface Dataset {
  readonly matches: readonly Match[];
  readonly players: readonly Player[];
}

/** Numeric coercion that tolerates blanks, quotes, and trailing ".0" floats. */
function num(value: string | undefined): number | undefined {
  if (value === undefined) return undefined;
  const t = value.trim().replace(/^"|"$/g, "");
  if (t === "") return undefined;
  const n = Number(t);
  return Number.isFinite(n) ? n : undefined;
}

function makeMatch(args: {
  source: SourceFile;
  competition: Competition;
  season: number;
  date?: string;
  round?: string;
  stage?: string;
  stadium?: string;
  home: string;
  away: string;
  homeGoals: number;
  awayGoals: number;
  stats?: MatchStats;
}): Match {
  return {
    source: args.source,
    competition: args.competition,
    season: args.season,
    date: parseDate(args.date),
    round: args.round?.trim() || undefined,
    stage: args.stage?.trim() || undefined,
    stadium: args.stadium?.trim() || undefined,
    homeTeamRaw: args.home,
    awayTeamRaw: args.away,
    home: parseTeam(args.home),
    away: parseTeam(args.away),
    homeGoals: args.homeGoals,
    awayGoals: args.awayGoals,
    stats: args.stats,
  };
}

const BR_FOOTBALL_COMPETITION: Record<string, Competition> = {
  "serie a": "Brasileirão Série A",
  "serie b": "Brasileirão Série B",
  "serie c": "Brasileirão Série C",
  "copa do brasil": "Copa do Brasil",
};

function loadBrasileirao(dir: string): Match[] {
  const rows = parseCsv(readFileSync(join(dir, "Brasileirao_Matches.csv"), "utf8"));
  const out: Match[] = [];
  for (const r of rows) {
    const hg = num(r["home_goal"]);
    const ag = num(r["away_goal"]);
    const season = num(r["season"]);
    if (hg === undefined || ag === undefined || season === undefined) continue;
    out.push(
      makeMatch({
        source: "Brasileirao_Matches.csv",
        competition: "Brasileirão Série A",
        season,
        date: r["datetime"],
        round: r["round"],
        home: r["home_team"] ?? "",
        away: r["away_team"] ?? "",
        homeGoals: hg,
        awayGoals: ag,
      }),
    );
  }
  return out;
}

function loadCup(dir: string): Match[] {
  const rows = parseCsv(readFileSync(join(dir, "Brazilian_Cup_Matches.csv"), "utf8"));
  const out: Match[] = [];
  for (const r of rows) {
    const hg = num(r["home_goal"]);
    const ag = num(r["away_goal"]);
    const season = num(r["season"]);
    if (hg === undefined || ag === undefined || season === undefined) continue;
    out.push(
      makeMatch({
        source: "Brazilian_Cup_Matches.csv",
        competition: "Copa do Brasil",
        season,
        date: r["datetime"],
        round: r["round"],
        home: r["home_team"] ?? "",
        away: r["away_team"] ?? "",
        homeGoals: hg,
        awayGoals: ag,
      }),
    );
  }
  return out;
}

function loadLibertadores(dir: string): Match[] {
  const rows = parseCsv(readFileSync(join(dir, "Libertadores_Matches.csv"), "utf8"));
  const out: Match[] = [];
  for (const r of rows) {
    const hg = num(r["home_goal"]);
    const ag = num(r["away_goal"]);
    const season = num(r["season"]);
    if (hg === undefined || ag === undefined || season === undefined) continue;
    out.push(
      makeMatch({
        source: "Libertadores_Matches.csv",
        competition: "Copa Libertadores",
        season,
        date: r["datetime"],
        stage: r["stage"],
        home: r["home_team"] ?? "",
        away: r["away_team"] ?? "",
        homeGoals: hg,
        awayGoals: ag,
      }),
    );
  }
  return out;
}

function loadHistorical(dir: string): Match[] {
  const rows = parseCsv(readFileSync(join(dir, "novo_campeonato_brasileiro.csv"), "utf8"));
  const out: Match[] = [];
  for (const r of rows) {
    const hg = num(r["Gols_mandante"]);
    const ag = num(r["Gols_visitante"]);
    const season = num(r["Ano"]);
    if (hg === undefined || ag === undefined || season === undefined) continue;
    out.push(
      makeMatch({
        source: "novo_campeonato_brasileiro.csv",
        competition: "Brasileirão Série A",
        season,
        date: r["Data"],
        round: r["Rodada"],
        stadium: r["Arena"],
        home: r["Equipe_mandante"] ?? "",
        away: r["Equipe_visitante"] ?? "",
        homeGoals: hg,
        awayGoals: ag,
      }),
    );
  }
  return out;
}

function loadExtended(dir: string): Match[] {
  const rows = parseCsv(readFileSync(join(dir, "BR-Football-Dataset.csv"), "utf8"));
  const out: Match[] = [];
  for (const r of rows) {
    const hg = num(r["home_goal"]);
    const ag = num(r["away_goal"]);
    const competition = BR_FOOTBALL_COMPETITION[(r["tournament"] ?? "").trim().toLowerCase()];
    const date = parseDate(r["date"]);
    if (hg === undefined || ag === undefined || !competition || !date) continue;
    const stats: MatchStats = {
      homeCorners: num(r["home_corner"]),
      awayCorners: num(r["away_corner"]),
      totalCorners: num(r["total_corners"]),
      homeShots: num(r["home_shots"]),
      awayShots: num(r["away_shots"]),
      homeAttacks: num(r["home_attack"]),
      awayAttacks: num(r["away_attack"]),
    };
    out.push(
      makeMatch({
        source: "BR-Football-Dataset.csv",
        competition,
        season: date.year,
        date: r["date"],
        home: r["home"] ?? "",
        away: r["away"] ?? "",
        homeGoals: hg,
        awayGoals: ag,
        stats,
      }),
    );
  }
  return out;
}

/**
 * Per-source preference rank. For any given (competition, season) we keep the
 * matches from the single highest-ranked source that covers it, instead of
 * fuzzy-deduplicating near-identical rows whose team spellings diverge between
 * sources ("Atletico-PR" vs "Athletico-PR"). This guarantees each real game is
 * counted exactly once — critical for standings and win-rate math.
 *
 *   - Série A 2012–2022 → Brasileirao_Matches.csv (rank 4)
 *   - Série A 2003–2011 → novo_campeonato_brasileiro.csv (rank 3)
 *   - Série A 2023, Série B/C → BR-Football-Dataset.csv (rank 1, sole source)
 *   - Copa do Brasil → Brazilian_Cup_Matches.csv (rank 4)
 *   - Copa Libertadores → Libertadores_Matches.csv (rank 4)
 */
const SOURCE_RANK: Record<SourceFile, number> = {
  "Brasileirao_Matches.csv": 4,
  "Brazilian_Cup_Matches.csv": 4,
  "Libertadores_Matches.csv": 4,
  "novo_campeonato_brasileiro.csv": 3,
  "BR-Football-Dataset.csv": 1,
};

/** Stats-enrichment key: competition, season, folded teams, score. */
function statsKey(m: Match): string {
  return [m.competition, m.season, m.home.baseKey, m.away.baseKey, m.homeGoals, m.awayGoals].join("|");
}

/**
 * Select the canonical match list:
 *   1. For each (competition, season) keep only rows from the top-ranked source.
 *   2. Enrich surviving rows with extended stats from BR-Football-Dataset.csv
 *      (corners/shots/attacks), matched on {competition, season, teams, score}.
 */
function selectCanonical(all: Match[], extended: Match[]): Match[] {
  const bestRank = new Map<string, number>();
  for (const m of all) {
    const g = `${m.competition}|${m.season}`;
    const rank = SOURCE_RANK[m.source];
    if (rank > (bestRank.get(g) ?? 0)) bestRank.set(g, rank);
  }

  const canonical = all.filter((m) => SOURCE_RANK[m.source] === bestRank.get(`${m.competition}|${m.season}`));

  // Index every extended row's stats so non-canonical sources still contribute
  // their statistics to the canonical match for the same game.
  const stats = new Map<string, MatchStats>();
  for (const m of extended) {
    if (m.stats) stats.set(statsKey(m), m.stats);
  }
  for (const m of canonical) {
    if (!m.stats) {
      const found = stats.get(statsKey(m));
      if (found) m.stats = found;
    }
  }
  return canonical;
}

function loadPlayers(dir: string): Player[] {
  const rows = parseCsv(readFileSync(join(dir, "fifa_data.csv"), "utf8"));
  const out: Player[] = [];
  for (const r of rows) {
    const id = num(r["ID"]);
    const name = (r["Name"] ?? "").trim();
    if (id === undefined || !name) continue;
    out.push({
      id,
      name,
      age: num(r["Age"]),
      nationality: (r["Nationality"] ?? "").trim(),
      overall: num(r["Overall"]),
      potential: num(r["Potential"]),
      club: (r["Club"] ?? "").trim(),
      position: (r["Position"] ?? "").trim(),
      jerseyNumber: num(r["Jersey Number"]),
      height: (r["Height"] ?? "").trim() || undefined,
      weight: (r["Weight"] ?? "").trim() || undefined,
      preferredFoot: (r["Preferred Foot"] ?? "").trim() || undefined,
    });
  }
  return out;
}

/** Load every dataset from `dir` (defaults to the bundled `data/kaggle`). */
export function loadDataset(dir: string = DEFAULT_DATA_DIR): Dataset {
  const extended = loadExtended(dir);
  const all = [
    ...loadBrasileirao(dir),
    ...loadCup(dir),
    ...loadLibertadores(dir),
    ...loadHistorical(dir),
    ...extended,
  ];
  const matches = selectCanonical(all, extended);
  const players = loadPlayers(dir);
  return { matches, players };
}
