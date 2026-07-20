/**
 * CSV loading layer: reads the six Kaggle datasets and produces a unified,
 * deduplicated list of matches plus the FIFA player list.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { parse } from "csv-parse/sync";
import type { CompetitionLabel, Match, Player, TeamRef } from "./types.js";
import {
  competitionFromTournament,
  isBrazilianTeamKey,
  loose,
  parseDate,
  teamRef,
} from "./normalize.js";

/* ------------------------------------------------------------------ */
/* Data directory resolution                                           */
/* ------------------------------------------------------------------ */

/**
 * Locate the `data/kaggle` directory. Search order:
 *  1. SOCCER_DATA_DIR env var
 *  2. <cwd>/data/kaggle
 *  3. walking up from this module's directory
 */
export function findDataDir(): string {
  if (process.env.SOCCER_DATA_DIR) {
    const p = process.env.SOCCER_DATA_DIR;
    if (fs.existsSync(p)) return p;
  }
  const fromCwd = path.resolve(process.cwd(), "data", "kaggle");
  if (fs.existsSync(fromCwd)) return fromCwd;
  let dir = path.dirname(fileURLToPath(import.meta.url));
  for (let i = 0; i < 6; i++) {
    const candidate = path.join(dir, "data", "kaggle");
    if (fs.existsSync(candidate)) return candidate;
    dir = path.dirname(dir);
  }
  throw new Error(
    "Could not locate data/kaggle directory. Set SOCCER_DATA_DIR.",
  );
}

/* ------------------------------------------------------------------ */
/* Small helpers                                                       */
/* ------------------------------------------------------------------ */

function readCsv(file: string): Record<string, string>[] {
  const content = fs.readFileSync(file);
  return parse(content, {
    columns: true,
    relax_quotes: true,
    skip_empty_lines: true,
    trim: true,
  }) as Record<string, string>[];
}

