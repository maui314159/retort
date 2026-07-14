/**
 * Brazilian Soccer MCP Server - Query Engine
 *
 * All data query functions: match search, team stats, player search,
 * competition standings, head-to-head, and statistical analysis.
 */

import { getMatches, getPlayers } from './data.js';
import { normalizeTeam } from './normalize.js';
import type {
  NormalizedMatch,
  NormalizedPlayer,
  MatchQuery,
  PlayerQuery,
  TeamRecord,
  TeamStats,
  HeadToHead,
  StandingEntry,
} from './types.js';

// ── Helpers ──────────────────────────────────────────────────────────

function teamMatchesQuery(
  team: NormalizedMatch,
  normalizedTeam: string
): boolean {
  return team.homeTeam === normalizedTeam || team.awayTeam === normalizedTeam;
}

function emptyTeamStats(team: string, display: string): TeamStats {
  return { team, teamDisplay: display, matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0, points: 0 };
}

function calcStats(teamName: string, display: string, matches: NormalizedMatch[]): TeamStats {
  const stats = emptyTeamStats(teamName, display);
  for (const m of matches) {
    const isHome = m.homeTeam === teamName;
    stats.matches++;
    stats.goalsFor += isHome ? m.homeGoal : m.awayGoal;
    stats.goalsAgainst += isHome ? m.awayGoal : m.homeGoal;
    if (m.homeGoal === m.awayGoal) {
      stats.draws++;
      stats.points += 1;
    } else if ((isHome && m.homeGoal > m.awayGoal) || (!isHome && m.awayGoal > m.homeGoal)) {
      stats.wins++;
      stats.points += 3;
    } else {
      stats.losses++;
    }
  }
  return stats;
}

// ── Match Queries ────────────────────────────────────────────────────

export function searchMatches(query: MatchQuery): NormalizedMatch[] {
  let matches = getMatches();
  const team = query.team ? normalizeTeam(query.team).key : null;
  const opponent = query.opponent ? normalizeTeam(query.opponent).key : null;

  if (team && opponent) {
    // Both specified: exactly those two teams
    matches = matches.filter(m =>
      (m.homeTeam === team && m.awayTeam === opponent) ||
      (m.homeTeam === opponent && m.awayTeam === team)
    );
  } else if (team) {
    matches = matches.filter(m => teamMatchesQuery(m, team));
  }

  if (query.competition) {
    const comp = query.competition.toLowerCase().replace(/[^a-z_]/g, '_');
    // Map common names
    const compKey = comp.includes('brasileir') || comp.includes('serie_a') ? 'brasileirao'
      : comp.includes('copa') && comp.includes('brasil') ? 'copa_do_brasil'
      : comp.includes('libertadores') ? 'libertadores'
      : comp;
    matches = matches.filter(m => m.competition === compKey);
  }

  if (query.season) {
    matches = matches.filter(m => m.season === query.season);
  }

  if (query.dateFrom) {
    matches = matches.filter(m => m.date >= query.dateFrom!);
  }
  if (query.dateTo) {
    matches = matches.filter(m => m.date <= query.dateTo!);
  }

  // Sort by date descending
  matches.sort((a, b) => b.date.localeCompare(a.date) || b.season - a.season);

  if (query.limit && query.limit > 0) {
    matches = matches.slice(0, query.limit);
  }

  return matches;
}

// ── Team Statistics ──────────────────────────────────────────────────

export function getTeamRecord(teamName: string): TeamRecord | null {
  const normalized = normalizeTeam(teamName);
  if (!normalized.key) return null;

  const allMatches = getMatches().filter(m => teamMatchesQuery(m, normalized.key));
  if (allMatches.length === 0) return null;

  const homeMatches = allMatches.filter(m => m.homeTeam === normalized.key);
  const awayMatches = allMatches.filter(m => m.awayTeam === normalized.key);

  // Per-competition stats
  const compMap = new Map<string, NormalizedMatch[]>();
  for (const m of allMatches) {
    const existing = compMap.get(m.competition) || [];
    existing.push(m);
    compMap.set(m.competition, existing);
  }
  const compStats: Record<string, TeamStats> = {};
  for (const [comp, ms] of compMap) {
    compStats[comp] = calcStats(normalized.key, normalized.display, ms);
  }

  return {
    ...calcStats(normalized.key, normalized.display, allMatches),
    homeStats: calcStats(normalized.key, normalized.display, homeMatches),
    awayStats: calcStats(normalized.key, normalized.display, awayMatches),
    competitions: compStats,
  };
}

// ── Head-to-Head ─────────────────────────────────────────────────────

