/**
 * Context
 * -------
 * Data loader for the Brazilian Soccer MCP server. Reads the six Kaggle CSV
 * files from `data/kaggle/`, maps each heterogeneous row schema into the
 * unified `Match`/`Player` domain types (see types.ts), and returns a single
 * in-memory `SoccerData` knowledge base.
 *
 * Each source has its own column names, date format and team-naming quirks;
 * those differences are absorbed here so the query engine sees one model.
 * Loading is synchronous and done once at startup (~42k rows total), keeping
 * lookups well under the spec's <2s / <5s latency budgets.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { parseCsv } from "./csv.js";
import {
  cleanDisplayName,
  normalizeTeamKey,
  parseDate,
  parseFloatSafe,
  parseIntSafe,
} from "./normalize.js";
import type {
  Competition,
  Match,
  Player,
  SoccerData,
  SourceFile,
} from "./types.js";

/** Build a unified Match from already-cleaned team names and scores. */
function makeMatch(
  source: SourceFile,
  index: number,
  competition: Competition,
  fields: {
    home: string;
    away: string;
    homeGoals?: number;
    awayGoals?: number;
    date?: string;
    season?: number;
    round?: string;
    stage?: string;
    arena?: string;
    stats?: Match["stats"];
  }
): Match {
  return {
    id: `${source}#${index}`,
    competition,
    source,
    date: fields.date,
    season: fields.season,
    round: fields.round,
    stage: fields.stage,
    homeTeam: cleanDisplayName(fields.home),
    awayTeam: cleanDisplayName(fields.away),
    homeKey: normalizeTeamKey(fields.home),
    awayKey: normalizeTeamKey(fields.away),
    homeGoals: fields.homeGoals,
    awayGoals: fields.awayGoals,
    arena: fields.arena,
    stats: fields.stats,
  };
}

/** Map a BR-Football-Dataset tournament string to a Competition. */
function mapTournament(raw: string): Competition {
  const t = raw.toLowerCase();
  if (t.includes("serie a")) return "Brasileirão Série A";
  if (t.includes("serie b")) return "Brasileirão Série B";
  if (t.includes("serie c")) return "Brasileirão Série C";
  if (t.includes("copa do brasil")) return "Copa do Brasil";
  if (t.includes("libertadores")) return "Copa Libertadores";
  return "Other";
}

function loadBrasileirao(dir: string): Match[] {
  const rows = parseCsv(readFileSync(join(dir, "Brasileirao_Matches.csv"), "utf8"));
  return rows.map((r, i) =>
    makeMatch("Brasileirao_Matches.csv", i, "Brasileirão Série A", {
      home: r.home_team,
      away: r.away_team,
      homeGoals: parseIntSafe(r.home_goal),
      awayGoals: parseIntSafe(r.away_goal),
      date: parseDate(r.datetime),
      season: parseIntSafe(r.season),
      round: r.round || undefined,
    })
  );
}

function loadCup(dir: string): Match[] {
  const rows = parseCsv(readFileSync(join(dir, "Brazilian_Cup_Matches.csv"), "utf8"));
  return rows.map((r, i) =>
    makeMatch("Brazilian_Cup_Matches.csv", i, "Copa do Brasil", {
      home: r.home_team,
      away: r.away_team,
      homeGoals: parseIntSafe(r.home_goal),
      awayGoals: parseIntSafe(r.away_goal),
      date: parseDate(r.datetime),
      season: parseIntSafe(r.season),
      round: r.round || undefined,
    })
  );
}

function loadLibertadores(dir: string): Match[] {
  const rows = parseCsv(readFileSync(join(dir, "Libertadores_Matches.csv"), "utf8"));
  return rows.map((r, i) =>
    makeMatch("Libertadores_Matches.csv", i, "Copa Libertadores", {
      home: r.home_team,
      away: r.away_team,
      homeGoals: parseIntSafe(r.home_goal),
      awayGoals: parseIntSafe(r.away_goal),
      date: parseDate(r.datetime),
      season: parseIntSafe(r.season),
      stage: r.stage || undefined,
    })
  );
}

