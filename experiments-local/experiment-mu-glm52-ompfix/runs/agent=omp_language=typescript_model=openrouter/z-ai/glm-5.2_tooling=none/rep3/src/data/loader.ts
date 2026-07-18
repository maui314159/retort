/**
 * Brazilian Soccer MCP Server — CSV Loading & Normalization
 * -----------------------------------------------------------------------------
 * Context block:
 *   This module reads the six Kaggle CSV files from `data/kaggle/` and parses
 *   them into the unified `Match`/`Player` model from `types.ts`. It is the
 *   ONLY place that knows about per-file column names. Downstream query code
 *   operates solely on the normalized model.
 *
 *   Per-file responsibilities:
 *     • Brasileirao_Matches.csv      → competition "brasileirao", season col
 *     • Brazilian_Cup_Matches.csv    → "copa-do-brasil", `round` may be quoted
 *     • Libertadores_Matches.csv     → "libertadores", goals may be "-" (NA row)
 *     • novo_campeonato_brasileiro.csv → "brasileirao-historical", DD/MM/YYYY,
 *       Portuguese column names, Vencedor winner label, Arena stadium
 *     • BR-Football-Dataset.csv      → tournament column drives competition
 *       ("Serie A"/"Serie B"/"Serie C"/"Copa do Brasil"); extended stats present
 *     • fifa_data.csv                → players; has a UTF-8 BOM and a leading
 *       unnamed index column; skill cells may contain "+N" forms (stripped)
 *
 *   We use `csv-parse` (sync) with `columns:true` so each row becomes an
 *   object keyed by its header. The BOM is stripped from the fifa header so
 *   the first column doesn't get a `\ufeff` prefix. All numeric parsing is
 *   defensive: any unparseable cell becomes null rather than throwing.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { parse } from "csv-parse/sync";
import type {
  CompetitionInfo,
  CompetitionKey,
  Dataset,
  Match,
  Player,
  SourceKey,
} from "./types.js";
import { normalizeTeamName } from "./teams.js";
import { parseDate, parseDatetime } from "./dates.js";

const DEFAULT_DATA_DIR = "data/kaggle";
// Mutable so tests can point the loader at an alternate fixture directory.
let dataDir = DEFAULT_DATA_DIR;

/** Point the loader at a different data directory (test seam). Restores the
 * default when called with no argument. */
export function setDataDir(dir: string = DEFAULT_DATA_DIR): void {
  dataDir = dir;
}

/** Defensive integer/float parse: returns null for "", "-", "NA", NaN. */
function num(v: unknown): number | null {
  if (v == null) return null;
  const s = String(v).trim();
  if (s === "" || s === "-" || s.toLowerCase() === "na") return null;
  // Skill cells like "88+2": take the base integer.
  const base = s.match(/^(-?\d+(?:\.\d+)?)/);
  if (!base) return null;
  const n = Number(base[1]);
  return Number.isFinite(n) ? n : null;
}

/** Strip a BOM if present. */
function stripBom(buf: Buffer): string {
  if (buf.length >= 3 && buf[0] === 0xef && buf[1] === 0xbb && buf[2] === 0xbf) {
    return buf.slice(3).toString("utf8");
  }
  return buf.toString("utf8");
}


/** Parse a CSV file into records, stripping BOM from header. */
function loadCsv(name: string): Record<string, string>[] {
  const text = stripBom(readFileSync(join(dataDir, name)));
  const rows = parse(text, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    relax_quotes: true,
  }) as Record<string, string>[];
  return rows;
}

function rowId(source: SourceKey, i: number): string {
  return `${source}:${i}`;
}

// ---------------------------------------------------------------------------
// Per-dataset loaders
// ---------------------------------------------------------------------------

function loadBrasileirao(): Match[] {
  const rows = loadCsv("Brasileirao_Matches.csv");
  return rows.map((r, i) => {
    const homeRaw = r.home_team ?? "";
    const awayRaw = r.away_team ?? "";
    return {
      id: rowId("Brasileirao_Matches", i),
      source: "Brasileirao_Matches",
      competition: "brasileirao",
      competitionLabel: "Brasileirão Serie A",
      season: num(r.season),
      date: parseDate(r.datetime),
      datetime: parseDatetime(r.datetime),
      homeTeam: normalizeTeamName(homeRaw, r.home_team_state),
      awayTeam: normalizeTeamName(awayRaw, r.away_team_state),
      homeTeamRaw: homeRaw,
      awayTeamRaw: awayRaw,
      homeState: r.home_team_state ?? null,
      awayState: r.away_team_state ?? null,
      homeGoals: num(r.home_goal),
      awayGoals: num(r.away_goal),
      round: r.round ?? null,
      stage: null,
      stadium: null,
      htResult: null,
      atResult: null,
      homeCorners: null,
      awayCorners: null,
      homeShots: null,
      awayShots: null,
      homeAttacks: null,
      awayAttacks: null,
      totalCorners: null,
    };
  });
}

