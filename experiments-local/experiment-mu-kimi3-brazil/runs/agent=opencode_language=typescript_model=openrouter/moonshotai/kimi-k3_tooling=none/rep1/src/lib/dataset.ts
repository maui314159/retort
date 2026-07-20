/**
 * Dataset loader: reads the six Kaggle CSV files, normalizes every row
 * into canonical Match / Player records and merges duplicate matches
 * that appear in more than one file (datasets overlap heavily between
 * 2014-2022).
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { parse } from "csv-parse/sync";
import {
  Competition,
  Match,
  MatchStats,
  Player,
  Team,
} from "./types.js";
import { parseDateTime } from "./dates.js";
import { TeamRegistry } from "./teams.js";
import { normalizeText } from "./text.js";

export const DATA_FILES = {
  brasileirao: "Brasileirao_Matches.csv",
  copaDoBrasil: "Brazilian_Cup_Matches.csv",
  libertadores: "Libertadores_Matches.csv",
  extended: "BR-Football-Dataset.csv",
  historical: "novo_campeonato_brasileiro.csv",
  fifa: "fifa_data.csv",
} as const;

/** Locate the data/kaggle directory (env override, cwd, or module-relative). */
export function resolveDataDir(): string {
  if (process.env.DATA_DIR && fs.existsSync(process.env.DATA_DIR)) {
    return process.env.DATA_DIR;
  }
  const here = path.dirname(fileURLToPath(import.meta.url));
  const candidates = [
    path.resolve(process.cwd(), "data", "kaggle"),
    path.resolve(here, "..", "..", "data", "kaggle"), // from src/lib or dist/lib
    path.resolve(here, "..", "..", "..", "data", "kaggle"),
  ];
  for (const c of candidates) {
    if (fs.existsSync(path.join(c, DATA_FILES.brasileirao))) return c;
  }
  throw new Error(
    `Could not locate data/kaggle directory. Set DATA_DIR. Tried: ${candidates.join(", ")}`,
  );
}

function readCsv(dataDir: string, file: string): Record<string, string>[] {
  const raw = fs.readFileSync(path.join(dataDir, file), "utf-8");
  return parse(raw, {
    columns: true,
    skip_empty_lines: true,
    relax_column_count: true,
    trim: true,
    bom: true,
  }) as Record<string, string>[];
}

function parseGoals(raw: string | undefined | null): number | null {
  if (raw === undefined || raw === null) return null;
  const s = String(raw).trim();
  if (s === "" || s.toUpperCase() === "NA") return null;
  const n = Number(s);
  return Number.isFinite(n) ? Math.round(n) : null;
}

function parseIntOrNull(raw: string | undefined | null): number | null {
  if (raw === undefined || raw === null) return null;
  const s = String(raw).trim();
  if (s === "" || s.toUpperCase() === "NA") return null;
  const n = Number(s);
  return Number.isFinite(n) ? Math.trunc(n) : null;
}

function parseSeason(raw: string | undefined | null): number | null {
  return parseIntOrNull(raw);
}

function num(raw: string | undefined | null): number | null {
  if (raw === undefined || raw === null || String(raw).trim() === "") return null;
  const n = Number(String(raw).trim());
  return Number.isFinite(n) ? n : null;
}

/** Parse a float-ish score like "1.0" into half-time goals. */
function halfTime(raw: string | undefined | null): number | null {
  return num(raw);
}

export interface Dataset {
  matches: Match[];
  players: Player[];
  teams: TeamRegistry;
  /** Per-file row counts actually loaded. */
  loadReport: Record<string, number>;
}

interface MatchDraft {
  competition: Competition;
  season: number | null;
  round: string | null;
  date: string | null;
  time: string | null;
  home: Team;
  away: Team;
  homeGoals: number | null;
  awayGoals: number | null;
  stadium: string | null;
  stats: MatchStats | null;
  source: string;
}

function dedupeKey(d: MatchDraft): string {
  return [
    d.competition,
    d.date ?? "unknown-date",
    d.home.key,
    d.away.key,
  ].join("|");
}

