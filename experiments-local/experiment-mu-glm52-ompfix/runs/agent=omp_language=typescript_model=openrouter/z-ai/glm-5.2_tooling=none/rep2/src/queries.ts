/**
 * Brazilian Soccer MCP Server — query engine
 * ------------------------------------------
 * Context block:
 *   Pure functions over the loaded Dataset that implement the five query
 *   categories required by the spec: match, team, player, competition and
 *   statistical analysis. Results are returned as plain JSON-serialisable
 *   objects so the MCP tool layer can serialise them verbatim.
 *
 *   Team matching uses the canonical team key (normalizer.canonicalTeamKey)
 *   so a query for "Flamengo" matches "Flamengo-RJ", "Flamengo - RJ" and
 *   "Flamengo" across files. A fuzzy fallback (substring on display name)
 *   is offered when an exact canonical lookup yields nothing, so the user can
 *   ask about teams whose exact alias is not curated.
 */

import type {
  HeadToHead,
  Match,
  StandingRow,
  TeamStats,
} from "./types.js";
import { canonicalTeamKey, teamKey } from "./normalizer.js";
import { formatDate } from "./dates.js";
import type { Dataset } from "./loader.js";

export interface MatchQuery {
  team?: string;
  opponent?: string;
  homeTeam?: string;
  awayTeam?: string;
  competition?: string;
  season?: number;
  startDate?: string;
  endDate?: string;
  stage?: string;
  round?: string;
  limit?: number;
}

export interface MatchResult {
  id: string;
  date: string;
  competition: string;
  homeTeam: string;
  awayTeam: string;
  homeGoal: number | null;
  awayGoal: number | null;
  season: number | null;
  round: string | null;
  stage: string | null;
  arena: string | null;
  source: string;
}

export interface TeamQuery {
  team: string;
  season?: number;
  competition?: string;
  homeAway?: "home" | "away" | "all";
}

export interface PlayerQuery {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  sortBy?: "overall" | "potential" | "age" | "name";
  limit?: number;
}

export interface CompetitionQuery {
  competition?: string;
  season?: number;
}

export interface StatsQuery {
  competition?: string;
  season?: number;
  team?: string;
}


/** Does a match's competition label match the requested competition? */
function competitionMatches(match: Match, requested?: string): boolean {
  if (!requested) return true;
  const want = requested.toLowerCase();
  return match.competition.toLowerCase().includes(want);
}

/** Convert a Match to the user-facing result shape. */
function toResult(m: Match): MatchResult {
  return {
    id: m.id,
    date: formatDate(m.date, m.rawDate),
    competition: m.competition,
    homeTeam: m.homeTeamDisplay,
    awayTeam: m.awayTeamDisplay,
    homeGoal: m.homeGoal,
    awayGoal: m.awayGoal,
    season: m.season,
    round: m.round,
    stage: m.stage ?? null,
    arena: m.arena ?? null,
    source: m.source,
  };
}

/** Parse an ISO date string into a UTC midnight Date, or null. */
function parseIsoDate(raw: string): Date | null {
  const d = new Date(raw);
  if (isNaN(d.getTime())) return null;
  return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
}

/** Query matches by criteria. */
export function queryMatches(ds: Dataset, q: MatchQuery): MatchResult[] {
  const teamKeyQ = q.team ? canonicalTeamKey(q.team) : undefined;
  const oppKeyQ = q.opponent ? canonicalTeamKey(q.opponent) : undefined;
  const homeKeyQ = q.homeTeam ? canonicalTeamKey(q.homeTeam) : undefined;
  const awayKeyQ = q.awayTeam ? canonicalTeamKey(q.awayTeam) : undefined;
  const start = q.startDate ? parseIsoDate(q.startDate) : null;
  const end = q.endDate ? parseIsoDate(q.endDate) : null;

  const out: MatchResult[] = [];
  for (const m of ds.matches) {
    if (teamKeyQ && m.homeTeam !== teamKeyQ && m.awayTeam !== teamKeyQ) continue;
    if (oppKeyQ) {
      const otherIsOpp = (m.homeTeam === teamKeyQ && m.awayTeam === oppKeyQ) ||
        (m.awayTeam === teamKeyQ && m.homeTeam === oppKeyQ);
      if (!otherIsOpp) continue;
    }
    if (homeKeyQ && m.homeTeam !== homeKeyQ) continue;
    if (awayKeyQ && m.awayTeam !== awayKeyQ) continue;
    if (!competitionMatches(m, q.competition)) continue;
    if (q.season !== undefined && m.season !== q.season) continue;
    if (q.round && m.round !== q.round) continue;
    if (q.stage && m.stage && !m.stage.toLowerCase().includes(q.stage.toLowerCase())) continue;
    if (start && m.date && m.date < start) continue;
    if (end && m.date && m.date > end) continue;
    out.push(toResult(m));
  }

  out.sort((a, b) => (b.date > a.date ? 1 : b.date < a.date ? -1 : 0));
  if (q.limit && q.limit > 0) return out.slice(0, q.limit);
  return out;
}

