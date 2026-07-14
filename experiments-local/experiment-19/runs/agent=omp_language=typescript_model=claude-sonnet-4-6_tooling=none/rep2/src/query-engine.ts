import { normalizeForSearch, teamMatches } from './normalize.js';
import type { Competition, Match, Player, TeamRecord } from './types.js';

// ---------------------------------------------------------------------------
// Match queries
// ---------------------------------------------------------------------------

export interface MatchFilter {
  team?: string;
  opponent?: string;
  competition?: string;
  season?: number;
  dateFrom?: string;
  dateTo?: string;
  /** 'home'|'away'|'all' — applies when `team` is set */
  venue?: 'home' | 'away' | 'all';
}

/**
 * Normalize a user-supplied competition string to the canonical Competition name.
 * Accepts partial/fuzzy strings like "brasileirao", "copa brasil", "libertadores".
 */
export function resolveCompetition(input: string): Competition | null {
  const s = normalizeForSearch(input);
  if (s.includes('brasilei') || s === 'serie a' || s === 'seriea') return 'Brasileirão Serie A';
  if (s.includes('copa') && s.includes('brasil')) return 'Copa do Brasil';
  if (s.includes('libertad')) return 'Copa Libertadores';
  if (s === 'serie b' || s === 'serieb') return 'Serie B';
  if (s === 'serie c' || s === 'seriec') return 'Serie C';
  return null;
}

/**
 * Filter matches by the supplied criteria. Returns matches sorted newest-first.
 */
export function filterMatches(matches: Match[], filter: MatchFilter): Match[] {
  const comp = filter.competition ? resolveCompetition(filter.competition) : null;

  return matches
    .filter((m) => {
      if (filter.season && m.season !== filter.season) return false;
      if (comp && m.competition !== comp) return false;
      if (filter.dateFrom && m.date < filter.dateFrom) return false;
      if (filter.dateTo && m.date > filter.dateTo) return false;

      if (filter.team) {
        const homeMatch = teamMatches(m.homeTeam, filter.team) || teamMatches(m.homeTeamNormalized, filter.team);
        const awayMatch = teamMatches(m.awayTeam, filter.team) || teamMatches(m.awayTeamNormalized, filter.team);
        const venue = filter.venue ?? 'all';
        if (venue === 'home' && !homeMatch) return false;
        if (venue === 'away' && !awayMatch) return false;
        if (venue === 'all' && !homeMatch && !awayMatch) return false;
      }

      if (filter.opponent) {
        const homeMatch = teamMatches(m.homeTeam, filter.opponent) || teamMatches(m.homeTeamNormalized, filter.opponent);
        const awayMatch = teamMatches(m.awayTeam, filter.opponent) || teamMatches(m.awayTeamNormalized, filter.opponent);
        if (!homeMatch && !awayMatch) return false;
      }

      return true;
    })
    .sort((a, b) => b.date.localeCompare(a.date));
}

// ---------------------------------------------------------------------------
// Team statistics
// ---------------------------------------------------------------------------

/**
 * Build a record for one team from a slice of matches.
 * The team name must already be matched/filtered externally.
 */
export function buildTeamRecord(team: string, matches: Match[]): TeamRecord {
  let wins = 0, draws = 0, losses = 0, gf = 0, ga = 0;

  for (const m of matches) {
    const isHome = teamMatches(m.homeTeam, team) || teamMatches(m.homeTeamNormalized, team);
    const isAway = teamMatches(m.awayTeam, team) || teamMatches(m.awayTeamNormalized, team);
    if (!isHome && !isAway) continue;

    const teamGoals = isHome ? m.homeGoals : m.awayGoals;
    const oppGoals = isHome ? m.awayGoals : m.homeGoals;
    gf += teamGoals;
    ga += oppGoals;
    if (teamGoals > oppGoals) wins++;
    else if (teamGoals === oppGoals) draws++;
    else losses++;
  }

  const played = wins + draws + losses;
  return {
    team,
    matches: played,
    wins,
    draws,
    losses,
    goalsFor: gf,
    goalsAgainst: ga,
    goalDiff: gf - ga,
    points: wins * 3 + draws,
    winRate: played > 0 ? wins / played : 0,
  };
}

