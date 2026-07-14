/**
 * brazilian-soccer-mcp / src/queries.ts
 *
 * Query layer over the normalized data.
 *
 * Context block:
 * Pure functions that operate on the normalized `Match[]` / `Player[]` arrays
 * loaded by data-loader.ts. Each function corresponds to one of the MCP tool
 * capabilities in the spec (match queries, team queries, player queries,
 * competition queries, statistical analysis). Team matching always goes
 * through `teamKey` so that name variations ("Palmeiras-SP", "Palmeiras")
 * resolve to the same side. All filters accept `null`/`undefined` as "no
 * filter" so a single tool call can combine arbitrary criteria.
 */
import type {
  Match, Player, TeamStats, HeadToHead, StandingRow, AggregateStats, ClubSummary,
} from './types.js';
import { teamKey, foldAccents } from './team-normalizer.js';

export interface MatchFilter {
  team?: string;
  opponent?: string;
  homeTeam?: string;
  awayTeam?: string;
  competition?: string;
  season?: number;
  seasonFrom?: number;
  seasonTo?: number;
  dateFrom?: string;
  dateTo?: string;
  venue?: 'home' | 'away' | 'either';
}

function competitionMatches(compFilter: string | undefined, m: Match): boolean {
  if (!compFilter) return true;
  const want = foldAccents(compFilter).toLowerCase().trim();
  const have = foldAccents(m.competition).toLowerCase().trim();
  // Substring match so "brasileirao" matches "brasileirão série a".
  return have.includes(want);
}

function dateInRange(m: Match, from?: string, to?: string): boolean {
  if (!m.date) return true;
  if (from && m.date < new Date(from)) return false;
  if (to && m.date > new Date(to)) return false;
  return true;
}

/** Find matches matching the given filter criteria. */
export function findMatches(matches: Match[], filter: MatchFilter): Match[] {
  const teamKeyOpt = filter.team ? teamKey(filter.team) : null;
  const oppKey = filter.opponent ? teamKey(filter.opponent) : null;
  const homeKey = filter.homeTeam ? teamKey(filter.homeTeam) : null;
  const awayKey = filter.awayTeam ? teamKey(filter.awayTeam) : null;

  return matches.filter((m) => {
    if (!competitionMatches(filter.competition, m)) return false;
    if (filter.season !== undefined && m.season !== filter.season) return false;
    if (filter.seasonFrom !== undefined && (m.season ?? 0) < filter.seasonFrom) return false;
    if (filter.seasonTo !== undefined && (m.season ?? 0) > filter.seasonTo) return false;
    if (!dateInRange(m, filter.dateFrom, filter.dateTo)) return false;

    if (homeKey && m.homeTeamKey !== homeKey) return false;
    if (awayKey && m.awayTeamKey !== awayKey) return false;

    if (teamKeyOpt) {
      const isHome = m.homeTeamKey === teamKeyOpt;
      const isAway = m.awayTeamKey === teamKeyOpt;
      if (filter.venue === 'home' && !isHome) return false;
      if (filter.venue === 'away' && !isAway) return false;
      if (!filter.venue || filter.venue === 'either') {
        if (!isHome && !isAway) return false;
      }
    }
    if (oppKey && teamKeyOpt) {
      // Require the opponent to be on the opposite side of the queried team.
      if (m.homeTeamKey === teamKeyOpt && m.awayTeamKey !== oppKey) return false;
      if (m.awayTeamKey === teamKeyOpt && m.homeTeamKey !== oppKey) return false;
      if (m.homeTeamKey !== teamKeyOpt && m.awayTeamKey !== teamKeyOpt) return false;
    }
    return true;
  });
}

/** All matches between two teams (either order), newest first. */
export function headToHeadMatches(matches: Match[], teamA: string, teamB: string): Match[] {
  const a = teamKey(teamA);
  const b = teamKey(teamB);
  const found = matches.filter(
    (m) =>
      (m.homeTeamKey === a && m.awayTeamKey === b) ||
      (m.homeTeamKey === b && m.awayTeamKey === a),
  );
  return found.sort((x, y) => (y.date?.getTime() ?? 0) - (x.date?.getTime() ?? 0));
}