function loadCopaDoBrasil(): Match[] {
  const rows = loadCsv("Brazilian_Cup_Matches.csv");
  return rows.map((r, i) => {
    const homeRaw = r.home_team ?? "";
    const awayRaw = r.away_team ?? "";
    return {
      id: rowId("Brazilian_Cup_Matches", i),
      source: "Brazilian_Cup_Matches",
      competition: "copa-do-brasil",
      competitionLabel: "Copa do Brasil",
      season: num(r.season),
      date: parseDate(r.datetime),
      datetime: parseDatetime(r.datetime),
      homeTeam: normalizeTeamName(homeRaw),
      awayTeam: normalizeTeamName(awayRaw),
      homeTeamRaw: homeRaw,
      awayTeamRaw: awayRaw,
      homeState: null,
      awayState: null,
      homeGoals: num(r.home_goal),
      awayGoals: num(r.away_goal),
      round: r.round ?? null,
      stage: null,
      stadium: null,
      htResult: null,
      atResult: null,
      homeCorners: null,
      awayCorners: null,
      homeShots: null,
      awayShots: null,
      homeAttacks: null,
      awayAttacks: null,
      totalCorners: null,
    };
  });
}

function loadLibertadores(): Match[] {
  const rows = loadCsv("Libertadores_Matches.csv");
  return rows.map((r, i) => {
    const homeRaw = r.home_team ?? "";
    const awayRaw = r.away_team ?? "";
    return {
      id: rowId("Libertadores_Matches", i),
      source: "Libertadores_Matches",
      competition: "libertadores",
      competitionLabel: "Copa Libertadores",
      season: num(r.season),
      date: parseDate(r.datetime),
      datetime: parseDatetime(r.datetime),
      homeTeam: normalizeTeamName(homeRaw),
      awayTeam: normalizeTeamName(awayRaw),
      homeTeamRaw: homeRaw,
      awayTeamRaw: awayRaw,
      homeState: null,
      awayState: null,
      homeGoals: num(r.home_goal),
      awayGoals: num(r.away_goal),
      round: null,
      stage: r.stage ?? null,
      stadium: null,
      htResult: null,
      atResult: null,
      homeCorners: null,
      awayCorners: null,
      homeShots: null,
      awayShots: null,
      homeAttacks: null,
      awayAttacks: null,
      totalCorners: null,
    };
  });
}

function loadHistoricalBrasileirao(): Match[] {
  const rows = loadCsv("novo_campeonato_brasileiro.csv");
  return rows.map((r, i) => {
    const homeRaw = r.Equipe_mandante ?? "";
    const awayRaw = r.Equipe_visitante ?? "";
    return {
      id: rowId("novo_campeonato_brasileiro", i),
      source: "novo_campeonato_brasileiro",
      competition: "brasileirao-historical",
      competitionLabel: "Brasileirão (2003-2019)",
      season: num(r.Ano),
      date: parseDate(r.Data),
      datetime: parseDatetime(r.Data),
      homeTeam: normalizeTeamName(homeRaw, r.Mandante_UF),
      awayTeam: normalizeTeamName(awayRaw, r.Visitante_UF),
      homeTeamRaw: homeRaw,
      awayTeamRaw: awayRaw,
      homeState: r.Mandante_UF ?? null,
      awayState: r.Visitante_UF ?? null,
      homeGoals: num(r.Gols_mandante),
      awayGoals: num(r.Gols_visitante),
      round: r.Rodada ?? null,
      stage: null,
      stadium: r.Arena ?? null,
      htResult: null,
      atResult: null,
      homeCorners: null,
      awayCorners: null,
      homeShots: null,
      awayShots: null,
      homeAttacks: null,
      awayAttacks: null,
      totalCorners: null,
    };
  });
}

