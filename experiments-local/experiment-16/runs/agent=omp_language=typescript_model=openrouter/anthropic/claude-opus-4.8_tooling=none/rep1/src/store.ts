/**
 * Context
 * -------
 * Loads the five match CSVs and the FIFA player CSV from `data/kaggle/` and
 * projects them into the unified `Match` / `Player` domain model. The store is
 * built once and held in memory; with ~24k matches and ~18k players this fits
 * comfortably and keeps every query well under the spec's 2s/5s latency budget.
 *
 * Source-file quirks handled here:
 *   - Brasileirao_Matches.csv      : teams carry "-UF" suffixes; round is numeric.
 *   - Brazilian_Cup_Matches.csv    : teams carry " - UF" suffixes; competition fixed.
 *   - Libertadores_Matches.csv     : goals quoted as strings; `stage` is the round.
 *   - BR-Football-Dataset.csv      : `tournament` maps Serie A->Brasileirão, also
 *                                    Serie B/C and Copa do Brasil; season from date.
 *   - novo_campeonato_brasileiro.csv: Portuguese headers; DD/MM/YYYY dates; arena.
 *   - fifa_data.csv                : leading BOM column; rich attribute columns.
 *
 * Exports
 * -------
 * - DataStore: holds matches + players and exposes them.
 * - loadStore(dataDir?): build a DataStore from CSV files on disk.
 */

import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { parseCsv } from "./csv.js";
import { normalizeTeam, parseDate, parseGoals } from "./normalize.js";
import type { Competition, Match, Player } from "./types.js";

/** Map BR-Football-Dataset `tournament` values onto canonical competitions. */
const TOURNAMENT_MAP: Record<string, Competition> = {
  "serie a": "Brasileirão",
  "serie b": "Serie B",
  "serie c": "Serie C",
  "copa do brasil": "Copa do Brasil",
};

/** In-memory dataset exposed to every query module. */
export class DataStore {
  constructor(
    readonly matches: Match[],
    readonly players: Player[],
  ) {}

  /** Distinct competitions present in the loaded matches. */
  competitions(): Competition[] {
    const seen = new Set<Competition>();
    for (const m of this.matches) seen.add(m.competition);
    return [...seen];
  }
}

function buildMatch(
  source: string,
  competition: Competition,
  home: string,
  away: string,
  homeGoal: string | undefined,
  awayGoal: string | undefined,
  dateRaw: string | undefined,
  seasonRaw: string | undefined,
  round: string | null,
  arena: string | null,
): Match {
  const parsedDate = parseDate(dateRaw);
  let season: number | null = seasonRaw ? Number(seasonRaw) : null;
  if ((season == null || !Number.isFinite(season)) && parsedDate.iso) {
    season = Number(parsedDate.iso.slice(0, 4));
  }
  if (season != null && !Number.isFinite(season)) season = null;

  return {
    source,
    competition,
    date: parsedDate.iso,
    dateRaw: parsedDate.raw,
    season,
    round: round && round.trim() !== "" ? round.trim() : null,
    homeTeam: home,
    awayTeam: away,
    homeKey: normalizeTeam(home),
    awayKey: normalizeTeam(away),
    homeGoal: parseGoals(homeGoal),
    awayGoal: parseGoals(awayGoal),
    arena: arena && arena.trim() !== "" ? arena.trim() : null,
  };
}

async function readCsvFile(path: string): Promise<Record<string, string>[]> {
  const text = await readFile(path, "utf8");
  return parseCsv(text);
}