/** Compute head-to-head summary between two teams. */
export function headToHead(matches: Match[], teamA: string, teamB: string): HeadToHead {
  const a = teamKey(teamA);
  const games = headToHeadMatches(matches, teamA, teamB);
  let aWins = 0, bWins = 0, draws = 0;
  for (const m of games) {
    if (m.homeGoals === null || m.awayGoals === null) continue;
    const homeWon = m.homeGoals > m.awayGoals;
    const awayWon = m.awayGoals > m.homeGoals;
    if (homeWon) {
      if (m.homeTeamKey === a) aWins++; else bWins++;
    } else if (awayWon) {
      if (m.awayTeamKey === a) aWins++; else bWins++;
    } else {
      draws++;
    }
  }
  return { teamA, teamB, matches: games.length, aWins, bWins, draws };
}

/** Result of a single match from a team's perspective. */
type TeamResult = 'win' | 'draw' | 'loss';

function resultFor(m: Match, key: string): TeamResult | null {
  if (m.homeGoals === null || m.awayGoals === null) return null;
  const isHome = m.homeTeamKey === key;
  const isAway = m.awayTeamKey === key;
  if (!isHome && !isAway) return null;
  const gf = isHome ? m.homeGoals : m.awayGoals;
  const ga = isHome ? m.awayGoals : m.homeGoals;
  if (gf > ga) return 'win';
  if (gf < ga) return 'loss';
  return 'draw';
}

/** Compute aggregate statistics for a team over a set of matches. */
export function teamStats(matches: Match[], team: string, filter?: MatchFilter): TeamStats {
  const key = teamKey(team);
  const scoped = filter ? findMatches(matches, filter) : matches;
  let wins = 0, draws = 0, losses = 0, gf = 0, ga = 0, played = 0;
  for (const m of scoped) {
    const r = resultFor(m, key);
    if (!r) continue;
    played++;
    const isHome = m.homeTeamKey === key;
    const teamGf = isHome ? (m.homeGoals ?? 0) : (m.awayGoals ?? 0);
    const teamGa = isHome ? (m.awayGoals ?? 0) : (m.homeGoals ?? 0);
    gf += teamGf;
    ga += teamGa;
    if (r === 'win') wins++;
    else if (r === 'draw') draws++;
    else losses++;
  }
  const points = wins * 3 + draws;
  const goalDifference = gf - ga;
  const winRate = played > 0 ? wins / played : 0;
  return { team, matches: played, wins, draws, losses, goalsFor: gf, goalsAgainst: ga, goalDifference, points, winRate };
}

/** Aggregate statistics over an arbitrary set of matches. */
export function aggregateStats(matches: Match[]): AggregateStats {
  let totalGoals = 0, scored = 0, homeWins = 0, awayWins = 0, draws = 0;
  for (const m of matches) {
    if (m.homeGoals === null || m.awayGoals === null) continue;
    scored++;
    totalGoals += m.homeGoals + m.awayGoals;
    if (m.homeGoals > m.awayGoals) homeWins++;
    else if (m.awayGoals > m.homeGoals) awayWins++;
    else draws++;
  }
  const averageGoalsPerMatch = scored > 0 ? totalGoals / scored : 0;
  return {
    matches: scored,
    totalGoals,
    averageGoalsPerMatch,
    homeWins, awayWins, draws,
    homeWinRate: scored > 0 ? homeWins / scored : 0,
    awayWinRate: scored > 0 ? awayWins / scored : 0,
    drawRate: scored > 0 ? draws / scored : 0,
  };
}

/** Biggest victories (by goal difference) within a set of matches. */
export function biggestWins(matches: Match[], limit = 10): Match[] {
  const scored = matches.filter((m) => m.homeGoals !== null && m.awayGoals !== null);
  return scored
    .map((m) => ({ m, diff: Math.abs((m.homeGoals ?? 0) - (m.awayGoals ?? 0)) }))
    .sort((a, b) => b.diff - a.diff || (b.m.date?.getTime() ?? 0) - (a.m.date?.getTime() ?? 0))
    .slice(0, limit)
    .map((x) => x.m);
}