/**
 * Compute league table (standings) from a set of matches for a single season.
 */
export function computeStandings(matches: Match[]): TeamRecord[] {
  // Use original team name (with state suffix) as key to avoid merging e.g. Atletico-MG + Atletico-PR
  const teamNames = new Map<string, string>(); // lowerCaseKey → display name
  for (const m of matches) {
    const hKey = normalizeForSearch(m.homeTeam);
    const aKey = normalizeForSearch(m.awayTeam);
    if (!teamNames.has(hKey)) teamNames.set(hKey, m.homeTeam);
    if (!teamNames.has(aKey)) teamNames.set(aKey, m.awayTeam);
  }

  const table: TeamRecord[] = [];
  for (const [, name] of teamNames) {
    // Exact-match by original name: avoids fuzzy cross-contamination between
    // teams that share a base name (e.g. Atletico-MG vs Atletico-PR).
    const teamMatches2 = matches.filter(
      (m) => m.homeTeam === name || m.awayTeam === name
    );
    if (teamMatches2.length === 0) continue;
    const rec = buildTeamRecord(name, teamMatches2);
    if (rec.matches > 0) table.push(rec);
  }

  // Sort: points desc, goal diff desc, goals for desc, name asc
  table.sort(
    (a, b) =>
      b.points - a.points ||
      b.goalDiff - a.goalDiff ||
      b.goalsFor - a.goalsFor ||
      a.team.localeCompare(b.team)
  );

  return table;
}

// ---------------------------------------------------------------------------
// Head-to-head
// ---------------------------------------------------------------------------

export interface HeadToHeadSummary {
  team1: string;
  team2: string;
  matches: Match[];
  team1Wins: number;
  team2Wins: number;
  draws: number;
  team1Goals: number;
  team2Goals: number;
}

export function headToHead(
  allMatches: Match[],
  team1: string,
  team2: string,
  competition?: string,
  season?: number
): HeadToHeadSummary {
  const filtered = filterMatches(allMatches, {
    team: team1,
    opponent: team2,
    competition,
    season,
  });

  let t1Wins = 0, t2Wins = 0, draws = 0, t1Goals = 0, t2Goals = 0;
  for (const m of filtered) {
    const t1IsHome = teamMatches(m.homeTeam, team1) || teamMatches(m.homeTeamNormalized, team1);
    const t1G = t1IsHome ? m.homeGoals : m.awayGoals;
    const t2G = t1IsHome ? m.awayGoals : m.homeGoals;
    t1Goals += t1G;
    t2Goals += t2G;
    if (t1G > t2G) t1Wins++;
    else if (t1G < t2G) t2Wins++;
    else draws++;
  }

  return { team1, team2, matches: filtered, team1Wins: t1Wins, team2Wins: t2Wins, draws, team1Goals: t1Goals, team2Goals: t2Goals };
}

// ---------------------------------------------------------------------------
// Player queries
// ---------------------------------------------------------------------------

export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  maxOverall?: number;
}

export function filterPlayers(players: Player[], filter: PlayerFilter): Player[] {
  return players.filter((p) => {
    if (filter.name && !normalizeForSearch(p.name).includes(normalizeForSearch(filter.name))) return false;
    if (filter.nationality && !normalizeForSearch(p.nationality ?? '').includes(normalizeForSearch(filter.nationality))) return false;
    if (filter.club && !normalizeForSearch(p.club ?? '').includes(normalizeForSearch(filter.club))) return false;
    if (filter.position && !normalizeForSearch(p.position ?? '').includes(normalizeForSearch(filter.position))) return false;
    if (filter.minOverall !== undefined && (p.overall ?? 0) < filter.minOverall) return false;
    if (filter.maxOverall !== undefined && (p.overall ?? 999) > filter.maxOverall) return false;
    return true;
  });
}

