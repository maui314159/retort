/**
 * CSV loading and cross-file normalization.
 *
 * Reads all six Kaggle CSVs from `data/kaggle/` and normalizes every row
 * into the unified {@link Match} / {@link Player} model, then builds a
 * team -> matches index so query services never re-scan files.
 *
 * Provenance is kept on every record (`source`) and row counts are
 * reported in `loadedFiles` so the MCP `dataset_summary` tool can show
 * data coverage.
 */
import { readFile } from "node:fs/promises";
import path from "node:path";
import { parse } from "csv-parse/sync";
import type { Dataset, Match, Player, SourceFile } from "./types.js";
import {
  canonicalTeamKey,
  canonicalDisplay,
  parseDate,
  toFloat,
  toInt,
} from "./normalize.js";

type Row = Record<string, string>;

/** A match before canonical club keys are attached. */
type RawMatch = Omit<Match, "homeKey" | "awayKey">;

function readCsv(rows: Row[]): Row[] {
  return rows;
}

async function loadRows(file: SourceFile, dir: string): Promise<Row[]> {
  const full = path.join(dir, file);
  const content = await readFile(full, "utf-8");
  return readCsv(
    parse(content, {
      columns: true,
      skip_empty_lines: true,
      relax_column_count: true,
      trim: true,
      bom: true,
    }) as Row[],
  );
}

/* ---------- per-file normalizers ---------- */

function fromBrasileirao(r: Row, i: number): RawMatch | null {
  const homeGoals = toInt(r.home_goal);
  const awayGoals = toInt(r.away_goal);
  if (homeGoals === null || awayGoals === null) return null;
  return {
    id: `brasileirao#${i}`,
    date: parseDate(r.datetime),
    season: toInt(r.season),
    competition: "Brasileirão Série A",
    homeTeam: canonicalDisplay(r.home_team),
    awayTeam: canonicalDisplay(r.away_team),
    homeTeamRaw: r.home_team,
    awayTeamRaw: r.away_team,
    homeGoals,
    awayGoals,
    round: r.round ?? null,
    stage: null,
    arena: null,
    source: "Brasileirao_Matches.csv",
  };
}

function fromCopaDoBrasil(r: Row, i: number): RawMatch | null {
  const homeGoals = toInt(r.home_goal);
  const awayGoals = toInt(r.away_goal);
  if (homeGoals === null || awayGoals === null) return null;
  const round = (r.round ?? "").trim();
  return {
    id: `copa-do-brasil#${i}`,
    date: parseDate(r.datetime),
    season: toInt(r.season),
    competition: "Copa do Brasil",
    homeTeam: canonicalDisplay(r.home_team),
    awayTeam: canonicalDisplay(r.away_team),
    homeTeamRaw: r.home_team,
    awayTeamRaw: r.away_team,
    homeGoals,
    awayGoals,
    round: round || null,
    // In this file the final rounds are numbered 7 (semis) and 8 (final).
    stage: round === "8" ? "final" : round === "7" ? "semi-final" : null,
    arena: null,
    source: "Brazilian_Cup_Matches.csv",
  };
}

function fromLibertadores(r: Row, i: number): RawMatch | null {
  const homeGoals = toInt(r.home_goal);
  const awayGoals = toInt(r.away_goal);
  if (homeGoals === null || awayGoals === null) return null;
  return {
    id: `libertadores#${i}`,
    date: parseDate(r.datetime),
    season: toInt(r.season),
    competition: "Copa Libertadores",
    homeTeam: canonicalDisplay(r.home_team),
    awayTeam: canonicalDisplay(r.away_team),
    homeTeamRaw: r.home_team,
    awayTeamRaw: r.away_team,
    homeGoals,
    awayGoals,
    round: null,
    stage: (r.stage ?? "").trim() || null,
    arena: null,
    source: "Libertadores_Matches.csv",
  };
}