/** Compute standings for a competition season from match results (3-1-0 points). */
export function standings(matches: Match[], competition: string, season: number): StandingRow[] {
  const compKey = foldAccents(competition).toLowerCase().trim();
  const seasonMatches = matches.filter(
    (m) => m.season === season && foldAccents(m.competition).toLowerCase().includes(compKey),
  );
  const table = new Map<string, StandingRow>();
  const displayName = new Map<string, string>();
  for (const m of seasonMatches) {
    if (m.homeGoals === null || m.awayGoals === null) continue;
    for (const [key, name, gf, ga] of [
      [m.homeTeamKey, m.homeTeam, m.homeGoals, m.awayGoals],
      [m.awayTeamKey, m.awayTeam, m.awayGoals, m.homeGoals],
    ] as const) {
      let row = table.get(key);
      if (!row) {
        row = { position: 0, team: name, played: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0, goalDifference: 0, points: 0 };
        table.set(key, row);
        displayName.set(key, name);
      }
      row.team = displayName.get(key) ?? name;
      row.played++;
      row.goalsFor += gf;
      if (gf > ga) { row.wins++; row.points += 3; }
      else if (gf < ga) { row.losses++; }
      else { row.draws++; row.points++; }
    }
  }
  const rows = [...table.values()];
  for (const r of rows) r.goalDifference = r.goalsFor - r.goalsAgainst;
  rows.sort((a, b) => b.points - a.points || b.wins - a.wins || b.goalDifference - a.goalDifference || b.goalsFor - a.goalsFor);
  rows.forEach((r, i) => { r.position = i + 1; });
  return rows;
}

/** Filter players by nationality, club, position, and/or name substring. */
export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  limit?: number;
}

export function findPlayers(players: Player[], filter: PlayerFilter): Player[] {
  const nameKey = filter.name ? foldAccents(filter.name).toLowerCase() : null;
  const natKey = filter.nationality ? foldAccents(filter.nationality).toLowerCase().trim() : null;
  const clubKey = filter.club ? foldAccents(filter.club).toLowerCase().trim() : null;
  const posKey = filter.position ? foldAccents(filter.position).toLowerCase().trim() : null;
  let result = players.filter((p) => {
    if (nameKey && !foldAccents(p.name).toLowerCase().includes(nameKey)) return false;
    if (natKey && !p.nationalityKey.includes(natKey)) return false;
    if (clubKey && !p.clubKey.includes(clubKey)) return false;
    if (posKey && foldAccents(p.position).toLowerCase() !== posKey) return false;
    if (filter.minOverall !== undefined && (p.overall ?? 0) < filter.minOverall) return false;
    return true;
  });
  result = result.sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
  if (filter.limit !== undefined) result = result.slice(0, filter.limit);
  return result;
}

/** List Brazilian clubs found in the player dataset, with player counts and average ratings. */
export function brazilianClubsSummary(players: Player[]): ClubSummary[] {
  const brazilianClubKeys = new Set<string>();
  const display = new Map<string, string>();
  for (const p of players) {
    if (p.nationalityKey === 'brazil' && p.club) {
      brazilianClubKeys.add(p.clubKey);
      display.set(p.clubKey, p.club);
    }
  }
  const out: ClubSummary[] = [];
  for (const key of brazilianClubKeys) {
    const clubPlayers = players.filter((p) => p.clubKey === key);
    const rated = clubPlayers.filter((p) => p.overall !== null);
    const avg = rated.length > 0
      ? rated.reduce((s, p) => s + (p.overall ?? 0), 0) / rated.length
      : 0;
    out.push({ club: display.get(key) ?? key, count: clubPlayers.length, avgOverall: avg });
  }
  return out.sort((a, b) => b.count - a.count || b.avgOverall - a.avgOverall);
}
