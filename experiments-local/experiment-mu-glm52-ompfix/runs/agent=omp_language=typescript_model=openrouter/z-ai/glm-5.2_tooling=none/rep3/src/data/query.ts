/**
 * Brazilian Soccer MCP Server — Query Engine
 * -----------------------------------------------------------------------------
 * Context block:
 *   This module implements the pure, synchronous query/analysis layer that the
 *   MCP tools (in `tools.ts`) thinly wrap. It operates solely on the normalized
 *   `Dataset` model and exposes no I/O. Keeping it decoupled from MCP makes it
 *   directly unit-testable (the BDD scenarios in `test/` exercise these
 *   functions).
 *
 *   Conventions:
 *     • All "by team" matching uses tolerant normalization (`teamMatches`)
 *       so "Flamengo" matches "Flamengo-RJ" and vice versa.
 *     • Venue scoping for team stats: "home" (team is home), "away" (team is
 *       away), "either" (both, but counted from the team's perspective).
 *     • Standings/points use the standard 3-1-0 scoring; only scored matches
 *       (both goals non-null) contribute.
 *     • Competition scope accepts a list of CompetitionKeys OR a list of
 *       SourceKeys, so callers can ask "modern Brasileirão only" vs "all
 *       Serie A incl. extended".
 *     • Matches are returned newest-first by default for display.
 */

import type {
  ClubBrazilianPlayers,
  CompetitionKey,
  Dataset,
  HeadToHead,
  Match,
  MatchStatistics,
  Player,
  SourceKey,
  StandingRow,
  TeamStat,
  Venue,
} from "./types.js";
import { inDateRange } from "./dates.js";
import { normalizeTeamName, teamMatches, teamKey } from "./teams.js";

export interface MatchFilter {
  team?: string;
  opponent?: string;
  venue?: Venue;
  competition?: CompetitionKey | CompetitionKey[];
  source?: SourceKey | SourceKey[];
  season?: number;
  from?: string | null;
  to?: string | null;
  stage?: string;
  round?: string;
  limit?: number;
}

function asArray<T>(v: T | T[] | undefined): T[] | undefined {
  if (v === undefined) return undefined;
  return Array.isArray(v) ? v : [v];
}

/** Determine the result for `team` in a scored match: "W" | "D" | "L" | null. */
function resultFor(match: Match, team: string): "W" | "D" | "L" | null {
  if (match.homeGoals == null || match.awayGoals == null) return null;
  const isHome = teamMatches(team, match.homeTeam);
  const isAway = teamMatches(team, match.awayTeam);
  if (!isHome && !isAway) return null;
  const hg = match.homeGoals;
  const ag = match.awayGoals;
  if (hg === ag) return "D";
  const teamWon = isHome ? hg > ag : ag > hg;
  return teamWon ? "W" : "L";
}

function teamInMatch(match: Match, team: string): boolean {
  return teamMatches(team, match.homeTeam) || teamMatches(team, match.awayTeam);
}

/** Apply a MatchFilter to the full match list, returning sorted matches. */
export function findMatches(ds: Dataset, f: MatchFilter = {}): Match[] {
  const comps = asArray(f.competition);
  const srcs = asArray(f.source);
  let out = ds.matches.filter((m) => {
    if (comps && !comps.includes(m.competition)) return false;
    if (srcs && !srcs.includes(m.source)) return false;
    if (f.season != null && m.season !== f.season) return false;
    if (f.from || f.to) {
      if (!inDateRange(m.date, f.from ?? null, f.to ?? null)) return false;
    }
    if (f.stage && m.stage !== f.stage) return false;
    if (f.round && m.round !== f.round) return false;
    if (f.team) {
      if (f.venue === "home") {
        if (!teamMatches(f.team, m.homeTeam)) return false;
      } else if (f.venue === "away") {
        if (!teamMatches(f.team, m.awayTeam)) return false;
      } else {
        if (!teamInMatch(m, f.team)) return false;
      }
      if (f.opponent) {
        const oppHome = teamMatches(f.opponent, m.homeTeam);
        const oppAway = teamMatches(f.opponent, m.awayTeam);
        if (!oppHome && !oppAway) return false;
      }
    } else if (f.opponent) {
      if (!teamInMatch(m, f.opponent)) return false;
    }
    return true;
  });

  // Sort newest first by datetime (date falls back), then by id for stability.
  out = out.sort((a, b) => {
    const da = a.datetime ?? a.date ?? "";
    const db = b.datetime ?? b.date ?? "";
    if (da !== db) return da < db ? 1 : -1;
    return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
  });

  if (f.limit != null && f.limit >= 0) out = out.slice(0, f.limit);
  return out;
}

/** Find head-to-head matches between two teams (either venue, either order).
 *  Uses tolerant matching so "Flamengo" matches the stored "Flamengo-RJ". */