function parseGoals(v: string | undefined | null): number | null {
  if (v == null) return null;
  const s = String(v).trim();
  if (s === "" || s.toUpperCase() === "NA" || s === "-") return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

function parseIntOrNull(v: string | undefined | null): number | null {
  const n = parseGoals(v);
  return n == null ? null : Math.trunc(n);
}

function parseSeason(v: string | undefined | null): number | null {
  const n = parseIntOrNull(v);
  if (n == null || n < 1900 || n > 2100) return null;
  return n;
}

/* ------------------------------------------------------------------ */
/* Match assembly with cross-source deduplication                      */
/* ------------------------------------------------------------------ */

export interface Dataset {
  matches: Match[];
  players: Player[];
  /** Count of rows read per source file (before deduplication). */
  sourceRowCounts: Record<string, number>;
  /** Matches that were merged into an existing record (per source). */
  duplicateCounts: Record<string, number>;
}

interface MutableMatch extends Match {}

class MatchTable {
  private byId = new Map<string, MutableMatch>();

  /** Insert a match, merging with an existing record on (date, home, away). */
  upsert(m: MutableMatch): { merged: boolean } {
    const existing = this.byId.get(m.id);
    if (!existing) {
      this.byId.set(m.id, m);
      return { merged: false };
    }
    // Merge: keep the richer/more authoritative record.
    if (!existing.round && m.round) existing.round = m.round;
    if (!existing.stage && m.stage) existing.stage = m.stage;
    if (!existing.arena && m.arena) existing.arena = m.arena;
    if (existing.homeGoals == null && m.homeGoals != null) {
      existing.homeGoals = m.homeGoals;
      existing.awayGoals = m.awayGoals;
    }
    if (!existing.stats && m.stats) existing.stats = m.stats;
    if (!existing.season && m.season) existing.season = m.season;
    if (!existing.date && m.date) existing.date = m.date;
    for (const s of m.sources) {
      if (!existing.sources.includes(s)) existing.sources.push(s);
    }
    return { merged: true };
  }

  list(): Match[] {
    return [...this.byId.values()];
  }
}

function makeMatch(
  id: string,
  date: string,
  season: number | null,
  competition: CompetitionLabel,
  home: TeamRef,
  away: TeamRef,
  homeGoals: number | null,
  awayGoals: number | null,
  source: string,
  extra: Partial<Match> = {},
): MutableMatch {
  return {
    id,
    date,
    season,
    competition,
    round: extra.round ?? null,
    stage: extra.stage ?? null,
    homeTeam: home,
    awayTeam: away,
    homeGoals,
    awayGoals,
    arena: extra.arena ?? null,
    sources: [source],
    stats: extra.stats,
  };
}

/* ------------------------------------------------------------------ */
/* Date-drift reconciliation                                           */
/* ------------------------------------------------------------------ */

/**
 * The sources sometimes record the same fixture on adjacent dates
 * (e.g. a 22:00 kick-off logged as the next day in another dataset).
 * Exact-key dedup cannot catch those. This pass groups matches by
 * (competition, season, home, away) and merges records whose dates are
 * within 2 days of each other.
 */
function reconcileDateDrift(matches: Match[]): { matches: Match[]; merged: number } {
  const groups = new Map<string, Match[]>();
  for (const m of matches) {
    const gk = `${m.competition}|${m.season ?? "?"}|${m.homeTeam.key}|${m.awayTeam.key}`;
    const arr = groups.get(gk) ?? [];
    arr.push(m);
    groups.set(gk, arr);
  }
  const days = (iso: string): number => {
    const t = Date.parse(`${iso}T00:00:00Z`);
    return Number.isFinite(t) ? t / 86_400_000 : NaN;
  };
  const removed = new Set<Match>();
  let merged = 0;

  const mergeInto = (base: Match, other: Match) => {
    if (!base.round && other.round) base.round = other.round;
    if (!base.stage && other.stage) base.stage = other.stage;
    if (!base.arena && other.arena) base.arena = other.arena;
    if (base.homeGoals == null && other.homeGoals != null) {
      base.homeGoals = other.homeGoals;
      base.awayGoals = other.awayGoals;
    }
    if (!base.stats && other.stats) base.stats = other.stats;
    if (!base.season && other.season) base.season = other.season;
    for (const s of other.sources) if (!base.sources.includes(s)) base.sources.push(s);
  };

  for (const group of groups.values()) {
    if (group.length < 2) continue;
    group.sort((a, b) => a.date.localeCompare(b.date));
    // Rule 1: an unplayed placeholder (null goals) is always redundant when a
    // played record for the same fixture exists, regardless of date drift
    // (scheduled dates move when matches are postponed).
    const played = group.filter((m) => m.homeGoals != null);
    if (played.length > 0) {
      for (const placeholder of group) {
        if (placeholder.homeGoals != null) continue;
        mergeInto(played[0], placeholder);
        removed.add(placeholder);
        merged++;
      }
      if (played.length === 1) continue;
    }
    // Rule 2: merge remaining records whose dates drift by <= 2 days.
    const remaining = group.filter((m) => !removed.has(m));
    let anchor = remaining[0];
    for (let i = 1; i < remaining.length; i++) {
      const cur = remaining[i];
      const drift = Math.abs(days(cur.date) - days(anchor.date));
      if (Number.isFinite(drift) && drift <= 2 && cur !== anchor) {
        // Prefer the record that has goals as the surviving base.
        if (anchor.homeGoals == null && cur.homeGoals != null) {
          mergeInto(cur, anchor);
          removed.add(anchor);
          anchor = cur;
        } else {
          mergeInto(anchor, cur);
          removed.add(cur);
        }
        merged++;
      } else {
        anchor = cur;
      }
    }
  }
  return { matches: matches.filter((m) => !removed.has(m)), merged };
}

/* ------------------------------------------------------------------ */
/* League-season integrity filter                                      */
/* ------------------------------------------------------------------ */

/**
 * Drop league matches involving teams that play only a handful of games in
 * an otherwise complete season (>= 30 matches for the busiest team). These
 * are source-data anomalies, e.g. the friendly "Brasilia FC 1-1 CA
 * Taguatinga" (2016-01-30) that BR-Football-Dataset labels as "Serie A".
 * In a real league season every club plays ~2*(n-1) matches.
 */
function leagueSeasonIntegrity(matches: Match[]): { matches: Match[]; dropped: number } {
  const groups = new Map<string, Match[]>();
  for (const m of matches) {
    if (!m.competition.startsWith("Brasileirão") || m.season == null) continue;
    const gk = `${m.competition}|${m.season}`;
    const arr = groups.get(gk) ?? [];
    arr.push(m);
    groups.set(gk, arr);
  }
  const removed = new Set<Match>();
  for (const group of groups.values()) {
    const perTeam = new Map<string, number>();
    for (const m of group) {
      perTeam.set(m.homeTeam.key, (perTeam.get(m.homeTeam.key) ?? 0) + 1);
      perTeam.set(m.awayTeam.key, (perTeam.get(m.awayTeam.key) ?? 0) + 1);
    }
    const maxForTeam = Math.max(...perTeam.values());
    if (maxForTeam < 30) continue; // incomplete season in the data; keep as-is
    const fringeTeams = new Set(
      [...perTeam.entries()].filter(([, n]) => n < 10).map(([k]) => k),
    );
    if (fringeTeams.size === 0) continue;
    for (const m of group) {
      if (fringeTeams.has(m.homeTeam.key) || fringeTeams.has(m.awayTeam.key)) {
        removed.add(m);
      }
    }
  }
  return { matches: matches.filter((m) => !removed.has(m)), dropped: removed.size };
}

/* ------------------------------------------------------------------ */
/* Per-file loaders                                                    */
/* ------------------------------------------------------------------ */

function loadBrasileirao(table: MatchTable, counts: Dataset["duplicateCounts"]): number {
  const rows = readCsv(path.join(dataDir, "Brasileirao_Matches.csv"));
  for (const r of rows) {
    const date = parseDate(r.datetime) ?? "";
    const home = teamRef(r.home_team);
    const away = teamRef(r.away_team);
    const id = `${date}|${home.key}|${away.key}`;
    const { merged } = table.upsert(
      makeMatch(
        id, date, parseSeason(r.season), "Brasileirão Série A", home, away,
        parseGoals(r.home_goal), parseGoals(r.away_goal), "brasileirao",
        { round: r.round ?? null },
      ),
    );
    if (merged) counts.brasileirao++;
  }
  return rows.length;
}

function loadCup(table: MatchTable, counts: Dataset["duplicateCounts"]): number {
  const rows = readCsv(path.join(dataDir, "Brazilian_Cup_Matches.csv"));
  for (const r of rows) {
    const date = parseDate(r.datetime) ?? "";
    const home = teamRef(r.home_team);
    const away = teamRef(r.away_team);
    const id = `${date}|${home.key}|${away.key}`;
    const { merged } = table.upsert(
      makeMatch(
        id, date, parseSeason(r.season), "Copa do Brasil", home, away,
        parseGoals(r.home_goal), parseGoals(r.away_goal), "copa-do-brasil",
        { round: r.round ?? null },
      ),
    );
    if (merged) counts["copa-do-brasil"]++;
  }
  return rows.length;
}

function loadLibertadores(table: MatchTable, counts: Dataset["duplicateCounts"]): number {
  const rows = readCsv(path.join(dataDir, "Libertadores_Matches.csv"));
  for (const r of rows) {
    const date = parseDate(r.datetime) ?? "";
    const home = teamRef(r.home_team);
    const away = teamRef(r.away_team);
    const id = `${date}|${home.key}|${away.key}`;
    const { merged } = table.upsert(
      makeMatch(
        id, date, parseSeason(r.season), "Copa Libertadores", home, away,
        parseGoals(r.home_goal), parseGoals(r.away_goal), "libertadores",
        { stage: r.stage ?? null },
      ),
    );
    if (merged) counts.libertadores++;
  }
  return rows.length;
}

function loadHistorical(table: MatchTable, counts: Dataset["duplicateCounts"]): number {
  const rows = readCsv(path.join(dataDir, "novo_campeonato_brasileiro.csv"));
  for (const r of rows) {
    const date = parseDate(r.Data) ?? "";
    const home = teamRef(r.Equipe_mandante);
    const away = teamRef(r.Equipe_visitante);
    const id = `${date}|${home.key}|${away.key}`;
    const { merged } = table.upsert(
      makeMatch(
        id, date, parseSeason(r.Ano), "Brasileirão Série A", home, away,
        parseGoals(r.Gols_mandante), parseGoals(r.Gols_visitante), "historico",
        { round: r.Rodada ?? null, arena: r.Arena || null },
      ),
    );
    if (merged) counts.historico++;
  }
  return rows.length;
}

function loadExtendedStats(table: MatchTable, counts: Dataset["duplicateCounts"]): number {
  const rows = readCsv(path.join(dataDir, "BR-Football-Dataset.csv"));
  for (const r of rows) {
    const competition = competitionFromTournament(r.tournament ?? "");
    if (!competition) continue;
    const date = parseDate(r.date) ?? "";
    const home = teamRef(r.home);
    const away = teamRef(r.away);
    const id = `${date}|${home.key}|${away.key}`;
    // League seasons sometimes spill into Jan-Mar of the following year
    // (notably the COVID-delayed 2020 season, played Aug 2020-Feb 2021).
    // Assign those matches to the season that started the previous year.
    let season: number | null = date ? Number(date.slice(0, 4)) : null;
    const month = date ? Number(date.slice(5, 7)) : null;
    if (
      season != null &&
      month != null &&
      month <= 3 &&
      competition.startsWith("Brasileirão")
    ) {
      season -= 1;
    }
    const num = (v: string) => {
      const n = Number(v);
      return Number.isFinite(n) ? n : undefined;
    };
    const { merged } = table.upsert(
      makeMatch(
        id, date, season, competition, home, away,
        parseGoals(r.home_goal), parseGoals(r.away_goal), "estendido",
        {
          stats: {
            homeCorners: num(r.home_corner),
            awayCorners: num(r.away_corner),
            homeShots: num(r.home_shots),
            awayShots: num(r.away_shots),
            homeAttacks: num(r.home_attack),
            awayAttacks: num(r.away_attack),
            totalCorners: num(r.total_corners),
          },
        },
      ),
    );
    if (merged) counts.estendido++;
  }
  return rows.length;
}

/* ------------------------------------------------------------------ */
/* FIFA players                                                        */
/* ------------------------------------------------------------------ */

function loadPlayers(): Player[] {
  const rows = readCsv(path.join(dataDir, "fifa_data.csv"));
  const players: Player[] = [];
  for (const r of rows) {
    const id = Number(r.ID);
    if (!Number.isFinite(id)) continue;
    const club = r.Club?.trim() || null;
    let clubKey: string | null = null;
    if (club) {
      const ref = teamRef(club);
      clubKey = isBrazilianTeamKey(ref.key) ? ref.key : null;
    }
    players.push({
      id,
      name: r.Name ?? "",
      age: parseIntOrNull(r.Age),
      nationality: r.Nationality ?? "",
      overall: parseIntOrNull(r.Overall),
      potential: parseIntOrNull(r.Potential),
      club,
      clubKey,
      position: r.Position?.trim() || null,
      jerseyNumber: parseIntOrNull(r["Jersey Number"]),
      height: r.Height?.trim() || null,
      weight: r.Weight?.trim() || null,
    });
  }
  return players;
}

/* ------------------------------------------------------------------ */
/* Public entry point                                                  */
/* ------------------------------------------------------------------ */

let dataDir: string;

/** Load all six CSV files into a unified, deduplicated dataset. */
export function loadDataset(dir?: string): Dataset {
  dataDir = dir ?? findDataDir();
  const table = new MatchTable();
  const duplicateCounts: Dataset["duplicateCounts"] = {
    brasileirao: 0,
    "copa-do-brasil": 0,
    libertadores: 0,
    historico: 0,
    estendido: 0,
  };
  const sourceRowCounts: Record<string, number> = {};
  sourceRowCounts["Brasileirao_Matches.csv"] = loadBrasileirao(table, duplicateCounts);
  sourceRowCounts["Brazilian_Cup_Matches.csv"] = loadCup(table, duplicateCounts);
  sourceRowCounts["Libertadores_Matches.csv"] = loadLibertadores(table, duplicateCounts);
  sourceRowCounts["novo_campeonato_brasileiro.csv"] = loadHistorical(table, duplicateCounts);
  sourceRowCounts["BR-Football-Dataset.csv"] = loadExtendedStats(table, duplicateCounts);
  const players = loadPlayers();
  sourceRowCounts["fifa_data.csv"] = players.length;
  const reconciled = reconcileDateDrift(table.list());
  duplicateCounts.dateDrift = reconciled.merged;
  const integrity = leagueSeasonIntegrity(reconciled.matches);
  duplicateCounts.integrityDropped = integrity.dropped;
  const matches = integrity.matches;
  matches.sort((a, b) => a.date.localeCompare(b.date));
  return { matches, players, sourceRowCounts, duplicateCounts };
}

export { loose };