function fromBrFootball(r: Row, i: number): RawMatch | null {
  const homeGoals = toFloat(r.home_goal);
  const awayGoals = toFloat(r.away_goal);
  if (homeGoals === null || awayGoals === null) return null;
  const tournament = (r.tournament ?? "").trim();
  const competition =
    tournament === "Serie A"
      ? "Brasileirão Série A"
      : tournament === "Serie B"
        ? "Brasileirão Série B"
        : tournament === "Serie C"
          ? "Brasileirão Série C"
          : tournament || "Unknown";
  return {
    id: `br-football#${i}`,
    date: parseDate(r.date),
    season: r.date ? toInt(r.date.slice(0, 4)) : null,
    competition,
    homeTeam: canonicalDisplay(r.home),
    awayTeam: canonicalDisplay(r.away),
    homeTeamRaw: r.home,
    awayTeamRaw: r.away,
    homeGoals,
    awayGoals,
    round: null,
    stage: null,
    arena: null,
    source: "BR-Football-Dataset.csv",
    stats: {
      homeCorners: toFloat(r.home_corner) ?? undefined,
      awayCorners: toFloat(r.away_corner) ?? undefined,
      homeShots: toFloat(r.home_shots) ?? undefined,
      awayShots: toFloat(r.away_shots) ?? undefined,
      homeAttacks: toFloat(r.home_attack) ?? undefined,
      awayAttacks: toFloat(r.away_attack) ?? undefined,
    },
  };
}

function fromNovoBrasileiro(r: Row, i: number): RawMatch | null {
  const homeGoals = toInt(r.Gols_mandante);
  const awayGoals = toInt(r.Gols_visitante);
  if (homeGoals === null || awayGoals === null) return null;
  return {
    id: `novo-brasileiro#${i}`,
    date: parseDate(r.Data),
    season: toInt(r.Ano),
    competition: "Brasileirão Série A",
    homeTeam: canonicalDisplay(r.Equipe_mandante),
    awayTeam: canonicalDisplay(r.Equipe_visitante),
    homeTeamRaw: r.Equipe_mandante,
    awayTeamRaw: r.Equipe_visitante,
    homeGoals,
    awayGoals,
    round: r.Rodada ?? null,
    stage: null,
    arena: (r.Arena ?? "").trim() || null,
    source: "novo_campeonato_brasileiro.csv",
  };
}

function fromFifa(r: Row): Player | null {
  const id = toInt(r.ID);
  if (id === null || !r.Name) return null;
  const num = (k: string) => toInt(r[k]) ?? undefined;
  return {
    id,
    name: r.Name.trim(),
    age: toInt(r.Age),
    nationality: (r.Nationality ?? "").trim(),
    overall: toInt(r.Overall),
    potential: toInt(r.Potential),
    club: (r.Club ?? "").trim() || null,
    position: (r.Position ?? "").trim() || null,
    jerseyNumber: toInt(r["Jersey Number"]),
    height: (r.Height ?? "").trim() || null,
    weight: (r.Weight ?? "").trim() || null,
    preferredFoot: (r["Preferred Foot"] ?? "").trim() || null,
    skills: {
      crossing: num("Crossing"),
      finishing: num("Finishing"),
      dribbling: num("Dribbling"),
      shortPassing: num("ShortPassing"),
      ballControl: num("BallControl"),
      sprintSpeed: num("SprintSpeed"),
      shotPower: num("ShotPower"),
      longShots: num("LongShots"),
      gkDiving: num("GKDiving"),
    },
  };
}

/* ---------- public API ---------- */

export const DEFAULT_DATA_DIR = path.resolve(
  path.dirname(new URL(import.meta.url).pathname),
  "..",
  "data",
  "kaggle",
);

/**
 * Load every CSV into the unified dataset. Missing files are skipped with
 * a warning on stderr so the server still starts with partial data.
 */