function loadExtended(dir: string): Match[] {
  const rows = parseCsv(readFileSync(join(dir, "BR-Football-Dataset.csv"), "utf8"));
  const out: Match[] = [];
  for (let i = 0; i < rows.length; i++) {
    const r = rows[i];
    const date = parseDate(r.date);
    out.push(
      makeMatch("BR-Football-Dataset.csv", i, mapTournament(r.tournament), {
        home: r.home,
        away: r.away,
        homeGoals: parseIntSafe(r.home_goal),
        awayGoals: parseIntSafe(r.away_goal),
        date,
        season: date ? parseIntSafe(date.slice(0, 4)) : undefined,
        stats: {
          homeShots: parseFloatSafe(r.home_shots),
          awayShots: parseFloatSafe(r.away_shots),
          homeCorners: parseFloatSafe(r.home_corner),
          awayCorners: parseFloatSafe(r.away_corner),
          homeAttacks: parseFloatSafe(r.home_attack),
          awayAttacks: parseFloatSafe(r.away_attack),
          totalCorners: parseFloatSafe(r.total_corners),
          halfTimeHome: r.ht_result || undefined,
          halfTimeAway: r.at_result || undefined,
        },
      })
    );
  }
  return out;
}

function loadHistorical(dir: string): Match[] {
  const rows = parseCsv(
    readFileSync(join(dir, "novo_campeonato_brasileiro.csv"), "utf8")
  );
  return rows.map((r, i) =>
    makeMatch("novo_campeonato_brasileiro.csv", i, "Brasileirão Série A", {
      home: r.Equipe_mandante,
      away: r.Equipe_visitante,
      homeGoals: parseIntSafe(r.Gols_mandante),
      awayGoals: parseIntSafe(r.Gols_visitante),
      date: parseDate(r.Data),
      season: parseIntSafe(r.Ano),
      round: r.Rodada || undefined,
      arena: r.Arena || undefined,
    })
  );
}

function loadPlayers(dir: string): Player[] {
  const rows = parseCsv(readFileSync(join(dir, "fifa_data.csv"), "utf8"));
  return rows.map((r) => ({
    id: r.ID,
    name: r.Name,
    age: parseIntSafe(r.Age),
    nationality: r.Nationality,
    overall: parseIntSafe(r.Overall),
    potential: parseIntSafe(r.Potential),
    club: r.Club,
    clubKey: normalizeTeamKey(r.Club ?? ""),
    position: r.Position,
    jerseyNumber: parseIntSafe(r["Jersey Number"]),
    height: r.Height || undefined,
    weight: r.Weight || undefined,
    preferredFoot: r["Preferred Foot"] || undefined,
  }));
}

/**
 * Source preference per competition+season. The Brasileirão Série A fixtures
 * appear verbatim in up to three files (Brasileirao_Matches, the 2003-2019
 * historical set, and the BR-Football aggregator), and Copa do Brasil in two.
 * Loading them all would triple standings/head-to-head totals, so for each
 * `(competition, season)` we keep only the single highest-priority source that
 * covers it. Lower number = higher priority; the dedicated per-competition
 * files win, the broad multi-competition aggregator is the fallback.
 */
const SOURCE_PRIORITY: Record<SourceFile, number> = {
  "Brasileirao_Matches.csv": 0,
  "Brazilian_Cup_Matches.csv": 0,
  "Libertadores_Matches.csv": 0,
  "novo_campeonato_brasileiro.csv": 1,
  "BR-Football-Dataset.csv": 2,
};

/**
 * Drop duplicate fixtures that appear in more than one source. Matches are
 * grouped by `competition|season`; within each group only the highest-priority
 * source is retained. Matches without a season (unparseable date) cannot be
 * grouped safely and are always kept.
 */
function deduplicate(matches: Match[]): Match[] {
  const bestSource = new Map<string, SourceFile>();
  for (const m of matches) {
    if (m.season === undefined) continue;
    const group = `${m.competition}|${m.season}`;
    const current = bestSource.get(group);
    if (current === undefined || SOURCE_PRIORITY[m.source] < SOURCE_PRIORITY[current]) {
      bestSource.set(group, m.source);
    }
  }
  return matches.filter((m) => {
    if (m.season === undefined) return true;
    return bestSource.get(`${m.competition}|${m.season}`) === m.source;
  });
}

/**
 * Load the full knowledge base from the dataset directory.
 * @param dataDir directory containing the Kaggle CSV files (the `data/kaggle`
 *   folder). Defaults to `data/kaggle` relative to the current working dir.
 */
export function loadSoccerData(dataDir = join(process.cwd(), "data", "kaggle")): SoccerData {
  const matches = deduplicate([
    ...loadBrasileirao(dataDir),
    ...loadCup(dataDir),
    ...loadLibertadores(dataDir),
    ...loadExtended(dataDir),
    ...loadHistorical(dataDir),
  ]);
  const players = loadPlayers(dataDir);
  return { matches, players };
}