export function headToHead(ds: Dataset, team1: string, team2: string, f: MatchFilter = {}): HeadToHead {
  const matches = findMatches(ds, f).filter(
    (m) =>
      (teamMatches(team1, m.homeTeam) && teamMatches(team2, m.awayTeam)) ||
      (teamMatches(team1, m.awayTeam) && teamMatches(team2, m.homeTeam)),
  );
  let t1w = 0, t2w = 0, draws = 0, t1g = 0, t2g = 0;
  for (const m of matches) {
    if (m.homeGoals == null || m.awayGoals == null) continue;
    const t1Home = teamMatches(team1, m.homeTeam);
    const g1 = t1Home ? m.homeGoals : m.awayGoals;
    const g2 = t1Home ? m.awayGoals : m.homeGoals;
    t1g += g1;
    t2g += g2;
    if (g1 > g2) t1w++;
    else if (g1 < g2) t2w++;
    else draws++;
  }
  return {
    team1: normalizeTeamName(team1),
    team2: normalizeTeamName(team2),
    team1Wins: t1w,
    team2Wins: t2w,
    draws,
    played: t1w + t2w + draws,
    team1Goals: t1g,
    team2Goals: t2g,
    matches,
  };
}

/** Compute a TeamStat for a team over a filtered match set. */
export function teamStats(ds: Dataset, team: string, f: MatchFilter = {}): TeamStat {
  const matches = findMatches(ds, { ...f, team });
  let played = 0, wins = 0, draws = 0, losses = 0, gf = 0, ga = 0;
  for (const m of matches) {
    if (m.homeGoals == null || m.awayGoals == null) continue;
    const r = resultFor(m, team);
    if (r == null) continue;
    played++;
    const isHome = teamMatches(team, m.homeTeam);
    const teamGoals = isHome ? m.homeGoals : m.awayGoals;
    const oppGoals = isHome ? m.awayGoals : m.homeGoals;
    gf += teamGoals;
    ga += oppGoals;
    if (r === "W") wins++;
    else if (r === "D") draws++;
    else losses++;
  }
  return {
    team: normalizeTeamName(team),
    played,
    wins,
    draws,
    losses,
    goalsFor: gf,
    goalsAgainst: ga,
    goalDifference: gf - ga,
    points: wins * 3 + draws,
    winRate: played ? wins / played : 0,
  };
}

/** Compute a standings table for a (competition/source/season) scope. */
export function standings(ds: Dataset, f: MatchFilter = {}): StandingRow[] {
  const matches = findMatches(ds, f);
  const table = new Map<string, TeamStat>();
  const acc = (name: string): TeamStat => {
    const k = teamKey(name);
    if (!table.has(k)) {
      table.set(k, {
        team: normalizeTeamName(name),
        played: 0, wins: 0, draws: 0, losses: 0,
        goalsFor: 0, goalsAgainst: 0, goalDifference: 0,
        points: 0, winRate: 0,
      });
    }
    return table.get(k)!;
  };

  for (const m of matches) {
    if (m.homeGoals == null || m.awayGoals == null) continue;
    const h = acc(m.homeTeam);
    const a = acc(m.awayTeam);
    h.played++; a.played++;
    h.goalsFor += m.homeGoals; h.goalsAgainst += m.awayGoals;
    a.goalsFor += m.awayGoals; a.goalsAgainst += m.homeGoals;
    if (m.homeGoals > m.awayGoals) { h.wins++; a.losses++; }
    else if (m.homeGoals < m.awayGoals) { a.wins++; h.losses++; }
    else { h.draws++; a.draws++; }
  }

  const rows = [...table.values()];
  for (const r of rows) {
    r.points = r.wins * 3 + r.draws;
    r.goalDifference = r.goalsFor - r.goalsAgainst;
    r.winRate = r.played ? r.wins / r.played : 0;
  }
  rows.sort((a, b) =>
    b.points - a.points ||
    b.wins - a.wins ||
    b.goalDifference - a.goalDifference ||
    b.goalsFor - a.goalsFor ||
    a.team.localeCompare(b.team),
  );
  return rows.map((r, i) => ({ ...r, position: i + 1 }));
}

