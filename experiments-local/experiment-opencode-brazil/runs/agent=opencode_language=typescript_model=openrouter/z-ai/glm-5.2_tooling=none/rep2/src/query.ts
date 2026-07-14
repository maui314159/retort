/**
 * Query engine for the Brazilian Soccer MCP server.
 *
 * Exposes pure, dataset-backed functions covering the five required capability
 * categories from the spec: match queries, team queries, player queries,
 * competition queries, and statistical analysis. Each function returns plain
 * JSON-serializable data that the MCP tool layer wraps into responses.
 */

import type {
  Dataset,
  Match,
  MatchFilter,
  Competition,
  TeamRecord,
  HeadToHead,
  Player,
} from './types.js';
import { normalizeTeamName, parseDate, teamMatches, teamsEqual } from './normalize.js';

/** Apply a {@link MatchFilter} to the full match list. */
export function filterMatches(matches: Match[], filter: MatchFilter): Match[] {
  let out = matches;

  if (filter.competition) {
    const comps = Array.isArray(filter.competition)
      ? filter.competition
      : [filter.competition];
    const set = new Set<Competition>(comps);
    out = out.filter((m) => set.has(m.competition));
  }
  if (filter.season != null) {
    out = out.filter((m) => m.season === filter.season);
  }
  if (filter.fromDate) {
    const f = filter.fromDate;
    out = out.filter((m) => m.date != null && m.date >= f);
  }
  if (filter.toDate) {
    const t = filter.toDate;
    out = out.filter((m) => m.date != null && m.date <= t);
  }
  if (filter.homeTeam) {
    const q = normalizeTeamName(filter.homeTeam);
    out = out.filter((m) => teamMatches(m.homeTeam, q));
  }
  if (filter.awayTeam) {
    const q = normalizeTeamName(filter.awayTeam);
    out = out.filter((m) => teamMatches(m.awayTeam, q));
  }
  if (filter.team) {
    const q = normalizeTeamName(filter.team);
    out = out.filter((m) => teamMatches(m.homeTeam, q) || teamMatches(m.awayTeam, q));
  }
  if (filter.opponent) {
    const q = normalizeTeamName(filter.opponent);
    out = out.filter((m) => teamMatches(m.homeTeam, q) || teamMatches(m.awayTeam, q));
  }

  // Sort by date ascending (nulls last).
  out = [...out].sort((a, b) => {
    if (a.date == null && b.date == null) return 0;
    if (a.date == null) return 1;
    if (b.date == null) return -1;
    return a.date < b.date ? -1 : a.date > b.date ? 1 : 0;
  });

  if (filter.limit != null && filter.limit >= 0) {
    out = out.slice(0, filter.limit);
  }
  return out;
}

/** Find matches between two specific teams (any venue). */
export function headToHeadMatches(
  matches: Match[],
  teamA: string,
  teamB: string,
): Match[] {
  const a = normalizeTeamName(teamA);
  const b = normalizeTeamName(teamB);
  return matches
    .filter(
      (m) =>
        (teamMatches(m.homeTeam, a) && teamMatches(m.awayTeam, b)) ||
        (teamMatches(m.homeTeam, b) && teamMatches(m.awayTeam, a)),
    )
    .sort((x, y) => {
      const xd = x.date ?? '';
      const yd = y.date ?? '';
      return xd < yd ? -1 : xd > yd ? 1 : 0;
    });
}

/** Compute a head-to-head summary between two teams. */
export function headToHead(
  matches: Match[],
  teamA: string,
  teamB: string,
): HeadToHead {
  const a = normalizeTeamName(teamA);
  const b = normalizeTeamName(teamB);
  const h2h = headToHeadMatches(matches, teamA, teamB);
  let aWins = 0;
  let bWins = 0;
  let draws = 0;
  for (const m of h2h) {
    if (m.homeGoal == null || m.awayGoal == null) continue;
    const homeIsA = teamMatches(m.homeTeam, a);
    const homeIsB = teamMatches(m.homeTeam, b);
    if (m.homeGoal > m.awayGoal) {
      if (homeIsA) aWins++;
      else if (homeIsB) bWins++;
    } else if (m.homeGoal < m.awayGoal) {
      if (homeIsA) bWins++;
      else if (homeIsB) aWins++;
    } else {
      draws++;
    }
  }
  return {
    teamA: a,
    teamB: b,
    matches: h2h,
    teamAWins: aWins,
    teamBWins: bWins,
    draws,
  };
}