export async function loadDataset(
  dataDir: string = DEFAULT_DATA_DIR,
): Promise<Dataset> {
  const rawMatches: RawMatch[] = [];
  const players: Player[] = [];
  const loadedFiles: Dataset["loadedFiles"] = [];

  const loaders: [SourceFile, (rows: Row[]) => void][] = [
    [
      "Brasileirao_Matches.csv",
      (rows) =>
        rows.forEach((r, i) => {
          const m = fromBrasileirao(r, i);
          if (m) rawMatches.push(m);
        }),
    ],
    [
      "Brazilian_Cup_Matches.csv",
      (rows) =>
        rows.forEach((r, i) => {
          const m = fromCopaDoBrasil(r, i);
          if (m) rawMatches.push(m);
        }),
    ],
    [
      "Libertadores_Matches.csv",
      (rows) =>
        rows.forEach((r, i) => {
          const m = fromLibertadores(r, i);
          if (m) rawMatches.push(m);
        }),
    ],
    [
      "BR-Football-Dataset.csv",
      (rows) =>
        rows.forEach((r, i) => {
          const m = fromBrFootball(r, i);
          if (m) rawMatches.push(m);
        }),
    ],
    [
      "novo_campeonato_brasileiro.csv",
      (rows) =>
        rows.forEach((r, i) => {
          const m = fromNovoBrasileiro(r, i);
          if (m) rawMatches.push(m);
        }),
    ],
    [
      "fifa_data.csv",
      (rows) =>
        rows.forEach((r) => {
          const p = fromFifa(r);
          if (p) players.push(p);
        }),
    ],
  ];

  for (const [file, apply] of loaders) {
    try {
      const rows = await loadRows(file, dataDir);
      apply(rows);
      loadedFiles.push({ file, rows: rows.length });
    } catch (err) {
      console.error(`[loader] could not load ${file}: ${(err as Error).message}`);
    }
  }

  // Attach canonical club keys (cross-file identity).
  const matches: Match[] = rawMatches.map((m) => ({
    ...m,
    homeKey: canonicalTeamKey(m.homeTeamRaw),
    awayKey: canonicalTeamKey(m.awayTeamRaw),
  }));

  // Cross-file dedupe: the same real-world match appears in up to three
  // files (e.g. a 2019 Brasileirão game is in Brasileirao_Matches.csv,
  // novo_campeonato_brasileiro.csv AND BR-Football-Dataset.csv), but the
  // sources routinely disagree on the exact DATE by a day or two, so
  // identity is (competition, season, home, away, score) instead of
  // (date, home, away). In league play an ordered pair is unique per
  // season; in two-legged cup ties the score disambiguates. One
  // knowledge-graph node per real match; attributes are merged.
  const byKey = new Map<string, Match>();
  for (const m of matches) {
    const key = [
      m.competition,
      m.season ?? m.date ?? "?",
      m.homeKey,
      m.awayKey,
      m.homeGoals,
      m.awayGoals,
    ].join("|");
    const existing = byKey.get(key);
    if (!existing) {
      byKey.set(key, m);
      continue;
    }
    // Merge: fill gaps from the duplicate record.
    existing.round ??= m.round;
    existing.stage ??= m.stage;
    existing.arena ??= m.arena;
    existing.season ??= m.season;
    if (!existing.stats && m.stats) existing.stats = m.stats;
    existing.id += `|${m.id}`;
  }
  const uniqueMatches = [...byKey.values()];

  // Sort matches chronologically (null dates last).
  uniqueMatches.sort((a, b) => (a.date ?? "9999").localeCompare(b.date ?? "9999"));

  // Team index: canonical key -> positions in `matches`.
  const teamIndex = new Map<string, number[]>();
  uniqueMatches.forEach((m, i) => {
    for (const key of [m.homeKey, m.awayKey]) {
      if (!key) continue;
      const arr = teamIndex.get(key);
      if (arr) arr.push(i);
      else teamIndex.set(key, [i]);
    }
  });

  return { matches: uniqueMatches, players, teamIndex, loadedFiles };
}