export function getHeadToHead(team1: string, team2: string): HeadToHead | null {
  const t1 = normalizeTeam(team1);
  const t2 = normalizeTeam(team2);
  if (!t1.key || !t2.key) return null;

  const matches = getMatches().filter(m =>
    (m.homeTeam === t1.key && m.awayTeam === t2.key) ||
    (m.homeTeam === t2.key && m.awayTeam === t1.key)
  ).sort((a, b) => b.date.localeCompare(a.date));

  if (matches.length === 0) return null;

  let t1Wins = 0, t2Wins = 0, draws = 0, t1Goals = 0, t2Goals = 0;

  for (const m of matches) {
    if (m.homeTeam === t1.key) {
      t1Goals += m.homeGoal;
      t2Goals += m.awayGoal;
      if (m.homeGoal > m.awayGoal) t1Wins++;
      else if (m.homeGoal < m.awayGoal) t2Wins++;
      else draws++;
    } else {
      t1Goals += m.awayGoal;
      t2Goals += m.homeGoal;
      if (m.awayGoal > m.homeGoal) t1Wins++;
      else if (m.awayGoal < m.homeGoal) t2Wins++;
      else draws++;
    }
  }

  return {
    team1: t1.key,
    team1Display: t1.display,
    team2: t2.key,
    team2Display: t2.display,
    totalMatches: matches.length,
    team1Wins: t1Wins,
    team2Wins: t2Wins,
    draws,
    team1Goals: t1Goals,
    team2Goals: t2Goals,
    matches,
  };
}

// ── Player Queries ───────────────────────────────────────────────────

export function searchPlayers(query: PlayerQuery): NormalizedPlayer[] {
  let players = getPlayers();

  if (query.name) {
    const q = query.name.toLowerCase();
    players = players.filter(p => p.name.toLowerCase().includes(q));
  }

  if (query.nationality) {
    const nat = query.nationality.toLowerCase().trim();
    players = players.filter(p => p.nationality.toLowerCase() === nat);
  }

  if (query.club) {
    const club = normalizeTeam(query.club).key;
    if (club) {
      players = players.filter(p => p.club.includes(club));
    }
  }

  if (query.position) {
    const pos = query.position.toUpperCase().trim();
    players = players.filter(p => {
      const pPos = p.position.toUpperCase();
      // Allow partial match (e.g., "CDM" matches "CDM", "CB" matches "CB")
      return pPos.includes(pos);
    });
  }

  if (query.minRating !== undefined) {
    players = players.filter(p => p.overall >= query.minRating!);
  }
  if (query.maxRating !== undefined) {
    players = players.filter(p => p.overall <= query.maxRating!);
  }

  // Sort
  const sortBy = query.sortBy || '-overall';
  const desc = sortBy.startsWith('-');
  const field = desc ? sortBy.slice(1) : sortBy;

  players.sort((a, b) => {
    const aVal = (a as any)[field] ?? 0;
    const bVal = (b as any)[field] ?? 0;
    return desc ? bVal - aVal : aVal - bVal;
  });

  if (query.limit && query.limit > 0) {
    players = players.slice(0, query.limit);
  }

  return players;
}

// ── Competition Standings ────────────────────────────────────────────

const BRAZILIAN_POINTS_PER_WIN = 3;

export function getStandings(competition: string, season: number): StandingEntry[] {
  const compKey = competition.toLowerCase().replace(/[^a-z_]/g, '_');
  const cKey = compKey.includes('brasileir') || compKey.includes('serie_a') ? 'brasileirao'
    : compKey.includes('copa') && compKey.includes('brasil') ? 'copa_do_brasil'
    : compKey.includes('libertadores') ? 'libertadores'
    : compKey;

  const matches = getMatches().filter(m => m.competition === cKey && m.season === season);
  if (matches.length === 0) return [];

  // Accumulate per team
  const map = new Map<string, { display: string; played: number; wins: number; draws: number; losses: number; gf: number; ga: number }>();
  for (const m of matches) {
    for (const [team, display, gf, ga] of [
      [m.homeTeam, m.homeTeamDisplay, m.homeGoal, m.awayGoal] as const,
      [m.awayTeam, m.awayTeamDisplay, m.awayGoal, m.homeGoal] as const,
    ]) {
      let entry = map.get(team);
      if (!entry) {
        entry = { display, played: 0, wins: 0, draws: 0, losses: 0, gf: 0, ga: 0 };
        map.set(team, entry);
      }
      entry.played++;
      entry.gf += gf;
      entry.ga += ga;
      if (gf > ga) entry.wins++;
      else if (gf < ga) entry.losses++;
      else entry.draws++;
    }
  }

  // Convert to standings
  const standings: StandingEntry[] = [...map.entries()].map(([team, e]) => ({
    position: 0,
    team,
    teamDisplay: e.display,
    played: e.played,
    wins: e.wins,
    draws: e.draws,
    losses: e.losses,
    goalsFor: e.gf,
    goalsAgainst: e.ga,
    goalDifference: e.gf - e.ga,
    points: e.wins * BRAZILIAN_POINTS_PER_WIN + e.draws,
  }));

  // Sort: points DESC, wins DESC, goal diff DESC, goals for DESC
  standings.sort((a, b) =>
    b.points - a.points ||
    b.wins - a.wins ||
    b.goalDifference - a.goalDifference ||
    b.goalsFor - a.goalsFor
  );

  standings.forEach((s, i) => { s.position = i + 1; });

  return standings;
}

// ── Statistical Queries ──────────────────────────────────────────────