/** Compute aggregate statistics for a team, optionally filtered. */
export function teamStats(ds: Dataset, q: TeamQuery): TeamStats {
  const key = canonicalTeamKey(q.team);
  let wins = 0, draws = 0, losses = 0, goalsFor = 0, goalsAgainst = 0;
  let teamDisplay = q.team;
  let count = 0;

  for (const m of ds.matches) {
    const isHome = m.homeTeam === key;
    const isAway = m.awayTeam === key;
    if (!isHome && !isAway) continue;
    if (q.season !== undefined && m.season !== q.season) continue;
    if (!competitionMatches(m, q.competition)) continue;
    if (q.homeAway === "home" && !isHome) continue;
    if (q.homeAway === "away" && !isAway) continue;
    if (teamDisplay === q.team) teamDisplay = isHome ? m.homeTeamDisplay : m.awayTeamDisplay;

    const hg = m.homeGoal ?? 0;
    const ag = m.awayGoal ?? 0;
    if (isHome) {
      goalsFor += hg;
      goalsAgainst += ag;
      if (hg > ag) wins++;
      else if (hg < ag) losses++;
      else draws++;
    } else {
      goalsFor += ag;
      goalsAgainst += hg;
      if (ag > hg) wins++;
      else if (ag < hg) losses++;
      else draws++;
    }
    count++;
  }

  return {
    team: key,
    teamDisplay,
    matches: count,
    wins,
    draws,
    losses,
    goalsFor,
    goalsAgainst,
    points: wins * 3 + draws,
    homeAway: q.homeAway ?? "all",
  };
}

/** Head-to-head summary between two teams. */
export function headToHead(ds: Dataset, teamA: string, teamB: string, season?: number): HeadToHead {
  const keyA = canonicalTeamKey(teamA);
  const keyB = canonicalTeamKey(teamB);
  let aWins = 0, bWins = 0, draws = 0, aGoals = 0, bGoals = 0, matches = 0;

  for (const m of ds.matches) {
    if (season !== undefined && m.season !== season) continue;
    const aIsHome = m.homeTeam === keyA && m.awayTeam === keyB;
    const aIsAway = m.awayTeam === keyA && m.homeTeam === keyB;
    if (!aIsHome && !aIsAway) continue;
    const hg = m.homeGoal ?? 0;
    const ag = m.awayGoal ?? 0;
    if (aIsHome) {
      aGoals += hg;
      bGoals += ag;
      if (hg > ag) aWins++;
      else if (hg < ag) bWins++;
      else draws++;
    } else {
      aGoals += ag;
      bGoals += hg;
      if (ag > hg) aWins++;
      else if (hg > ag) bWins++;
      else draws++;
    }
    matches++;
  }

  return {
    teamA: keyA,
    teamB: keyB,
    matches,
    teamAWins: aWins,
    teamBWins: bWins,
    draws,
    teamAGoals: aGoals,
    teamBGoals: bGoals,
  };
}

