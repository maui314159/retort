import type { LoadedData } from './loader.js';
import type { Match, Player, TeamStats, CompetitionStanding } from './types.js';
import { canonicalTeamKey, normalizeTeamName, normalizeCompetition, escapeRegExp } from './normalize.js';

export interface MatchFilters {
  team?: string;
  team1?: string;
  team2?: string;
  homeTeam?: string;
  awayTeam?: string;
  competition?: string;
  season?: number;
  from?: string;
  to?: string;
  round?: string;
  stage?: string;
  limit?: number;
}

function teamMatches(name: string, match: Match): boolean {
  const keys = [match.home_team, match.away_team].map(canonicalTeamKey);
  return keys.includes(canonicalTeamKey(name));
}

function bothTeams(name1: string, name2: string, match: Match): boolean {
  const keys = [match.home_team, match.away_team].map(canonicalTeamKey);
  const k1 = canonicalTeamKey(name1);
  const k2 = canonicalTeamKey(name2);
  return keys.includes(k1) && keys.includes(k2);
}

function matchDate(match: Match): Date | undefined {
  if (match.datetime) return match.datetime;
  if (match.date) return new Date(match.date);
  return undefined;
}

function inDateRange(match: Match, from?: string, to?: string): boolean {
  const dt = matchDate(match);
  if (!dt) return true;
  if (from) {
    const fromDate = new Date(from);
    if (dt < fromDate) return false;
  }
  if (to) {
    const toDate = new Date(to);
    if (dt > toDate) return false;
  }
  return true;
}

function filterMatches(matches: Match[], filters: MatchFilters): Match[] {
  const result = matches.filter((m) => {
    if (filters.team1 && filters.team2) {
      if (!bothTeams(filters.team1, filters.team2, m)) return false;
    } else if (filters.team) {
      if (!teamMatches(filters.team, m)) return false;
    }
    if (filters.homeTeam && canonicalTeamKey(m.home_team) !== canonicalTeamKey(filters.homeTeam)) return false;
    if (filters.awayTeam && canonicalTeamKey(m.away_team) !== canonicalTeamKey(filters.awayTeam)) return false;
    if (filters.competition && normalizeCompetition(m.competition) !== normalizeCompetition(filters.competition)) return false;
    if (filters.season && m.season !== filters.season) return false;
    if (filters.round && String(m.round) !== String(filters.round)) return false;
    if (filters.stage && String(m.stage).toLowerCase() !== String(filters.stage).toLowerCase()) return false;
    if (filters.from || filters.to) {
      if (!inDateRange(m, filters.from, filters.to)) return false;
    }
    return true;
  });
  const sorted = result.sort((a, b) => {
    const da = matchDate(a)?.getTime() ?? 0;
    const db = matchDate(b)?.getTime() ?? 0;
    return db - da;
  });
  if (filters.limit && filters.limit > 0) return sorted.slice(0, filters.limit);
  return sorted;
}

function createStats(): TeamStats {
  return {
    team: '',
    matches: 0,
    wins: 0,
    draws: 0,
    losses: 0,
    goalsFor: 0,
    goalsAgainst: 0,
  };
}

function addMatchToStats(stats: TeamStats, match: Match, side: 'home' | 'away') {
  stats.matches++;
  const gf = side === 'home' ? match.home_goal : match.away_goal;
  const ga = side === 'home' ? match.away_goal : match.home_goal;
  stats.goalsFor += gf;
  stats.goalsAgainst += ga;
  if (match.winner === side) stats.wins++;
  else if (match.winner === 'draw') stats.draws++;
  else stats.losses++;
}

function computeTeamStats(matches: Match[], team: string, filters: MatchFilters): TeamStats {
  const filtered = filterMatches(matches, { ...filters, team });
  const result = createStats();
  result.team = normalizeTeamName(team);
  const homeStats = createStats();
  homeStats.team = normalizeTeamName(team);
  const awayStats = createStats();
  awayStats.team = normalizeTeamName(team);
  for (const match of filtered) {
    if (canonicalTeamKey(match.home_team) === canonicalTeamKey(team)) {
      addMatchToStats(result, match, 'home');
      addMatchToStats(homeStats, match, 'home');
    } else {
      addMatchToStats(result, match, 'away');
      addMatchToStats(awayStats, match, 'away');
    }
  }
  result.homeMatches = homeStats;
  result.awayMatches = awayStats;
  return result;
}

function computeHeadToHead(matches: Match[], team1: string, team2: string, filters: MatchFilters) {
  const filtered = filterMatches(matches, { team1, team2, ...filters });
  let team1Wins = 0;
  let team2Wins = 0;
  let draws = 0;
  for (const match of filtered) {
    const homeKey = canonicalTeamKey(match.home_team);
    if (match.winner === 'draw') draws++;
    else if (match.winner === 'home' && homeKey === canonicalTeamKey(team1)) team1Wins++;
    else if (match.winner === 'home' && homeKey === canonicalTeamKey(team2)) team2Wins++;
    else if (match.winner === 'away' && canonicalTeamKey(match.away_team) === canonicalTeamKey(team1)) team1Wins++;
    else if (match.winner === 'away' && canonicalTeamKey(match.away_team) === canonicalTeamKey(team2)) team2Wins++;
  }
  return { matches: filtered, team1Wins, team2Wins, draws };
}