/** Compute a team's record over a set of matches (already filtered). */
export function teamRecord(matches: Match[], team: string): TeamRecord {
  const t = normalizeTeamName(team);
  let wins = 0,
    draws = 0,
    losses = 0,
    gf = 0,
    ga = 0,
    count = 0;
  for (const m of matches) {
    const isHome = teamMatches(m.homeTeam, t);
    const isAway = teamMatches(m.awayTeam, t);
    if (!isHome && !isAway) continue;
    if (m.homeGoal == null || m.awayGoal == null) continue;
    count++;
    const own = isHome ? m.homeGoal : m.awayGoal;
    const opp = isHome ? m.awayGoal : m.homeGoal;
    gf += own;
    ga += opp;
    if (own > opp) wins++;
    else if (own < opp) losses++;
    else draws++;
  }
  return {
    team: t,
    matches: count,
    wins,
    draws,
    losses,
    goalsFor: gf,
    goalsAgainst: ga,
    points: wins * 3 + draws,
  };
}

/** Compute team record restricted to home or away fixtures. */
export function teamVenueRecord(
  matches: Match[],
  team: string,
  venue: 'home' | 'away',
): TeamRecord {
  const t = normalizeTeamName(team);
  const filtered = matches.filter((m) =>
    venue === 'home' ? teamMatches(m.homeTeam, t) : teamMatches(m.awayTeam, t),
  );
  return teamRecord(filtered, t);
}

/** All distinct team names found in the dataset. */
export function allTeams(matches: Match[]): string[] {
  const set = new Set<string>();
  for (const m of matches) {
    if (m.homeTeam) set.add(m.homeTeam);
    if (m.awayTeam) set.add(m.awayTeam);
  }
  return [...set].sort((a, b) => a.localeCompare(b));
}

/**
 * Calculate standings for a competition+season from match results.
 * Teams are ranked by points, then goal difference, then goals for.
 */
export function standings(
  matches: Match[],
  competition: Competition,
  season?: number,
): TeamRecord[] {
  const scoped = matches.filter(
    (m) =>
      m.competition === competition &&
      (season == null || m.season === season) &&
      m.homeGoal != null &&
      m.awayGoal != null,
  );

  const map = new Map<string, TeamRecord>();
  const ensure = (name: string): TeamRecord => {
    let r = map.get(name);
    if (!r) {
      r = {
        team: name,
        matches: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        goalsFor: 0,
        goalsAgainst: 0,
        points: 0,
      };
      map.set(name, r);
    }
    return r;
  };

  for (const m of scoped) {
    const h = ensure(m.homeTeam);
    const a = ensure(m.awayTeam);
    h.matches++;
    a.matches++;
    h.goalsFor += m.homeGoal!;
    h.goalsAgainst += m.awayGoal!;
    a.goalsFor += m.awayGoal!;
    a.goalsAgainst += m.homeGoal!;
    if (m.homeGoal! > m.awayGoal!) {
      h.wins++;
      a.losses++;
      h.points += 3;
    } else if (m.homeGoal! < m.awayGoal!) {
      a.wins++;
      h.losses++;
      a.points += 3;
    } else {
      h.draws++;
      a.draws++;
      h.points += 1;
      a.points += 1;
    }
  }

  return [...map.values()].sort((x, y) => {
    if (y.points !== x.points) return y.points - x.points;
    const gdY = y.goalsFor - y.goalsAgainst;
    const gdX = x.goalsFor - x.goalsAgainst;
    if (gdY !== gdX) return gdY - gdX;
    return y.goalsFor - x.goalsFor;
  });
}

/** Search players by name (case-insensitive substring). */
export function searchPlayers(players: Player[], name: string): Player[] {
  const q = name.trim().toLowerCase();
  if (!q) return [];
  return players.filter((p) => p.name.toLowerCase().includes(q));
}