/** Build a DataStore by loading all CSVs from `dataDir`. */
export async function loadStore(
  dataDir = join(process.cwd(), "data", "kaggle"),
): Promise<DataStore> {
  const file = (name: string) => join(dataDir, name);

  const [brasileirao, cup, liberta, brFootball, novo, fifa] = await Promise.all([
    readCsvFile(file("Brasileirao_Matches.csv")),
    readCsvFile(file("Brazilian_Cup_Matches.csv")),
    readCsvFile(file("Libertadores_Matches.csv")),
    readCsvFile(file("BR-Football-Dataset.csv")),
    readCsvFile(file("novo_campeonato_brasileiro.csv")),
    readCsvFile(file("fifa_data.csv")),
  ]);

  const matches: Match[] = [];

  for (const r of brasileirao) {
    matches.push(
      buildMatch(
        "Brasileirao_Matches.csv",
        "Brasileirão",
        r.home_team,
        r.away_team,
        r.home_goal,
        r.away_goal,
        r.datetime,
        r.season,
        r.round ?? null,
        null,
      ),
    );
  }

  for (const r of cup) {
    matches.push(
      buildMatch(
        "Brazilian_Cup_Matches.csv",
        "Copa do Brasil",
        r.home_team,
        r.away_team,
        r.home_goal,
        r.away_goal,
        r.datetime,
        r.season,
        r.round ?? null,
        null,
      ),
    );
  }

  for (const r of liberta) {
    matches.push(
      buildMatch(
        "Libertadores_Matches.csv",
        "Libertadores",
        r.home_team,
        r.away_team,
        r.home_goal,
        r.away_goal,
        r.datetime,
        r.season,
        r.stage ?? null,
        null,
      ),
    );
  }

  for (const r of brFootball) {
    const competition = TOURNAMENT_MAP[(r.tournament ?? "").toLowerCase().trim()];
    if (!competition) continue; // skip unknown tournaments
    matches.push(
      buildMatch(
        "BR-Football-Dataset.csv",
        competition,
        r.home,
        r.away,
        r.home_goal,
        r.away_goal,
        r.date,
        undefined,
        null,
        null,
      ),
    );
  }

  for (const r of novo) {
    matches.push(
      buildMatch(
        "novo_campeonato_brasileiro.csv",
        "Brasileirão",
        r.Equipe_mandante,
        r.Equipe_visitante,
        r.Gols_mandante,
        r.Gols_visitante,
        r.Data,
        r.Ano,
        r.Rodada ?? null,
        r.Arena ?? null,
      ),
    );
  }

  const players: Player[] = [];
  for (const r of fifa) {
    const name = (r.Name ?? "").trim();
    if (name === "") continue;
    const club = (r.Club ?? "").trim();
    players.push({
      id: (r.ID ?? "").trim(),
      name,
      age: r.Age ? Number(r.Age) : null,
      nationality: (r.Nationality ?? "").trim(),
      overall: r.Overall ? Number(r.Overall) : null,
      potential: r.Potential ? Number(r.Potential) : null,
      club,
      clubKey: normalizeTeam(club),
      position: (r.Position ?? "").trim(),
      jerseyNumber: (r["Jersey Number"] ?? "").trim(),
      height: (r.Height ?? "").trim(),
      weight: (r.Weight ?? "").trim(),
    });
  }

  return new DataStore(dedupeMatches(matches), players);
}

/**
 * Source preference when the same fixture appears in multiple datasets. Lower
 * number wins. The dedicated competition files carry round/state metadata, so
 * they are preferred over the cross-competition BR-Football aggregate.
 */
const SOURCE_PRIORITY: Record<string, number> = {
  "Brasileirao_Matches.csv": 0,
  "Brazilian_Cup_Matches.csv": 0,
  "Libertadores_Matches.csv": 0,
  "novo_campeonato_brasileiro.csv": 1,
  "BR-Football-Dataset.csv": 2,
};

/**
 * Collapse overlapping datasets that describe the same competition+season.
 *
 * The same Brasileirão season appears in up to three files, and the files spell
 * the same club with different words ("Atletico-MG" vs "Atletico Mineiro",
 * "Vasco" vs "Vasco da Gama"), so per-fixture name matching is unreliable.
 * Instead we pick exactly ONE source per (competition, season) bucket: the one
 * with the most matches (most complete), breaking ties by SOURCE_PRIORITY. This
 * is spelling-independent and prevents the double/triple counting that otherwise
 * inflates standings, head-to-head and goal averages.
 *
 * Matches without a parsed season cannot be bucketed and are always kept.
 */
function dedupeMatches(matches: Match[]): Match[] {
  // bucket key -> source -> matches
  const buckets = new Map<string, Map<string, Match[]>>();
  const undated: Match[] = [];

  for (const m of matches) {
    if (m.season == null) {
      undated.push(m);
      continue;
    }
    const bucketKey = `${m.competition}|${m.season}`;
    let bySource = buckets.get(bucketKey);
    if (!bySource) {
      bySource = new Map<string, Match[]>();
      buckets.set(bucketKey, bySource);
    }
    const arr = bySource.get(m.source);
    if (arr) arr.push(m);
    else bySource.set(m.source, [m]);
  }

  const kept: Match[] = [...undated];
  for (const bySource of buckets.values()) {
    let chosen: Match[] = [];
    let chosenSource = "";
    for (const [source, arr] of bySource) {
      const better =
        arr.length > chosen.length ||
        (arr.length === chosen.length &&
          (SOURCE_PRIORITY[source] ?? 9) < (SOURCE_PRIORITY[chosenSource] ?? 9));
      if (better) {
        chosen = arr;
        chosenSource = source;
      }
    }
    for (const m of chosen) kept.push(m);
  }

  return kept;
}