/** Query FIFA players by criteria. */
export function queryPlayers(ds: Dataset, q: PlayerQuery) {
  const nameQ = q.name?.toLowerCase();
  const natQ = q.nationality?.toLowerCase();
  const clubQ = q.club?.toLowerCase();
  const posQ = q.position?.toLowerCase();

  let rows = ds.players.filter((p) => {
    if (nameQ && !p.name.toLowerCase().includes(nameQ)) return false;
    if (natQ && !p.nationality.toLowerCase().includes(natQ)) return false;
    if (clubQ && !p.club.toLowerCase().includes(clubQ)) return false;
    if (posQ && !p.position.toLowerCase().includes(posQ)) return false;
    if (q.minOverall !== undefined && (p.overall ?? 0) < q.minOverall) return false;
    return true;
  });

  const sortBy = q.sortBy ?? "overall";
  rows = rows.slice().sort((a, b) => {
    switch (sortBy) {
      case "overall":
        return (b.overall ?? 0) - (a.overall ?? 0);
      case "potential":
        return (b.potential ?? 0) - (a.potential ?? 0);
      case "age":
        return (a.age ?? 0) - (b.age ?? 0);
      case "name":
        return a.name.localeCompare(b.name);
      default:
        return 0;
    }
  });

  if (q.limit && q.limit > 0) rows = rows.slice(0, q.limit);
  return rows;
}

/** Standings for a competition+season, computed from match results (3-1-0). */
export function standings(ds: Dataset, q: CompetitionQuery): StandingRow[] {
  const table = new Map<string, {
    team: string; display: string; played: number; w: number; d: number; l: number;
    gf: number; ga: number;
  }>();

  for (const m of ds.matches) {
    if (!competitionMatches(m, q.competition)) continue;
    if (q.season !== undefined && m.season !== q.season) continue;
    if (m.homeGoal === null || m.awayGoal === null) continue;

    ensureRow(table, m.homeTeam, m.homeTeamDisplay);
    ensureRow(table, m.awayTeam, m.awayTeamDisplay);
    const home = table.get(m.homeTeam)!;
    const away = table.get(m.awayTeam)!;
    home.played++; away.played++;
    home.gf += m.homeGoal; home.ga += m.awayGoal;
    away.gf += m.awayGoal; away.ga += m.homeGoal;
    if (m.homeGoal > m.awayGoal) { home.w++; away.l++; }
    else if (m.homeGoal < m.awayGoal) { away.w++; home.l++; }
    else { home.d++; away.d++; }
  }

  return Array.from(table.values())
    .map((r) => ({
      position: 0,
      team: r.team,
      teamDisplay: r.display,
      played: r.played,
      wins: r.w,
      draws: r.d,
      losses: r.l,
      goalsFor: r.gf,
      goalsAgainst: r.ga,
      goalDifference: r.gf - r.ga,
      points: r.w * 3 + r.d,
    }))
    .sort((a, b) => b.points - a.points || b.goalDifference - a.goalDifference || b.goalsFor - a.goalsFor)
    .map((r, i) => ({ ...r, position: i + 1 }));
}

function ensureRow(
  table: Map<string, { team: string; display: string; played: number; w: number; d: number; l: number; gf: number; ga: number }>,
  key: string,
  display: string,
): void {
  if (!table.has(key)) {
    table.set(key, { team: key, display, played: 0, w: 0, d: 0, l: 0, gf: 0, ga: 0 });
  } else {
    const existing = table.get(key)!;
    if (!existing.display) existing.display = display;
  }
}

/** Average goals per match, home win rate, away win rate, draw rate. */
export function goalStats(ds: Dataset, q: StatsQuery) {
  let totalGoals = 0, totalMatches = 0;
  let homeWins = 0, awayWins = 0, draws = 0;
  let biggestWins: { date: string; home: string; away: string; homeGoal: number; awayGoal: number; competition: string; margin: number }[] = [];
  const teamKeyQ = q.team ? canonicalTeamKey(q.team) : undefined;

  for (const m of ds.matches) {
    if (!competitionMatches(m, q.competition)) continue;
    if (q.season !== undefined && m.season !== q.season) continue;
    if (m.homeGoal === null || m.awayGoal === null) continue;
    if (teamKeyQ && m.homeTeam !== teamKeyQ && m.awayTeam !== teamKeyQ) continue;

    totalGoals += m.homeGoal + m.awayGoal;
    totalMatches++;
    if (m.homeGoal > m.awayGoal) homeWins++;
    else if (m.awayGoal > m.homeGoal) awayWins++;
    else draws++;

    const margin = Math.abs(m.homeGoal - m.awayGoal);
    if (margin >= 4) {
      biggestWins.push({
        date: formatDate(m.date, m.rawDate),
        home: m.homeTeamDisplay,
        away: m.awayTeamDisplay,
        homeGoal: m.homeGoal,
        awayGoal: m.awayGoal,
        competition: m.competition,
        margin,
      });
    }
  }

  biggestWins.sort((a, b) => b.margin - a.margin || b.homeGoal + b.awayGoal - (a.homeGoal + a.awayGoal));
  return {
    totalMatches,
    totalGoals,
    averageGoalsPerMatch: totalMatches ? +(totalGoals / totalMatches).toFixed(2) : 0,
    homeWinRate: totalMatches ? +((homeWins / totalMatches) * 100).toFixed(1) : 0,
    awayWinRate: totalMatches ? +((awayWins / totalMatches) * 100).toFixed(1) : 0,
    drawRate: totalMatches ? +((draws / totalMatches) * 100).toFixed(1) : 0,
    biggestWins: biggestWins.slice(0, 10),
  };
}

