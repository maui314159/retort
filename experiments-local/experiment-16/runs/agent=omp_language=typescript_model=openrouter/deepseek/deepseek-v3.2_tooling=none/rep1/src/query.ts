/**
 * Brazilian Soccer MCP Server - Query Utilities
 * 
 * Provides query functions for matches, players, teams, and competitions
 * with filtering, aggregation, and statistical analysis.
 */

import { Match, Player, TeamStats, CompetitionStandings, HeadToHead, QueryFilters } from './types';
import { normalizeTeamName } from './csv-loader';
import { format, isValid } from 'date-fns';

/**
 * Filters matches based on query criteria
 */
export function filterMatches(matches: Match[], filters: QueryFilters): Match[] {
  let filtered = [...matches];
  
  if (filters.team) {
    const normalizedTeam = normalizeTeamName(filters.team);
    filtered = filtered.filter(match => 
      normalizeTeamName(match.homeTeam) === normalizedTeam ||
      normalizeTeamName(match.awayTeam) === normalizedTeam
    );
  }
  
  if (filters.teams && filters.teams.length === 2) {
    const team1 = normalizeTeamName(filters.teams[0]);
    const team2 = normalizeTeamName(filters.teams[1]);
    filtered = filtered.filter(match => {
      const home = normalizeTeamName(match.homeTeam);
      const away = normalizeTeamName(match.awayTeam);
      return (home === team1 && away === team2) || (home === team2 && away === team1);
    });
  }
  
  if (filters.homeTeam) {
    const normalizedHome = normalizeTeamName(filters.homeTeam);
    filtered = filtered.filter(match => 
      normalizeTeamName(match.homeTeam) === normalizedHome
    );
  }
  
  if (filters.awayTeam) {
    const normalizedAway = normalizeTeamName(filters.awayTeam);
    filtered = filtered.filter(match => 
      normalizeTeamName(match.awayTeam) === normalizedAway
    );
  }
  
  if (filters.dateFrom && isValid(filters.dateFrom)) {
    filtered = filtered.filter(match => 
      isValid(match.date) && match.date >= filters.dateFrom!
    );
  }
  
  if (filters.dateTo && isValid(filters.dateTo)) {
    filtered = filtered.filter(match => 
      isValid(match.date) && match.date <= filters.dateTo!
    );
  }
  
  if (filters.season !== undefined) {
    filtered = filtered.filter(match => match.season === filters.season);
  }
  
  if (filters.competition) {
    filtered = filtered.filter(match => 
      match.competition?.toLowerCase().includes(filters.competition!.toLowerCase())
    );
  }
  
  if (filters.limit !== undefined && filters.limit > 0) {
    filtered = filtered.slice(0, filters.limit);
  }
  
  // Sort by date descending (most recent first)
  return filtered.sort((a, b) => b.date.getTime() - a.date.getTime());
}

/**
 * Calculates team statistics from matches
 */
export function calculateTeamStats(
  matches: Match[], 
  teamName: string,
  filters?: Pick<QueryFilters, 'season' | 'competition'>
): TeamStats {
  const normalizedTeam = normalizeTeamName(teamName);
  let teamMatches = matches.filter(match => 
    normalizeTeamName(match.homeTeam) === normalizedTeam ||
    normalizeTeamName(match.awayTeam) === normalizedTeam
  );
  
  if (filters?.season !== undefined) {
    teamMatches = teamMatches.filter(match => match.season === filters.season);
  }
  
  if (filters?.competition) {
    teamMatches = teamMatches.filter(match => 
      match.competition?.toLowerCase().includes(filters.competition!.toLowerCase())
    );
  }
  
  let wins = 0;
  let draws = 0;
  let losses = 0;
  let goalsFor = 0;
  let goalsAgainst = 0;
  
  for (const match of teamMatches) {
    const isHome = normalizeTeamName(match.homeTeam) === normalizedTeam;
    const teamGoals = isHome ? match.homeGoals : match.awayGoals;
    const opponentGoals = isHome ? match.awayGoals : match.homeGoals;
    
    goalsFor += teamGoals;
    goalsAgainst += opponentGoals;
    
    if (teamGoals > opponentGoals) {
      wins++;
    } else if (teamGoals < opponentGoals) {
      losses++;
    } else {
      draws++;
    }
  }
  
  const totalMatches = teamMatches.length;
  const winRate = totalMatches > 0 ? (wins / totalMatches) * 100 : 0;
  
  // Calculate home/away stats
  const homeMatches = teamMatches.filter(match => 
    normalizeTeamName(match.homeTeam) === normalizedTeam
  );
  const awayMatches = teamMatches.filter(match => 
    normalizeTeamName(match.awayTeam) === normalizedTeam
  );
  
  const homeStats = homeMatches.length > 0 ? 
    calculateTeamStats(homeMatches, teamName) : undefined;
  const awayStats = awayMatches.length > 0 ? 
    calculateTeamStats(awayMatches, teamName) : undefined;
  
  return {
    team: teamName,
    matches: totalMatches,
    wins,
    draws,
    losses,
    goalsFor,
    goalsAgainst,
    goalDifference: goalsFor - goalsAgainst,
    winRate,
    homeRecord: homeStats,
    awayRecord: awayStats
  };
}