/** Filter players by nationality (substring, accent-insensitive). */
export function playersByNationality(players: Player[], nationality: string): Player[] {
  const q = nationality.trim().toLowerCase();
  return players.filter(
    (p) => p.nationality && p.nationality.toLowerCase().includes(q),
  );
}

/** Filter players by club (substring, accent-insensitive). */
export function playersByClub(players: Player[], club: string): Player[] {
  const q = club.trim().toLowerCase();
  return players.filter((p) => p.club && p.club.toLowerCase().includes(q));
}

/** Top-N players by overall rating, with optional filters. */
export function topPlayers(
  players: Player[],
  opts: { limit?: number; nationality?: string; club?: string; position?: string } = {},
): Player[] {
  let out = players;
  if (opts.nationality) out = playersByNationality(out, opts.nationality);
  if (opts.club) out = playersByClub(out, opts.club);
  if (opts.position) {
    const q = opts.position.toLowerCase();
    out = out.filter((p) => p.position && p.position.toLowerCase() === q);
  }
  out = [...out]
    .filter((p) => p.overall != null)
    .sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
  if (opts.limit != null) out = out.slice(0, opts.limit);
  return out;
}

/** Average goals per match across a set of matches (skips unplayed). */
export function averageGoalsPerMatch(matches: Match[]): number {
  let total = 0;
  let count = 0;
  for (const m of matches) {
    if (m.homeGoal == null || m.awayGoal == null) continue;
    total += m.homeGoal + m.awayGoal;
    count++;
  }
  return count === 0 ? 0 : total / count;
}

/** Home win / draw / away win rates across a set of matches. */
export function homeAwayRates(matches: Match[]): {
  homeWinRate: number;
  drawRate: number;
  awayWinRate: number;
  total: number;
} {
  let home = 0,
    draw = 0,
    away = 0,
    total = 0;
  for (const m of matches) {
    if (m.homeGoal == null || m.awayGoal == null) continue;
    total++;
    if (m.homeGoal > m.awayGoal) home++;
    else if (m.homeGoal < m.awayGoal) away++;
    else draw++;
  }
  return {
    homeWinRate: total === 0 ? 0 : home / total,
    drawRate: total === 0 ? 0 : draw / total,
    awayWinRate: total === 0 ? 0 : away / total,
    total,
  };
}

/** Biggest victories (goal difference) across a set of matches. */
export function biggestWins(matches: Match[], limit = 10): Match[] {
  return [...matches]
    .filter((m) => m.homeGoal != null && m.awayGoal != null)
    .map((m) => ({ m, diff: Math.abs(m.homeGoal! - m.awayGoal!) }))
    .sort((a, b) => b.diff - a.diff)
    .slice(0, limit)
    .map((x) => x.m);
}

/** Champion (top of standings) for a competition+season. */
export function champion(
  matches: Match[],
  competition: Competition,
  season: number,
): TeamRecord | undefined {
  return standings(matches, competition, season)[0];
}

/** Relegated teams: bottom N of standings for a competition+season. */
export function relegated(
  matches: Match[],
  competition: Competition,
  season: number,
  bottomN = 4,
): TeamRecord[] {
  const table = standings(matches, competition, season);
  return table.slice(Math.max(0, table.length - bottomN));
}

/** All competitions present in the dataset. */
export function allCompetitions(matches: Match[]): Competition[] {
  return [...new Set(matches.map((m) => m.competition))].sort();
}

/** Distinct seasons present for a competition. */
export function seasonsFor(matches: Match[], competition?: Competition): number[] {
  const set = new Set<number>();
  for (const m of matches) {
    if (competition && m.competition !== competition) continue;
    if (m.season != null) set.add(m.season);
  }
  return [...set].sort((a, b) => a - b);
}

/** Find the most recent match between two teams (by date). */
export function lastMatchBetween(
  matches: Match[],
  teamA: string,
  teamB: string,
): Match | undefined {
  const h2h = headToHeadMatches(matches, teamA, teamB);
  return h2h.length === 0 ? undefined : h2h[h2h.length - 1];
}

/** Convenience: parse an ISO date string for comparison. */
export function toDateKey(s: string | null | undefined): string | null {
  if (!s) return null;
  return parseDate(s) ?? s;
}

/** Re-export for tool layer convenience. */
export { teamsEqual };