/**
 * Known mislabeled rows in the source files, skipped at load time.
 * BR-Football-Dataset.csv row "2016-01-30, Brasilia FC 1-1 CA Taguatinga"
 * is labeled "Serie A" — neither club has ever played Série A (it is a
 * 2016 Copa do Brasil qualifying-round tie).
 */
const SOURCE_DATA_EXCLUSIONS: { date: string; home: string; away: string }[] = [
  { date: "2016-01-30", home: "Brasilia FC", away: "CA Taguatinga" },
];

function isExcluded(dt: ReturnType<typeof parseDateTime>, home: string, away: string): boolean {
  return SOURCE_DATA_EXCLUSIONS.some(
    (e) => e.date === dt?.date && e.home === home.trim() && e.away === away.trim(),
  );
}

function isoDayNumber(date: string): number {
  return Date.parse(`${date}T00:00:00Z`) / 86_400_000;
}

function mergeMatchInto(target: Match, d: MatchDraft | Match, source: string): void {
  if (!target.sources.includes(source)) target.sources.push(source);
  target.round ??= d.round;
  target.stadium ??= d.stadium;
  target.time ??= d.time;
  target.season ??= d.season;
  target.homeGoals ??= d.homeGoals;
  target.awayGoals ??= d.awayGoals;
  target.stats ??= d.stats;
}

/**
 * Second dedupe pass: datasets occasionally record the same fixture one or
 * two days apart (reschedules, timezone cuts), and the extended dataset
 * labels matches by calendar year — so the COVID-delayed 2020 season,
 * played into early 2021, carries a different "season" than the canonical
 * files. Group by (competition, home, away) only — a real fixture occurs
 * at most once per season with the same home/away assignment, and distinct
 * seasons are always far more than two days apart — then merge records
 * whose dates differ by at most `maxDaysApart`. Records loaded first
 * (canonical files with explicit season columns) win, so merged fixtures
 * keep the correct season.
 */
function fuzzyMergeFixtures(matches: Map<string, Match>, maxDaysApart = 2): Map<string, Match> {
  const byFixture = new Map<string, Match[]>();
  for (const m of matches.values()) {
    if (m.date === null) continue;
    const key = [m.competition, m.homeTeam.key, m.awayTeam.key].join("|");
    if (!byFixture.has(key)) byFixture.set(key, []);
    byFixture.get(key)!.push(m);
  }
  const dropped = new Set<string>();
  for (const group of byFixture.values()) {
    if (group.length < 2) continue;
    // Multi-anchor clustering in load order (canonical sources first): a
    // record joins the first cluster within `maxDaysApart`, otherwise it
    // starts a new cluster (e.g. the same fixture in a different season).
    const anchors: Match[] = [];
    for (const m of group) {
      let target: Match | null = null;
      for (const a of anchors) {
        if (Math.abs(isoDayNumber(m.date!) - isoDayNumber(a.date!)) <= maxDaysApart) {
          target = a;
          break;
        }
      }
      if (target) {
        for (const s of m.sources) mergeMatchInto(target, m, s);
        dropped.add(m.id);
      } else {
        anchors.push(m);
      }
    }
  }

  // Stale-schedule pass: postponed matches appear as an unplayed record
  // (scheduled date, NA goals) in one file and as the actually-played
  // record (later date) in another. A fixture occurs at most once per
  // season per home/away pair, so an unplayed record that has a played
  // counterpart in the same season (or within 60 days) is a stale
  // schedule entry — fold it into the played record. Matches that were
  // genuinely never played (e.g. Chapecoense x Atlético-MG, 2016 round 38)
  // have no played counterpart and survive untouched.
  for (const group of byFixture.values()) {
    const playedRecords = group.filter(
      (m) => !dropped.has(m.id) && m.homeGoals !== null && m.awayGoals !== null,
    );
    if (playedRecords.length === 0) continue;
    for (const m of group) {
      if (dropped.has(m.id) || (m.homeGoals !== null && m.awayGoals !== null)) continue;
      const target = playedRecords.find(
        (p) =>
          (m.season !== null && p.season === m.season) ||
          Math.abs(isoDayNumber(p.date!) - isoDayNumber(m.date!)) <= 60,
      );
      if (target) {
        for (const s of m.sources) mergeMatchInto(target, m, s);
        dropped.add(m.id);
      }
    }
  }
  if (dropped.size === 0) return matches;
  const result = new Map<string, Match>();
  for (const [key, m] of matches) {
    if (!dropped.has(m.id)) result.set(key, m);
  }
  return result;
}