function computeCompetitionStandings(matches: Match[], competition: string, season: number): CompetitionStanding[] {
  const filtered = filterMatches(matches, { competition, season });
  const standings: Record<string, CompetitionStanding> = {};
  for (const match of filtered) {
    const home = normalizeTeamName(match.home_team);
    const away = normalizeTeamName(match.away_team);
    if (!home || !away) continue;
    if (!standings[home]) {
      standings[home] = {
        position: 0,
        team: home,
        points: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        goalsFor: 0,
        goalsAgainst: 0,
        goalDifference: 0,
      };
    }
    if (!standings[away]) {
      standings[away] = {
        position: 0,
        team: away,
        points: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        goalsFor: 0,
        goalsAgainst: 0,
        goalDifference: 0,
      };
    }
    standings[home].goalsFor += match.home_goal;
    standings[home].goalsAgainst += match.away_goal;
    standings[away].goalsFor += match.away_goal;
    standings[away].goalsAgainst += match.home_goal;
    if (match.winner === 'home') {
      standings[home].points += 3;
      standings[home].wins++;
      standings[away].losses++;
    } else if (match.winner === 'away') {
      standings[away].points += 3;
      standings[away].wins++;
      standings[home].losses++;
    } else {
      standings[home].points++;
      standings[away].points++;
      standings[home].draws++;
      standings[away].draws++;
    }
  }
  for (const s of Object.values(standings)) {
    s.goalDifference = s.goalsFor - s.goalsAgainst;
  }
  const sorted = Object.values(standings).sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    if (b.wins !== a.wins) return b.wins - a.wins;
    return b.goalDifference - a.goalDifference;
  });
  for (let i = 0; i < sorted.length; i++) {
    sorted[i].position = i + 1;
  }
  return sorted;
}

function searchPlayers(players: Player[], {
  name,
  nationality,
  club,
  position,
  minOverall,
  limit,
}: {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  limit?: number;
}): Player[] {
  const result = players.filter((p) => {
    if (name) {
      const pattern = new RegExp(escapeRegExp(name), 'i');
      if (!pattern.test(p.name)) return false;
    }
    if (nationality) {
      if (!p.nationality || !new RegExp(escapeRegExp(nationality), 'i').test(p.nationality)) return false;
    }
    if (club) {
      if (!p.club || canonicalTeamKey(p.club) !== canonicalTeamKey(club)) return false;
    }
    if (position) {
      if (!p.position || !p.position.toLowerCase().includes(position.toLowerCase())) return false;
    }
    if (minOverall !== undefined && (p.overall === undefined || p.overall < minOverall)) return false;
    return true;
  });
  const sorted = result.sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
  if (limit && limit > 0) return sorted.slice(0, limit);
  return sorted;
}

function computeStatsSummary(matches: Match[], filters: MatchFilters) {
  const filtered = filterMatches(matches, filters);
  const totalGoals = filtered.reduce((sum, m) => sum + m.home_goal + m.away_goal, 0);
  const homeWins = filtered.filter((m) => m.winner === 'home').length;
  const awayWins = filtered.filter((m) => m.winner === 'away').length;
  const draws = filtered.filter((m) => m.winner === 'draw').length;
  const biggestWins = filtered
    .map((m) => ({ match: m, diff: Math.abs(m.home_goal - m.away_goal) }))
    .filter((m) => m.diff > 0)
    .sort((a, b) => b.diff - a.diff)
    .slice(0, 10)
    .map((m) => m.match);
  return {
    totalMatches: filtered.length,
    totalGoals,
    averageGoalsPerMatch: filtered.length ? totalGoals / filtered.length : 0,
    homeWinRate: filtered.length ? homeWins / filtered.length : 0,
    awayWinRate: filtered.length ? awayWins / filtered.length : 0,
    drawRate: filtered.length ? draws / filtered.length : 0,
    homeWins,
    awayWins,
    draws,
    biggestWins,
  };
}

export function createQueryEngine(data: LoadedData) {
  return {
    data,
    findMatches: (filters: MatchFilters) => filterMatches(data.matches, filters),
    getTeamStats: (team: string, filters: MatchFilters = {}) => computeTeamStats(data.matches, team, filters),
    getHeadToHead: (team1: string, team2: string, filters: MatchFilters = {}) => computeHeadToHead(data.matches, team1, team2, filters),
    getStandings: (competition: string, season: number) => computeCompetitionStandings(data.matches, competition, season),
    searchPlayers: (params: Parameters<typeof searchPlayers>[1]) => searchPlayers(data.players, params),
    getStatsSummary: (filters: MatchFilters = {}) => computeStatsSummary(data.matches, filters),
  };
}

export type QueryEngine = ReturnType<typeof createQueryEngine>;