/** Best home or away record across a competition/season. */
export function bestRecord(ds: Dataset, q: { competition?: string; season?: number; homeAway: "home" | "away" }): TeamStats[] {
  const teams = distinctTeams(ds, q);
  const stats: TeamStats[] = teams.map((t) => teamStats(ds, {
    team: t.display,
    competition: q.competition,
    season: q.season,
    homeAway: q.homeAway,
  }));
  return stats
    .filter((s) => s.matches > 0)
    .sort((a, b) => b.points - a.points || (b.wins - b.losses) - (a.wins - a.losses) || b.goalsFor - a.goalsFor)
    .slice(0, 5);
}

function distinctTeams(ds: Dataset, q: { competition?: string; season?: number }): { key: string; display: string }[] {
  const map = new Map<string, string>();
  for (const m of ds.matches) {
    if (!competitionMatches(m, q.competition)) continue;
    if (q.season !== undefined && m.season !== q.season) continue;
    if (!map.has(m.homeTeam)) map.set(m.homeTeam, m.homeTeamDisplay);
    if (!map.has(m.awayTeam)) map.set(m.awayTeam, m.awayTeamDisplay);
  }
  return Array.from(map.entries()).map(([key, display]) => ({ key, display }));
}

/** Top scorers are not directly present; we approximate by goals per team-game. */
export function topScoringTeams(ds: Dataset, q: { competition?: string; season?: number; limit?: number }) {
  const stats: { team: string; display: string; goalsFor: number; matches: number; avg: number }[] = [];
  const teams = distinctTeams(ds, q);
  for (const t of teams) {
    const s = teamStats(ds, { team: t.display, competition: q.competition, season: q.season });
    if (s.matches === 0) continue;
    stats.push({
      team: s.team,
      display: s.teamDisplay,
      goalsFor: s.goalsFor,
      matches: s.matches,
      avg: +(s.goalsFor / s.matches).toFixed(2),
    });
  }
  stats.sort((a, b) => b.goalsFor - a.goalsFor || b.avg - a.avg);
  return stats.slice(0, q.limit ?? 10);
}
/** Resolve a free-text team name to canonical info (used by MCP tools). */
export function resolveTeam(ds: Dataset, name: string) {
  const key = canonicalTeamKey(name);
  let display = name;
  for (const m of ds.matches) {
    if (m.homeTeam === key) { display = m.homeTeamDisplay; break; }
    if (m.awayTeam === key) { display = m.awayTeamDisplay; break; }
  }
  // Fuzzy fallback: substring on the deaccented display name when no exact
  // canonical-key match exists. Returns whichever side actually matched.
  if (!ds.matches.some((m) => m.homeTeam === key || m.awayTeam === key)) {
    const needle = teamKey(name);
    if (needle) {
      for (const m of ds.matches) {
        const homeHit = teamKey(m.homeTeamDisplay).includes(needle);
        const awayHit = teamKey(m.awayTeamDisplay).includes(needle);
        if (homeHit || awayHit) {
          return {
            query: name,
            canonicalKey: homeHit ? m.homeTeam : m.awayTeam,
            matchedDisplay: homeHit ? m.homeTeamDisplay : m.awayTeamDisplay,
            fuzzy: true,
          };
        }
      }
    }
  }
  return { query: name, canonicalKey: key, matchedDisplay: display, fuzzy: false };
}