/** Map BR-Football-Dataset tournament column → competition key + label. */
function tournamentMap(t: string): {
  competition: CompetitionKey;
  label: string;
} {
  const s = (t ?? "").toLowerCase();
  if (s.includes("serie a")) return { competition: "serie-a", label: "Serie A" };
  if (s.includes("serie b")) return { competition: "serie-b", label: "Serie B" };
  if (s.includes("serie c")) return { competition: "serie-c", label: "Serie C" };
  if (s.includes("copa do brasil")) {
    return { competition: "copa-do-brasil-ext", label: "Copa do Brasil (extended)" };
  }
  return { competition: "serie-a", label: t || "Unknown" };
}

function loadExtendedStats(): Match[] {
  const rows = loadCsv("BR-Football-Dataset.csv");
  return rows.map((r, i) => {
    const homeRaw = r.home ?? "";
    const awayRaw = r.away ?? "";
    const t = tournamentMap(r.tournament ?? "");
    // date col is ISO; time col is "HH:MM:SS"
    const dateIso = parseDate(r.date);
    const timePart = (r.time ?? "").trim();
    let datetime: string | null = null;
    if (dateIso && timePart) {
      const m = timePart.match(/^(\d{1,2}):(\d{2})(?::(\d{2}))?$/);
      if (m) {
        datetime = `${dateIso}T${m[1].padStart(2, "0")}:${m[2]}:${m[3] ?? "00"}`;
      } else {
        datetime = dateIso;
      }
    } else if (dateIso) {
      datetime = dateIso;
    }
    return {
      id: rowId("BR-Football-Dataset", i),
      source: "BR-Football-Dataset",
      competition: t.competition,
      competitionLabel: t.label,
      season: dateIso ? Number(dateIso.slice(0, 4)) : null,
      date: dateIso,
      datetime,
      homeTeam: normalizeTeamName(homeRaw),
      awayTeam: normalizeTeamName(awayRaw),
      homeTeamRaw: homeRaw,
      awayTeamRaw: awayRaw,
      homeState: null,
      awayState: null,
      homeGoals: num(r.home_goal),
      awayGoals: num(r.away_goal),
      round: null,
      stage: null,
      stadium: null,
      htResult: r.ht_result ?? null,
      atResult: r.at_result ?? null,
      homeCorners: num(r.home_corner),
      awayCorners: num(r.away_corner),
      homeShots: num(r.home_shots),
      awayShots: num(r.away_shots),
      homeAttacks: num(r.home_attack),
      awayAttacks: num(r.away_attack),
      totalCorners: num(r.total_corners),
    };
  });
}

function loadPlayers(): Player[] {
  const rows = loadCsv("fifa_data.csv");
  return rows.map((r) => ({
    id: num(r.ID) ?? 0,
    name: r.Name ?? "",
    age: num(r.Age),
    nationality: r.Nationality ?? "",
    overall: num(r.Overall),
    potential: num(r.Potential),
    club: (r.Club ?? "").trim(),
    position: r.Position ?? "",
    jerseyNumber: num(r["Jersey Number"]),
    preferredFoot: r["Preferred Foot"] ?? null,
    height: r.Height ?? null,
    weight: r.Weight ?? null,
    crossing: num(r.Crossing),
    finishing: num(r.Finishing),
    dribbling: num(r.Dribbling),
    shortPassing: num(r.ShortPassing),
    longPassing: num(r.LongPassing),
    shotPower: num(r.ShotPower),
    internationalReputation: num(r["International Reputation"]),
  }));
}

// ---------------------------------------------------------------------------
// Catalog
// ---------------------------------------------------------------------------

function buildCompetitionInfo(matches: Match[]): CompetitionInfo[] {
  const map = new Map<string, CompetitionInfo>();
  for (const m of matches) {
    const key = `${m.source}:${m.competition}`;
    if (!map.has(key)) {
      map.set(key, {
        competition: m.competition,
        label: m.competitionLabel,
        source: m.source,
        seasons: [],
        matchCount: 0,
      });
    }
    const info = map.get(key)!;
    info.matchCount++;
    if (m.season != null && !info.seasons.includes(m.season)) {
      info.seasons.push(m.season);
    }
  }
  const infos = [...map.values()];
  for (const info of infos) info.seasons.sort((a, b) => a - b);
  return infos.sort((a, b) => a.label.localeCompare(b.label));
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/** Load the entire dataset (all 6 files). Called once at server startup. */
export function loadDataset(): Dataset {
  const matches: Match[] = [
    ...loadBrasileirao(),
    ...loadCopaDoBrasil(),
    ...loadLibertadores(),
    ...loadHistoricalBrasileirao(),
    ...loadExtendedStats(),
  ];
  const players = loadPlayers();
  const competitions = buildCompetitionInfo(matches);
  return { matches, players, competitions };
}

