/**
 * brazilian-soccer-mcp / src/loader.ts
 *
 * CSV loading, two-pass team resolution, and cross-file deduplication.
 *
 * Context block:
 * Reads the six Kaggle CSVs from a configurable data directory and projects
 * every row into the unified `Match` / `Player` shapes (types.ts). Each source
 * file has a different schema, so per-file adapters map native columns onto a
 * common intermediate shape carrying the extracted team `NameParts` (core +
 * state + display). Competition labels are canonicalized ("Serie A" →
 * "Brasileirão").
 *
 * Two-pass team resolution: distinct clubs share nicknames (Atlético-MG vs
 * Atlético-GO vs Athletico-PR; Botafogo-RJ vs Botafogo-PB; América-MG vs
 * América-RN), and state info is present as a column in some files but embedded
 * in the name ("Botafogo RJ", "Atletico Mineiro") or a parenthetical
 * ("Nacional (URU)") in others. Pass 1 tallies, per core, the set of states
 * seen; a core with ≥2 states is "ambiguous" and keyed `core-state`, while a
 * unique core is keyed by its bare core (so "Flamengo-RJ" and "Flamengo" both
 * key to "flamengo"). Pass 2 assigns each match side its disambiguated
 * `homeTeamKey`/`awayTeamKey` plus a `core` for query matching and a canonical
 * display name.
 *
 * Cross-file deduplication: the datasets overlap — the modern Brasileirão file
 * (2012-2022) overlaps the historical file (2003-2019) for 2012-2019, and the
 * extended-stats file (2014-2023) overlaps both the Brasileirão and Copa do
 * Brasil files. We load primary files first, restrict the historical file to
 * pre-2012 years (the modern file is authoritative for 2012+ and the two
 * disagree on dates/scores for ~20% of overlapping matches), then for the
 * extended-stats file merge its corners/shots/attacks onto surviving matches by
 * signature (dropping non-matching rows in already-covered years to avoid
 * double-counting, but adding 2023 and Serie B/C which have no other source).
 */

import { readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import Papa from "papaparse";
import type { Match, Player } from "./types.js";
import {
  canonicalCompetition,
  extractParts,
  parseDate,
  parseSeason,
  resolveClubKey,
  toFloat,
  toInt,
  type NameParts,
} from "./normalize.js";

/** Result of loading all datasets. */
export interface LoadedData {
  matches: Match[];
  players: Player[];
  competitions: string[];
  competitionCounts: Record<string, number>;
  competitionSeasons: Record<string, { min: number; max: number }>;
  duplicatesDropped: number;
}

/** Resolve the data directory, honoring the `BR_SOCCER_DATA_DIR` env override. */
export function resolveDataDir(override?: string): string {
  const dir = override ?? process.env.BR_SOCCER_DATA_DIR ?? "./data/kaggle";
  return resolve(dir);
}

/** Read+parse a CSV file into an array of string-keyed row objects. */
function parseCsv(filePath: string): Record<string, string>[] {
  const content = readFileSync(filePath, "utf8");
  const result = Papa.parse<Record<string, string>>(content, {
    header: true,
    skipEmptyLines: true,
    dynamicTyping: false,
  });
  return (result.data ?? []).filter(
    (r): r is Record<string, string> => r != null && typeof r === "object",
  );
}


/** Intermediate match before club-key resolution. */
interface IntermediateMatch {
  competition: string;
  sourceFile: string;
  date: string | null;
  rawDate: string;
  season: number | null;
  round: string | null;
  homeParts: NameParts;
  awayParts: NameParts;
  homeGoal: number | null;
  awayGoal: number | null;
  stage: string | null;
  venue: string | null;
  homeCorner: number | null;
  awayCorner: number | null;
  homeShots: number | null;
  awayShots: number | null;
  homeAttack: number | null;
  awayAttack: number | null;
  totalCorners: number | null;
  htResult: string | null;
  atResult: string | null;
  /** True for extended-stats rows whose (competition,season) is already covered by a primary source — merge-or-drop. */
  covered: boolean;
}

/** Build an IntermediateMatch from common fields + two NameParts. */
function makeIntermediate(
  partial: Omit<IntermediateMatch, "homeParts" | "awayParts" | "covered"> & {
    covered?: boolean;
  },
  homeParts: NameParts,
  awayParts: NameParts,
): IntermediateMatch {
  return { covered: false, ...partial, homeParts, awayParts };
}

// ---- Per-file adapters (produce IntermediateMatch[]) -------------------

function fromBrasileirao(rows: Record<string, string>[]): IntermediateMatch[] {
  return rows.map((r) =>
    makeIntermediate(
      {
        competition: "Brasileirão",
        sourceFile: "Brasileirao_Matches.csv",
        date: parseDate(r.datetime),
        rawDate: r.datetime ?? "",
        season: parseSeason(r.season),
        round: r.round != null && r.round !== "" ? String(r.round) : null,
        homeGoal: toInt(r.home_goal),
        awayGoal: toInt(r.away_goal),
        stage: null,
        venue: null,
        homeCorner: null,
        awayCorner: null,
        homeShots: null,
        awayShots: null,
        homeAttack: null,
        awayAttack: null,
        totalCorners: null,
        htResult: null,
        atResult: null,
      },
      extractParts(r.home_team ?? "", r.home_team_state),
      extractParts(r.away_team ?? "", r.away_team_state),
    ),
  );
}

function fromCup(rows: Record<string, string>[]): IntermediateMatch[] {
  return rows.map((r) =>
    makeIntermediate(
      {
        competition: "Copa do Brasil",
        sourceFile: "Brazilian_Cup_Matches.csv",
        date: parseDate(r.datetime),
        rawDate: r.datetime ?? "",
        season: parseSeason(r.season),
        round: r.round != null && r.round !== "" ? String(r.round) : null,
        homeGoal: toInt(r.home_goal),
        awayGoal: toInt(r.away_goal),
        stage: null,
        venue: null,
        homeCorner: null,
        awayCorner: null,
        homeShots: null,
        awayShots: null,
        homeAttack: null,
        awayAttack: null,
        totalCorners: null,
        htResult: null,
        atResult: null,
      },
      extractParts(r.home_team ?? ""),
      extractParts(r.away_team ?? ""),
    ),
  );
}

function fromLibertadores(rows: Record<string, string>[]): IntermediateMatch[] {
  return rows.map((r) =>
    makeIntermediate(
      {
        competition: "Libertadores",
        sourceFile: "Libertadores_Matches.csv",
        date: parseDate(r.datetime),
        rawDate: r.datetime ?? "",
        season: parseSeason(r.season),
        round: r.stage != null && r.stage !== "" ? String(r.stage) : null,
        homeGoal: toInt(r.home_goal),
        awayGoal: toInt(r.away_goal),
        stage: r.stage != null && r.stage !== "" ? String(r.stage) : null,
        venue: null,
        homeCorner: null,
        awayCorner: null,
        homeShots: null,
        awayShots: null,
        homeAttack: null,
        awayAttack: null,
        totalCorners: null,
        htResult: null,
        atResult: null,
      },
      extractParts(r.home_team ?? ""),
      extractParts(r.away_team ?? ""),
    ),
  );
}

function fromHistorical(rows: Record<string, string>[]): IntermediateMatch[] {
  return rows.map((r) =>
    makeIntermediate(
      {
        competition: "Brasileirão",
        sourceFile: "novo_campeonato_brasileiro.csv",
        date: parseDate(r.Data),
        rawDate: r.Data ?? "",
        season: parseSeason(r.Ano),
        round: r.Rodada != null && r.Rodada !== "" ? String(r.Rodada) : null,
        homeGoal: toInt(r.Gols_mandante),
        awayGoal: toInt(r.Gols_visitante),
        stage: null,
        venue: r.Arena ?? null,
        homeCorner: null,
        awayCorner: null,
        homeShots: null,
        awayShots: null,
        homeAttack: null,
        awayAttack: null,
        totalCorners: null,
        htResult: null,
        atResult: null,
      },
      extractParts(r.Equipe_mandante ?? "", r.Mandante_UF),
      extractParts(r.Equipe_visitante ?? "", r.Visitante_UF),
    ),
  );
}

function fromExtended(rows: Record<string, string>[]): IntermediateMatch[] {
  return rows.map((r) => {
    const date = parseDate(r.date);
    const year = date ? Number(date.slice(0, 4)) : NaN;
    return makeIntermediate(
      {
        competition: canonicalCompetition(r.tournament ?? ""),
        sourceFile: "BR-Football-Dataset.csv",
        date,
        rawDate: r.date ?? "",
        season: Number.isFinite(year) ? year : null,
        round: null,
        homeGoal: toFloat(r.home_goal),
        awayGoal: toFloat(r.away_goal),
        stage: null,
        venue: null,
        homeCorner: toFloat(r.home_corner),
        awayCorner: toFloat(r.away_corner),
        homeShots: toFloat(r.home_shots),
        awayShots: toFloat(r.away_shots),
        homeAttack: toFloat(r.home_attack),
        awayAttack: toFloat(r.away_attack),
        totalCorners: toFloat(r.total_corners),
        htResult: r.ht_result ?? null,
        atResult: r.at_result ?? null,
      },
      extractParts(r.home ?? ""),
      extractParts(r.away ?? ""),
    );
  });
}

function fromFifa(rows: Record<string, string>[]): Player[] {
  const players: Player[] = [];
  for (const r of rows) {
    const name = r.Name ?? "";
    if (name.trim() === "") continue;
    const club = r.Club ?? "";
    players.push({
      id: toInt(r.ID) ?? players.length,
      name,
      age: toInt(r.Age),
      nationality: r.Nationality ?? "",
      overall: toInt(r.Overall),
      potential: toInt(r.Potential),
      club,
      clubKey: extractParts(club).core,
      position: (r.Position ?? "").toUpperCase(),
      jerseyNumber: toInt(r["Jersey Number"]),
      value: r.Value ?? "",
      wage: r.Wage ?? "",
    });
  }
  return players;
}

/** Safely load+adapt a file, returning [] on missing/unreadable. */
function loadFile(
  dir: string,
  file: string,
  adapter: (rows: Record<string, string>[]) => IntermediateMatch[],
): IntermediateMatch[] {
  try {
    return adapter(parseCsv(join(dir, file)));
  } catch (err) {
    console.error(`[loader] skipping ${file}: ${(err as Error).message}`);
    return [];
  }
}

/** Build a dedup signature for a resolved match. */
function matchSignature(m: {
  competition: string;
  date: string | null;
  rawDate: string;
  homeTeamKey: string;
  awayTeamKey: string;
  homeGoal: number | null;
  awayGoal: number | null;
}): string {
  const date = m.date ?? m.rawDate ?? "?";
  return `${m.competition}|${date}|${m.homeTeamKey}|${m.awayTeamKey}|${m.homeGoal ?? "?"}|${m.awayGoal ?? "?"}`;
}

/**
 * Resolve intermediate matches into final Match objects with disambiguated
 * club keys, canonical display names, and deduplication state.
 */
function resolveMatches(
  intermediates: IntermediateMatch[],
  duplicatesDroppedRef: { count: number },
): Match[] {
  // Pass 1: tally states per core, and display-base frequency per (core,state).
  const statesByCore = new Map<string, Set<string>>();
  const stateFreqByCore = new Map<string, Map<string, number>>();
  const displayFreq = new Map<string, Map<string, number>>(); // clubKey-ish not known yet; key by core|state

  const tally = (parts: NameParts): void => {
    if (!statesByCore.has(parts.core)) statesByCore.set(parts.core, new Set());
    if (!stateFreqByCore.has(parts.core)) stateFreqByCore.set(parts.core, new Map());
    if (parts.state) {
      statesByCore.get(parts.core)!.add(parts.state);
      const f = stateFreqByCore.get(parts.core)!;
      f.set(parts.state, (f.get(parts.state) ?? 0) + 1);
    }
  };
  for (const im of intermediates) {
    tally(im.homeParts);
    tally(im.awayParts);
  }

  const ambiguous = new Set<string>();
  for (const [core, states] of statesByCore) {
    if (states.size >= 2) ambiguous.add(core);
  }

  // Majority state per core (fallback for ambiguous occurrences lacking state).
  const majorityState = new Map<string, string | null>();
  for (const [core, freq] of stateFreqByCore) {
    let best: string | null = null;
    let bestN = -1;
    for (const [st, n] of freq) {
      if (n > bestN) {
        best = st;
        bestN = n;
      }
    }
    majorityState.set(core, best);
  }

  // Resolve club keys and tally display frequency per clubKey.
  const resolved = intermediates.map((im) => {
    const homeKey = resolveClubKey(
      im.homeParts.core,
      im.homeParts.state,
      ambiguous.has(im.homeParts.core),
      majorityState.get(im.homeParts.core) ?? null,
    );
    const awayKey = resolveClubKey(
      im.awayParts.core,
      im.awayParts.state,
      ambiguous.has(im.awayParts.core),
      majorityState.get(im.awayParts.core) ?? null,
    );
    return { im, homeKey, awayKey };
  });

  for (const { im, homeKey, awayKey } of resolved) {
    for (const [key, parts] of [
      [homeKey, im.homeParts],
      [awayKey, im.awayParts],
    ] as const) {
      if (!displayFreq.has(key)) displayFreq.set(key, new Map());
      const f = displayFreq.get(key)!;
      f.set(parts.display, (f.get(parts.display) ?? 0) + 1);
    }
  }

  // Canonical display per clubKey (most frequent display base, +state if ambiguous).
  const displayByKey = new Map<string, string>();
  for (const [key, freq] of displayFreq) {
    let best = "";
    let bestN = -1;
    for (const [d, n] of freq) {
      if (n > bestN) {
        best = d;
        bestN = n;
      }
    }
    const core = key.includes("-") ? key.slice(0, key.lastIndexOf("-")) : key;
    const stateSuffix = key.includes("-") ? key.slice(key.lastIndexOf("-") + 1).toUpperCase() : "";
    displayByKey.set(
      key,
      ambiguous.has(core) && stateSuffix ? `${best}-${stateSuffix}` : best,
    );
  }

  // Pass 2: emit Match objects.
  const matches: Match[] = [];
  const sigToIndex = new Map<string, number>();

  const emit = (im: IntermediateMatch, homeKey: string, awayKey: string): void => {
    matches.push({
      competition: im.competition,
      sourceFile: im.sourceFile,
      date: im.date,
      rawDate: im.rawDate,
      season: im.season,
      round: im.round,
      homeTeam: displayByKey.get(homeKey) ?? im.homeParts.display,
      awayTeam: displayByKey.get(awayKey) ?? im.awayParts.display,
      homeTeamKey: homeKey,
      awayTeamKey: awayKey,
      homeTeamCore: im.homeParts.core,
      awayTeamCore: im.awayParts.core,
      homeState: im.homeParts.state,
      awayState: im.awayParts.state,
      homeGoal: im.homeGoal,
      awayGoal: im.awayGoal,
      stage: im.stage,
      venue: im.venue,
      homeCorner: im.homeCorner,
      awayCorner: im.awayCorner,
      homeShots: im.homeShots,
      awayShots: im.awayShots,
      homeAttack: im.homeAttack,
      awayAttack: im.awayAttack,
      totalCorners: im.totalCorners,
      htResult: im.htResult,
      atResult: im.atResult,
    });
  };

  // Dedup helpers (operate on resolved keys).
  const sigOf = (im: IntermediateMatch, homeKey: string, awayKey: string) =>
    matchSignature({
      competition: im.competition,
      date: im.date,
      rawDate: im.rawDate,
      homeTeamKey: homeKey,
      awayTeamKey: awayKey,
      homeGoal: im.homeGoal,
      awayGoal: im.awayGoal,
    });

  // Add primary: drop if signature already present.
  const addPrimary = (im: IntermediateMatch, homeKey: string, awayKey: string): void => {
    const sig = sigOf(im, homeKey, awayKey);
    if (sigToIndex.has(sig)) {
      duplicatesDroppedRef.count++;
      return;
    }
    sigToIndex.set(sig, matches.length);
    emit(im, homeKey, awayKey);
  };

  // Add extended: merge onto existing match if signature present, else add.
  const addExtended = (im: IntermediateMatch, homeKey: string, awayKey: string): void => {
    const sig = sigOf(im, homeKey, awayKey);
    const existing = sigToIndex.get(sig);
    if (existing != null) {
      const t = matches[existing];
      if (t) {
        t.homeCorner = im.homeCorner ?? t.homeCorner;
        t.awayCorner = im.awayCorner ?? t.awayCorner;
        t.homeShots = im.homeShots ?? t.homeShots;
        t.awayShots = im.awayShots ?? t.awayShots;
        t.homeAttack = im.homeAttack ?? t.homeAttack;
        t.awayAttack = im.awayAttack ?? t.awayAttack;
        t.totalCorners = im.totalCorners ?? t.totalCorners;
        t.htResult = im.htResult ?? t.htResult;
        t.atResult = im.atResult ?? t.atResult;
      }
      return;
    }
    sigToIndex.set(sig, matches.length);
    emit(im, homeKey, awayKey);
  };

  // Covered extended row: merge stats if signature matches, else drop (no dup).
  const addCoveredExtended = (im: IntermediateMatch, homeKey: string, awayKey: string): void => {
    const sig = sigOf(im, homeKey, awayKey);
    const existing = sigToIndex.get(sig);
    if (existing != null) {
      addExtended(im, homeKey, awayKey); // merges onto existing match
    } else {
      duplicatesDroppedRef.count++;
    }
  };

  for (const { im, homeKey, awayKey } of resolved) {
    const isExtended = im.sourceFile === "BR-Football-Dataset.csv";
    const handler = im.covered
      ? addCoveredExtended
      : isExtended
        ? addExtended
        : addPrimary;
    handler(im, homeKey, awayKey);
  }

  return matches;
}

/**
 * Load all six datasets from `dataDir` with two-pass team resolution and
 * cross-file deduplication. Missing files are skipped (with a warning on
 * stderr) so the server still starts with partial data.
 *
 * Load order is deliberate: primary match files first, then the historical
 * file restricted to pre-2012 years (the modern Brasileirão file is
 * authoritative for 2012+), then the extended-stats file (adds 2023 + Serie B/C
 * and attaches corners/shots/attacks to surviving matches). The extended-stats
 * rows for Brasileirão/Copa in already-covered years merge-or-drop to avoid
 * double-counting.
 */
export function loadData(dataDir?: string): LoadedData {
  const dir = resolveDataDir(dataDir);

  const intermediates: IntermediateMatch[] = [];
  const MODERN_BRASILEIRAO_START = 2012;
  const OVERLAPPING_COMPETITIONS = new Set(["Brasileirão", "Copa do Brasil"]);

  // 1. Primary match files.
  intermediates.push(...loadFile(dir, "Brasileirao_Matches.csv", fromBrasileirao));
  intermediates.push(...loadFile(dir, "Brazilian_Cup_Matches.csv", fromCup));
  intermediates.push(...loadFile(dir, "Libertadores_Matches.csv", fromLibertadores));

  // 2. Historical Brasileirão, restricted to pre-modern years (2003-2011).
  for (const im of loadFile(dir, "novo_campeonato_brasileiro.csv", fromHistorical)) {
    if (im.season != null && im.season >= MODERN_BRASILEIRAO_START) continue;
    intermediates.push(im);
  }

  // 3. Extended-stats file. For Brasileirão/Copa rows whose (competition,season)
  //    is already covered by a primary source, mark `covered` so resolveMatches
  //    merges their stats onto the surviving match (or drops if no signature
  //    match) instead of double-counting. Uncovered rows (2023, Serie B/C) are
  //    added as new matches carrying their extended stats.
  const primaryCovered = new Set<string>();
  for (const im of intermediates) {
    if (im.season != null) primaryCovered.add(`${im.competition}|${im.season}`);
  }

  const extRows = loadFile(dir, "BR-Football-Dataset.csv", fromExtended);
  const droppedRef = { count: 0 };
  for (const im of extRows) {
    im.covered =
      im.season != null &&
      OVERLAPPING_COMPETITIONS.has(im.competition) &&
      primaryCovered.has(`${im.competition}|${im.season}`);
    intermediates.push(im);
  }

  const matches = resolveMatches(intermediates, droppedRef);

  // Players
  let players: Player[] = [];
  try {
    players = fromFifa(parseCsv(join(dir, "fifa_data.csv")));
  } catch (err) {
    console.error(`[loader] skipping fifa_data.csv: ${(err as Error).message}`);
  }

  // Competition rollups
  const competitionCounts: Record<string, number> = {};
  const competitionSeasons: Record<string, { min: number; max: number }> = {};
  for (const m of matches) {
    competitionCounts[m.competition] = (competitionCounts[m.competition] ?? 0) + 1;
    if (m.season != null) {
      const cur = competitionSeasons[m.competition];
      if (!cur) competitionSeasons[m.competition] = { min: m.season, max: m.season };
      else {
        if (m.season < cur.min) cur.min = m.season;
        if (m.season > cur.max) cur.max = m.season;
      }
    }
  }
  const competitions = Object.keys(competitionCounts).sort();

  return {
    matches,
    players,
    competitions,
    competitionCounts,
    competitionSeasons,
    duplicatesDropped: droppedRef.count,
  };
}