export function getBiggestWins(competition?: string, limit = 10): NormalizedMatch[] {
  let matches = getMatches();
  if (competition) {
    const cKey = competition.toLowerCase().replace(/[^a-z_]/g, '_');
    matches = matches.filter(m => m.competition === cKey || m.competition.includes(cKey));
  }
  // Only consider wins (not draws)
  matches = matches.filter(m => m.homeGoal !== m.awayGoal);
  matches.sort((a, b) => {
    const aDiff = Math.abs(a.homeGoal - a.awayGoal);
    const bDiff = Math.abs(b.homeGoal - b.awayGoal);
    return bDiff - aDiff || (b.homeGoal + b.awayGoal) - (a.homeGoal + a.awayGoal);
  });
  return matches.slice(0, limit);
}

export function getAverageGoals(competition?: string, season?: number): { avgGoalsPerMatch: number; totalMatches: number; totalGoals: number } {
  let matches = getMatches();
  if (competition) {
    const cKey = competition.toLowerCase().replace(/[^a-z_]/g, '_');
    matches = matches.filter(m => m.competition === cKey);
  }
  if (season) {
    matches = matches.filter(m => m.season === season);
  }
  const totalGoals = matches.reduce((sum, m) => sum + m.homeGoal + m.awayGoal, 0);
  return {
    avgGoalsPerMatch: matches.length > 0 ? Math.round((totalGoals / matches.length) * 100) / 100 : 0,
    totalMatches: matches.length,
    totalGoals,
  };
}

export function getHomeAwayStats(competition?: string, season?: number): {
  homeWins: number;
  awayWins: number;
  draws: number;
  totalMatches: number;
  homeWinRate: number;
} {
  let matches = getMatches();
  if (competition) {
    const cKey = competition.toLowerCase().replace(/[^a-z_]/g, '_');
    matches = matches.filter(m => m.competition === cKey);
  }
  if (season) {
    matches = matches.filter(m => m.season === season);
  }

  let homeWins = 0, awayWins = 0, draws = 0;
  for (const m of matches) {
    if (m.homeGoal > m.awayGoal) homeWins++;
    else if (m.awayGoal > m.homeGoal) awayWins++;
    else draws++;
  }

  return {
    homeWins,
    awayWins,
    draws,
    totalMatches: matches.length,
    homeWinRate: matches.length > 0 ? Math.round((homeWins / matches.length) * 1000) / 10 : 0,
  };
}

export function getTopScoringTeams(competition?: string, season?: number, limit = 10): { team: string; teamDisplay: string; goals: number; matches: number }[] {
  let matches = getMatches();
  if (competition) {
    const cKey = competition.toLowerCase().replace(/[^a-z_]/g, '_');
    matches = matches.filter(m => m.competition === cKey);
  }
  if (season) {
    matches = matches.filter(m => m.season === season);
  }

  const map = new Map<string, { display: string; goals: number; matches: number }>();
  for (const m of matches) {
    for (const [team, display, goals] of [
      [m.homeTeam, m.homeTeamDisplay, m.homeGoal] as const,
      [m.awayTeam, m.awayTeamDisplay, m.awayGoal] as const,
    ]) {
      let entry = map.get(team);
      if (!entry) {
        entry = { display, goals: 0, matches: 0 };
        map.set(team, entry);
      }
      entry.goals += goals;
      entry.matches++;
    }
  }

  return [...map.entries()]
    .map(([team, e]) => ({ team, teamDisplay: e.display, goals: e.goals, matches: e.matches }))
    .sort((a, b) => b.goals - a.goals)
    .slice(0, limit);
}

export function getTeamBestAwayRecord(limit = 10): { team: string; teamDisplay: string; awayWins: number; awayMatches: number; awayWinRate: number }[] {
  const matches = getMatches();
  const map = new Map<string, { display: string; wins: number; total: number }>();

  for (const m of matches) {
    let entry = map.get(m.awayTeam);
    if (!entry) {
      entry = { display: m.awayTeamDisplay, wins: 0, total: 0 };
      map.set(m.awayTeam, entry);
    }
    entry.total++;
    if (m.awayGoal > m.homeGoal) entry.wins++;
  }

  return [...map.entries()]
    .filter(([, e]) => e.total >= 5)
    .map(([team, e]) => ({
      team,
      teamDisplay: e.display,
      awayWins: e.wins,
      awayMatches: e.total,
      awayWinRate: Math.round((e.wins / e.total) * 1000) / 10,
    }))
    .sort((a, b) => b.awayWinRate - a.awayWinRate)
    .slice(0, limit);
}

export function getCompetitionList(): string[] {
  const comps = new Set<string>();
  for (const m of getMatches()) {
    comps.add(m.competition);
  }
  return [...comps].sort();
}

export function getSeasonList(competition?: string): number[] {
  let matches = getMatches();
  if (competition) {
    const cKey = competition.toLowerCase().replace(/[^a-z_]/g, '_');
    matches = matches.filter(m => m.competition === cKey);
  }
  const seasons = new Set<number>();
  for (const m of matches) {
    seasons.add(m.season);
  }
  return [...seasons].sort((a, b) => b - a);
}