// ---------------------------------------------------------------------------
// Aggregate / statistical analysis
// ---------------------------------------------------------------------------

export interface CompetitionOverview {
  competition: string;
  totalMatches: number;
  totalGoals: number;
  avgGoalsPerMatch: number;
  homeWins: number;
  awayWins: number;
  draws: number;
  homeWinRate: number;
}

export function competitionOverview(matches: Match[]): CompetitionOverview {
  let totalGoals = 0, homeWins = 0, awayWins = 0, draws = 0;
  for (const m of matches) {
    totalGoals += m.homeGoals + m.awayGoals;
    if (m.homeGoals > m.awayGoals) homeWins++;
    else if (m.homeGoals < m.awayGoals) awayWins++;
    else draws++;
  }
  const total = matches.length;
  return {
    competition: matches[0]?.competition ?? 'Unknown',
    totalMatches: total,
    totalGoals,
    avgGoalsPerMatch: total > 0 ? totalGoals / total : 0,
    homeWins,
    awayWins,
    draws,
    homeWinRate: total > 0 ? homeWins / total : 0,
  };
}

/** Return matches sorted by goal margin (biggest wins first). */
export function biggestWins(matches: Match[], limit: number): Match[] {
  return [...matches]
    .filter((m) => m.homeGoals !== m.awayGoals)
    .sort((a, b) => {
      const marginA = Math.abs(a.homeGoals - a.awayGoals);
      const marginB = Math.abs(b.homeGoals - b.awayGoals);
      return marginB - marginA || b.date.localeCompare(a.date);
    })
    .slice(0, limit);
}

/** Return top-scoring matches. */
export function highScoringMatches(matches: Match[], limit: number): Match[] {
  return [...matches]
    .sort((a, b) => {
      const totA = a.homeGoals + a.awayGoals;
      const totB = b.homeGoals + b.awayGoals;
      return totB - totA || b.date.localeCompare(a.date);
    })
    .slice(0, limit);
}

/** Rank teams by a derived metric across a set of matches. */
export function rankTeams(
  matches: Match[],
  metric: 'wins' | 'goals_for' | 'goals_against' | 'points' | 'away_record' | 'home_record',
  limit: number
): TeamRecord[] {
  const teamNames = new Map<string, string>();
  for (const m of matches) {
    const hKey = normalizeForSearch(m.homeTeamNormalized);
    const aKey = normalizeForSearch(m.awayTeamNormalized);
    if (!teamNames.has(hKey)) teamNames.set(hKey, m.homeTeamNormalized);
    if (!teamNames.has(aKey)) teamNames.set(aKey, m.awayTeamNormalized);
  }

  const records: TeamRecord[] = [];
  for (const [, name] of teamNames) {
    let relevantMatches = matches;
    if (metric === 'home_record') {
      relevantMatches = matches.filter(
        (m) => teamMatches(m.homeTeam, name) || teamMatches(m.homeTeamNormalized, name)
      );
    } else if (metric === 'away_record') {
      relevantMatches = matches.filter(
        (m) => teamMatches(m.awayTeam, name) || teamMatches(m.awayTeamNormalized, name)
      );
    }
    const rec = buildTeamRecord(name, relevantMatches);
    if (rec.matches > 0) records.push(rec);
  }

  type Metric = 'wins' | 'goals_for' | 'goals_against' | 'points' | 'away_record' | 'home_record';
  const sortKeyMap: Record<Metric, (r: TeamRecord) => number> = {
    wins: (r) => r.wins,
    goals_for: (r) => r.goalsFor,
    goals_against: (r) => -r.goalsAgainst,
    points: (r) => r.points,
    away_record: (r) => r.points,
    home_record: (r) => r.points,
  };
  const sortKey = sortKeyMap[metric];

  return records.sort((a, b) => sortKey(b) - sortKey(a)).slice(0, limit);
}