/** Aggregate statistics over a filtered match set. */
export function matchStatistics(ds: Dataset, f: MatchFilter = {}): MatchStatistics {
  const matches = findMatches(ds, f);
  let scored = 0, total = 0, hw = 0, aw = 0, dr = 0, hg = 0, ag = 0;
  let biggestHome: Match | null = null;
  let biggestAway: Match | null = null;
  let homeMargin = -1, awayMargin = -1;
  for (const m of matches) {
    if (m.homeGoals == null || m.awayGoals == null) continue;
    scored++;
    total += m.homeGoals + m.awayGoals;
    hg += m.homeGoals;
    ag += m.awayGoals;
    if (m.homeGoals > m.awayGoals) hw++;
    else if (m.homeGoals < m.awayGoals) aw++;
    else dr++;
    const hm = m.homeGoals - m.awayGoals;
    const am = m.awayGoals - m.homeGoals;
    if (hm > homeMargin) { homeMargin = hm; biggestHome = m; }
    if (am > awayMargin) { awayMargin = am; biggestAway = m; }
  }
  return {
    matches: matches.length,
    scoredMatches: scored,
    totalGoals: total,
    averageGoals: scored ? total / scored : 0,
    homeWins: hw,
    awayWins: aw,
    draws: dr,
    homeWinRate: scored ? hw / scored : 0,
    awayWinRate: scored ? aw / scored : 0,
    drawRate: scored ? dr / scored : 0,
    averageHomeGoals: scored ? hg / scored : 0,
    averageAwayGoals: scored ? ag / scored : 0,
    biggestHomeWin: biggestHome,
    biggestAwayWin: biggestAway,
  };
}

/** Biggest victories (home or away) in a filtered match set, sorted by margin. */
export function biggestWins(ds: Dataset, f: MatchFilter = {}, limit = 10): Match[] {
  const matches = findMatches(ds, f).filter(
    (m) => m.homeGoals != null && m.awayGoals != null,
  );
  return matches
    .map((m) => ({ m, margin: Math.abs((m.homeGoals ?? 0) - (m.awayGoals ?? 0)) }))
    .sort((a, b) => b.margin - a.margin || (a.m.date ?? "").localeCompare(b.m.date ?? ""))
    .slice(0, limit)
    .map((x) => x.m);
}

/** Find players by name substring, nationality, or club. */
export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  limit?: number;
}

export function findPlayers(ds: Dataset, f: PlayerFilter = {}): Player[] {
  let out = ds.players.filter((p) => {
    if (f.name) {
      const q = f.name.toLowerCase();
      if (!p.name.toLowerCase().includes(q)) return false;
    }
    if (f.nationality) {
      const q = f.nationality.toLowerCase();
      if (!p.nationality.toLowerCase().includes(q)) return false;
    }
    if (f.club) {
      const q = f.club.toLowerCase();
      if (!p.club.toLowerCase().includes(q)) return false;
    }
    if (f.position) {
      const q = f.position.toLowerCase();
      if (!p.position.toLowerCase().includes(q)) return false;
    }
    if (f.minOverall != null && (p.overall ?? 0) < f.minOverall) return false;
    return true;
  });
  out = out.sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
  if (f.limit != null) out = out.slice(0, f.limit);
  return out;
}

/** FIFA dataset uses full official club names. Match exactly (not substring)
 *  so Portuguese clubs like "Sporting CP" and "Vitória Guimarães" are not
 *  mistaken for the Brazilian "Sport Club do Recife" / "Vitória". Maps the
 *  exact FIFA club string to a canonical short display name. */
const BRAZILIAN_CLUBS: Record<string, string> = {
  "Grêmio": "Grêmio",
  "Atlético Mineiro": "Atlético-MG",
  "Cruzeiro": "Cruzeiro",
  "Fluminense": "Fluminense",
  "Santos": "Santos",
  "Internacional": "Internacional",
  "América FC (Minas Gerais)": "América-MG",
  "Botafogo": "Botafogo",
  "Bahia": "Bahia",
  "Paraná": "Paraná",
  "Atlético Paranaense": "Athletico-PR",
  "Vitória": "Vitória",
  "Sport Club do Recife": "Sport",
  "Chapecoense": "Chapecoense",
  "Ceará Sporting Club": "Ceará",
};

export function brazilianPlayersAtBrazilianClubs(ds: Dataset): ClubBrazilianPlayers[] {
  const groups = new Map<string, Player[]>();
  for (const p of ds.players) {
    if (p.nationality.toLowerCase() !== "brazil") continue;
    const name = BRAZILIAN_CLUBS[p.club];
    if (!name) continue;
    if (!groups.has(name)) groups.set(name, []);
    groups.get(name)!.push(p);
  }
  const out: ClubBrazilianPlayers[] = [];
  for (const [, players] of groups) {
    const ratings = players.map((p) => p.overall ?? 0).filter((r) => r > 0);
    const top = players.slice().sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0))[0];
    out.push({
      club: players[0].club,
      count: players.length,
      averageOverall: ratings.length ? ratings.reduce((s, r) => s + r, 0) / ratings.length : 0,
      topPlayer: top?.name ?? null,
    });
  }
  return out.sort((a, b) => b.count - a.count || b.averageOverall - a.averageOverall);
}

/** The most recent match involving `team` (either venue), or null. */
export function lastMatch(ds: Dataset, team: string, f: MatchFilter = {}): Match | null {
  const matches = findMatches(ds, { ...f, team, limit: 1 });
  return matches[0] ?? null;
}