/** Load every CSV file and return the unified, deduplicated dataset. */
export function loadDataset(dataDir?: string): Dataset {
  const dir = dataDir ?? resolveDataDir();
  const teams = new TeamRegistry();
  const matches = new Map<string, Match>();
  const loadReport: Record<string, number> = {};
  let counter = 0;

  const addMatch = (d: MatchDraft): void => {
    const key = dedupeKey(d);
    const existing = matches.get(key);
    if (existing) {
      // Merge: fill gaps and record provenance.
      if (!existing.sources.includes(d.source)) existing.sources.push(d.source);
      existing.round ??= d.round;
      existing.stadium ??= d.stadium;
      existing.time ??= d.time;
      existing.season ??= d.season;
      existing.homeGoals ??= d.homeGoals;
      existing.awayGoals ??= d.awayGoals;
      existing.stats ??= d.stats;
      return;
    }
    matches.set(key, {
      id: `m${++counter}`,
      competition: d.competition,
      season: d.season,
      round: d.round,
      date: d.date,
      time: d.time,
      homeTeam: d.home,
      awayTeam: d.away,
      homeGoals: d.homeGoals,
      awayGoals: d.awayGoals,
      stadium: d.stadium,
      stats: d.stats,
      sources: [d.source],
    });
  };

  // 1. Brasileirão Série A (2012-2022), canonical round info.
  const brasileirao = readCsv(dir, DATA_FILES.brasileirao);
  for (const r of brasileirao) {
    const dt = parseDateTime(r.datetime);
    addMatch({
      competition: Competition.BrasileiraoSerieA,
      season: parseSeason(r.season),
      round: r.round?.trim() || null,
      date: dt?.date ?? null,
      time: dt?.time ?? null,
      home: teams.register(r.home_team, r.home_team_state),
      away: teams.register(r.away_team, r.away_team_state),
      homeGoals: parseGoals(r.home_goal),
      awayGoals: parseGoals(r.away_goal),
      stadium: null,
      stats: null,
      source: DATA_FILES.brasileirao,
    });
  }
  loadReport[DATA_FILES.brasileirao] = brasileirao.length;

  // 2. Copa do Brasil (2012-2021).
  const cup = readCsv(dir, DATA_FILES.copaDoBrasil);
  for (const r of cup) {
    const dt = parseDateTime(r.datetime);
    addMatch({
      competition: Competition.CopaDoBrasil,
      season: parseSeason(r.season),
      round: r.round?.trim() || null,
      date: dt?.date ?? null,
      time: dt?.time ?? null,
      home: teams.register(r.home_team),
      away: teams.register(r.away_team),
      homeGoals: parseGoals(r.home_goal),
      awayGoals: parseGoals(r.away_goal),
      stadium: null,
      stats: null,
      source: DATA_FILES.copaDoBrasil,
    });
  }
  loadReport[DATA_FILES.copaDoBrasil] = cup.length;

  // 3. Copa Libertadores (2013-2022).
  const libertadores = readCsv(dir, DATA_FILES.libertadores);
  for (const r of libertadores) {
    const dt = parseDateTime(r.datetime);
    addMatch({
      competition: Competition.Libertadores,
      season: parseSeason(r.season),
      round: r.stage?.trim() || null,
      date: dt?.date ?? null,
      time: dt?.time ?? null,
      home: teams.register(r.home_team),
      away: teams.register(r.away_team),
      homeGoals: parseGoals(r.home_goal),
      awayGoals: parseGoals(r.away_goal),
      stadium: null,
      stats: null,
      source: DATA_FILES.libertadores,
    });
  }
  loadReport[DATA_FILES.libertadores] = libertadores.length;

  // 4. Historical Brasileirão (2003-2019), Portuguese columns, DD/MM/YYYY.
  const historical = readCsv(dir, DATA_FILES.historical);
  for (const r of historical) {
    const dt = parseDateTime(r.Data);
    addMatch({
      competition: Competition.BrasileiraoSerieA,
      season: parseSeason(r.Ano) ?? (dt ? Number(dt.date.slice(0, 4)) : null),
      round: r.Rodada?.trim() || null,
      date: dt?.date ?? null,
      time: dt?.time ?? null,
      home: teams.register(r.Equipe_mandante, r.Mandante_UF),
      away: teams.register(r.Equipe_visitante, r.Visitante_UF),
      homeGoals: parseGoals(r.Gols_mandante),
      awayGoals: parseGoals(r.Gols_visitante),
      stadium: r.Arena?.trim() || null,
      stats: null,
      source: DATA_FILES.historical,
    });
  }
  loadReport[DATA_FILES.historical] = historical.length;

  // 5. Extended dataset (2014-2023): Série A/B/C + Copa do Brasil w/ stats.
  const extended = readCsv(dir, DATA_FILES.extended);
  const tournamentMap: Record<string, Competition> = {
    "serie a": Competition.BrasileiraoSerieA,
    "serie b": Competition.SerieB,
    "serie c": Competition.SerieC,
    "copa do brasil": Competition.CopaDoBrasil,
  };
  for (const r of extended) {
    const competition = tournamentMap[normalizeText(r.tournament ?? "")];
    if (!competition) continue;
    const dt = parseDateTime(r.date);
    if (isExcluded(dt, r.home, r.away)) continue;
    const htHome = halfTime(r.ht_diff);
    const stats: MatchStats = {
      homeCorners: num(r.home_corner),
      awayCorners: num(r.away_corner),
      homeShots: num(r.home_shots),
      awayShots: num(r.away_shots),
      homeAttacks: num(r.home_attack),
      awayAttacks: num(r.away_attack),
      // ht_diff/at_diff are goal differences; recover absolute HT score when possible.
      halfTimeHomeGoals: null,
      halfTimeAwayGoals: null,
    };
    const hg = parseGoals(r.home_goal);
    const ag = parseGoals(r.away_goal);
    if (htHome !== null && hg !== null && ag !== null) {
      // ht_diff = HT home - HT away; we cannot recover absolutes reliably, skip.
    }
    addMatch({
      competition,
      season: dt ? Number(dt.date.slice(0, 4)) : null,
      round: null,
      date: dt?.date ?? null,
      time: r.time?.trim() ? r.time.trim().slice(0, 5) : (dt?.time ?? null),
      home: teams.register(r.home),
      away: teams.register(r.away),
      homeGoals: hg,
      awayGoals: ag,
      stadium: null,
      stats,
      source: DATA_FILES.extended,
    });
  }
  loadReport[DATA_FILES.extended] = extended.length;

  // 6. FIFA players.
  const fifa = readCsv(dir, DATA_FILES.fifa);
  const skillColumns = [
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
    "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
    "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
    "ShotPower", "Jumping", "Stamina", "Strength", "LongShots",
    "Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
    "Composure", "Marking", "StandingTackle", "SlidingTackle",
    "GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes",
  ];
  const players: Player[] = [];
  for (const r of fifa) {
    const club = r.Club?.trim() || null;
    let teamKey: string | null = null;
    if (club) {
      const res = teams.resolve(club);
      if (res.team) teamKey = res.team.key;
    }
    const skills: Record<string, number | null> = {};
    for (const c of skillColumns) skills[c] = num(r[c]);
    players.push({
      id: parseIntOrNull(r.ID) ?? players.length,
      name: r.Name ?? "",
      age: parseIntOrNull(r.Age),
      nationality: r.Nationality ?? "",
      overall: parseIntOrNull(r.Overall),
      potential: parseIntOrNull(r.Potential),
      club,
      position: r.Position?.trim() || null,
      jerseyNumber: parseIntOrNull(r["Jersey Number"]),
      height: r.Height?.trim() || null,
      weight: r.Weight?.trim() || null,
      preferredFoot: r["Preferred Foot"]?.trim() || null,
      skills,
      teamKey,
    });
  }
  loadReport[DATA_FILES.fifa] = players.length;

  const deduped = fuzzyMergeFixtures(matches);
  const matchList = [...deduped.values()];
  matchList.sort((a, b) => (a.date ?? "").localeCompare(b.date ?? ""));

  return { matches: matchList, players, teams, loadReport };
}
