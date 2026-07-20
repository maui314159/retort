/**
 * Match-query service: find matches by team(s), competition, season and
 * date range; compute head-to-head records.
 */
import type { Dataset, Match } from "../types.js";
import { teamMatches } from "../normalize.js";

export interface MatchFilter {
  /** Team name — matches home or away. */
  team?: string;
  /** Second team — when set, only matches between `team` and `opponent`. */
  opponent?: string;
  /** Fuzzy competition name: "brasileirao", "copa do brasil", "libertadores", "serie a"... */
  competition?: string;
  /** Season year, e.g. 2023. */
  season?: number;
  /** Inclusive ISO date bounds (YYYY-MM-DD). */
  fromDate?: string;
  toDate?: string;
  /** Round/stage substring, e.g. "final", "group". */
  stage?: string;
  /** Max results (default 50). */
  limit?: number;
}

/** Loose competition matcher: "brasileirao" ~ "Brasileirão Série A". */
export function competitionMatches(actual: string, query: string): boolean {
  const fold = (s: string) =>
    s
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/\s+/g, " ")
      .trim();
  const a = fold(actual);
  const q = fold(query);
  if (!q) return true;
  // Precise handling for the league family: a bare "brasileirao" means
  // Série A (not B/C); "serie b"/"serie c" pick their own division.
  if (/^(brasileirao|campeonato brasileiro|brasileirao serie a|serie ?a)$/.test(q)) {
    return a === "brasileirao serie a";
  }
  if (/^(brasileirao )?serie ?b$/.test(q)) return a === "brasileirao serie b";
  if (/^(brasileirao )?serie ?c$/.test(q)) return a === "brasileirao serie c";
  if (/^(copa do brasil|brazilian cup)$/.test(q)) return a === "copa do brasil";
  if (/^(copa )?libertadores$/.test(q)) return a === "copa libertadores";
  // Generic fallback for anything else.
  return a.includes(q) || q.includes(a);
}

/** Core match filtering. Results are chronological (dataset is pre-sorted). */
export function findMatches(ds: Dataset, f: MatchFilter): Match[] {
  const limit = f.limit ?? 50;
  const out: Match[] = [];
  for (const m of ds.matches) {
    if (f.team && !teamMatches(m.homeTeamRaw, f.team) && !teamMatches(m.awayTeamRaw, f.team))
      continue;
    if (
      f.opponent &&
      !teamMatches(m.homeTeamRaw, f.opponent) &&
      !teamMatches(m.awayTeamRaw, f.opponent)
    )
      continue;
    if (f.competition && !competitionMatches(m.competition, f.competition)) continue;
    if (f.season !== undefined && m.season !== f.season) continue;
    if (f.fromDate && (!m.date || m.date < f.fromDate)) continue;
    if (f.toDate && (!m.date || m.date > f.toDate)) continue;
    if (f.stage) {
      const q = f.stage.toLowerCase();
      const stage = (m.stage ?? "").toLowerCase();
      const round = (m.round ?? "").toLowerCase();
      if (q === "final") {
        // "final" must not substring-match "semi-final"/"semifinals".
        if (stage !== "final" && round !== "final") continue;
      } else {
        const hay = `${round} ${stage}`;
        if (!hay.includes(q)) continue;
      }
    }
    out.push(m);
    if (out.length >= limit) break;
  }
  return out;
}

export interface HeadToHead {
  teamA: string;
  teamB: string;
  matches: number;
  winsA: number;
  winsB: number;
  draws: number;
  goalsA: number;
  goalsB: number;
  /** Most recent meetings first. */
  recent: Match[];
}

/** Full head-to-head record between two teams across all files. */
export function headToHead(ds: Dataset, teamA: string, teamB: string): HeadToHead {
  const games = findMatches(ds, { team: teamA, opponent: teamB, limit: 10000 });
  let winsA = 0,
    winsB = 0,
    draws = 0,
    goalsA = 0,
    goalsB = 0;
  for (const m of games) {
    const aIsHome = teamMatches(m.homeTeamRaw, teamA);
    const aGoals = aIsHome ? m.homeGoals : m.awayGoals;
    const bGoals = aIsHome ? m.awayGoals : m.homeGoals;
    goalsA += aGoals;
    goalsB += bGoals;
    if (aGoals > bGoals) winsA++;
    else if (aGoals < bGoals) winsB++;
    else draws++;
  }
  const recent = [...games].reverse().slice(0, 10);
  return {
    teamA,
    teamB,
    matches: games.length,
    winsA,
    winsB,
    draws,
    goalsA,
    goalsB,
    recent,
  };
}

/** Most recent meeting between two teams (any competition). */
export function lastMeeting(ds: Dataset, teamA: string, teamB: string): Match | null {
  const games = findMatches(ds, { team: teamA, opponent: teamB, limit: 10000 });
  return games.length ? games[games.length - 1] : null;
}