/**
 * Calculates head-to-head statistics between two teams
 */
export function calculateHeadToHead(
  matches: Match[], 
  team1: string, 
  team2: string
): HeadToHead {
  const normalizedTeam1 = normalizeTeamName(team1);
  const normalizedTeam2 = normalizeTeamName(team2);
  
  const h2hMatches = matches.filter(match => {
    const home = normalizeTeamName(match.homeTeam);
    const away = normalizeTeamName(match.awayTeam);
    return (home === normalizedTeam1 && away === normalizedTeam2) ||
           (home === normalizedTeam2 && away === normalizedTeam1);
  });
  
  let team1Wins = 0;
  let team2Wins = 0;
  let draws = 0;
  let team1Goals = 0;
  let team2Goals = 0;
  
  for (const match of h2hMatches) {
    const isTeam1Home = normalizeTeamName(match.homeTeam) === normalizedTeam1;
    const team1Score = isTeam1Home ? match.homeGoals : match.awayGoals;
    const team2Score = isTeam1Home ? match.awayGoals : match.homeGoals;
    
    team1Goals += team1Score;
    team2Goals += team2Score;
    
    if (team1Score > team2Score) {
      team1Wins++;
    } else if (team1Score < team2Score) {
      team2Wins++;
    } else {
      draws++;
    }
  }
  
  return {
    team1: team1,
    team2: team2,
    matches: h2hMatches.sort((a, b) => b.date.getTime() - a.date.getTime()),
    team1Wins,
    team2Wins,
    draws,
    team1Goals,
    team2Goals
  };
}

/**
 * Filters players based on criteria
 */
export function filterPlayers(
  players: Player[], 
  filters: {
    name?: string;
    nationality?: string;
    club?: string;
    minRating?: number;
    maxRating?: number;
    position?: string;
    limit?: number;
  }
): Player[] {
  let filtered = [...players];
  
  if (filters.name) {
    const searchName = filters.name.toLowerCase();
    filtered = filtered.filter(player => 
      player.name.toLowerCase().includes(searchName)
    );
  }
  
  if (filters.nationality) {
    filtered = filtered.filter(player => 
      player.nationality.toLowerCase().includes(filters.nationality!.toLowerCase())
    );
  }
  
  if (filters.club) {
    filtered = filtered.filter(player => 
      player.club.toLowerCase().includes(filters.club!.toLowerCase())
    );
  }
  
  if (filters.minRating !== undefined) {
    filtered = filtered.filter(player => player.overall >= filters.minRating!);
  }
  
  if (filters.maxRating !== undefined) {
    filtered = filtered.filter(player => player.overall <= filters.maxRating!);
  }
  
  if (filters.position) {
    const position = filters.position.toLowerCase();
    filtered = filtered.filter(player => 
      player.position.toLowerCase().includes(position)
    );
  }
  
  if (filters.limit !== undefined && filters.limit > 0) {
    filtered = filtered.slice(0, filters.limit);
  }
  
  // Sort by rating descending
  return filtered.sort((a, b) => b.overall - a.overall);
}

/**
 * Calculates competition standings from matches
 */
export function calculateStandings(
  matches: Match[],
  competition: string,
  season?: number
): CompetitionStandings {
  // Filter matches by competition and season
  let compMatches = matches.filter(match => 
    match.competition?.toLowerCase().includes(competition.toLowerCase())
  );
  
  if (season !== undefined) {
    compMatches = compMatches.filter(match => match.season === season);
  }
  
  // Initialize team records
  const teamRecords: Record<string, {
    matches: number;
    wins: number;
    draws: number;
    losses: number;
    goalsFor: number;
    goalsAgainst: number;
  }> = {};
  
  // Process each match
  for (const match of compMatches) {
    const homeTeam = normalizeTeamName(match.homeTeam);
    const awayTeam = normalizeTeamName(match.awayTeam);
    
    // Initialize if not present
    if (!teamRecords[homeTeam]) {
      teamRecords[homeTeam] = { matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0 };
    }
    if (!teamRecords[awayTeam]) {
      teamRecords[awayTeam] = { matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0 };
    }
    
    // Update home team stats
    teamRecords[homeTeam].matches++;
    teamRecords[homeTeam].goalsFor += match.homeGoals;
    teamRecords[homeTeam].goalsAgainst += match.awayGoals;
    
    // Update away team stats
    teamRecords[awayTeam].matches++;
    teamRecords[awayTeam].goalsFor += match.awayGoals;
    teamRecords[awayTeam].goalsAgainst += match.homeGoals;
    
    // Determine result
    if (match.homeGoals > match.awayGoals) {
      teamRecords[homeTeam].wins++;
      teamRecords[awayTeam].losses++;
    } else if (match.homeGoals < match.awayGoals) {
      teamRecords[homeTeam].losses++;
      teamRecords[awayTeam].wins++;
    } else {
      teamRecords[homeTeam].draws++;
      teamRecords[awayTeam].draws++;
    }
  }
  
  // Convert to array and calculate points (3 for win, 1 for draw)
  const standings = Object.entries(teamRecords).map(([team, record]) => {
    const points = (record.wins * 3) + record.draws;
    const goalDifference = record.goalsFor - record.goalsAgainst;
    
    return {
      team,
      points,
      matches: record.matches,
      wins: record.wins,
      draws: record.draws,
      losses: record.losses,
      goalsFor: record.goalsFor,
      goalsAgainst: record.goalsAgainst,
      goalDifference
    };
  });
  
  // Sort by points, then goal difference, then goals for
  standings.sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    if (b.goalDifference !== a.goalDifference) return b.goalDifference - a.goalDifference;
    return b.goalsFor - a.goalsFor;
  });
  
  return {
    competition,
    season: season || compMatches[0]?.season || new Date().getFullYear(),
    teams: standings
  };
}

/**
 * Calculates overall statistics across all matches
 */
export function calculateOverallStats(matches: Match[]): {
  totalMatches: number;
  averageGoalsPerMatch: number;
  homeWinRate: number;
  drawRate: number;
  awayWinRate: number;
  biggestHomeWin?: Match;
  biggestAwayWin?: Match;
} {
  if (matches.length === 0) {
    return {
      totalMatches: 0,
      averageGoalsPerMatch: 0,
      homeWinRate: 0,
      drawRate: 0,
      awayWinRate: 0
    };
  }
  
  let totalGoals = 0;
  let homeWins = 0;
  let draws = 0;
  let awayWins = 0;
  let biggestHomeWin: Match | undefined;
  let biggestAwayWin: Match | undefined;
  let biggestHomeMargin = -1;
  let biggestAwayMargin = -1;
  
  for (const match of matches) {
    totalGoals += match.homeGoals + match.awayGoals;
    
    if (match.homeGoals > match.awayGoals) {
      homeWins++;
      const margin = match.homeGoals - match.awayGoals;
      if (margin > biggestHomeMargin) {
        biggestHomeMargin = margin;
        biggestHomeWin = match;
      }
    } else if (match.homeGoals < match.awayGoals) {
      awayWins++;
      const margin = match.awayGoals - match.homeGoals;
      if (margin > biggestAwayMargin) {
        biggestAwayMargin = margin;
        biggestAwayWin = match;
      }
    } else {
      draws++;
    }
  }
  
  const totalMatches = matches.length;
  const averageGoalsPerMatch = totalGoals / totalMatches;
  const homeWinRate = (homeWins / totalMatches) * 100;
  const drawRate = (draws / totalMatches) * 100;
  const awayWinRate = (awayWins / totalMatches) * 100;
  
  return {
    totalMatches,
    averageGoalsPerMatch,
    homeWinRate,
    drawRate,
    awayWinRate,
    biggestHomeWin,
    biggestAwayWin
  };
}

/**
 * Formats match for display
 */
export function formatMatch(match: Match): string {
  const dateStr = isValid(match.date) ? format(match.date, 'yyyy-MM-dd') : 'Unknown date';
  const roundInfo = match.round ? ` (Round ${match.round})` : '';
  const competitionInfo = match.competition ? ` (${match.competition})` : '';
  
  return `${dateStr}: ${match.homeTeam} ${match.homeGoals}-${match.awayGoals} ${match.awayTeam}${roundInfo}${competitionInfo}`;
}

/**
 * Formats player for display
 */
export function formatPlayer(player: Player): string {
  return `${player.name} - Overall: ${player.overall}, Position: ${player.position}, Club: ${player.club}, Nationality: ${player.nationality}`;
}

/**
 * Formats team statistics for display
 */
export function formatTeamStats(stats: TeamStats): string {
  return `${stats.team}: ${stats.matches} matches, ${stats.wins}W ${stats.draws}D ${stats.losses}L, GF: ${stats.goalsFor}, GA: ${stats.goalsAgainst}, GD: ${stats.goalDifference}, Win rate: ${stats.winRate.toFixed(1)}%`;
}

export { QueryFilters } from './types';