// Type definitions for Brazilian Soccer MCP Server

export interface Match {
  datetime: string;
  homeTeam: string;
  awayTeam: string;
  homeGoal: number;
  awayGoal: number;
  season: number;
  competition: string;
  round?: string;
  stage?: string;
  homeTeamState?: string;
  awayTeamState?: string;
  venue?: string;
  homeCorner?: number;
  awayCorner?: number;
  homeAttack?: number;
  awayAttack?: number;
  homeShots?: number;
  awayShots?: number;
}

export interface Player {
  id: string;
  name: string;
  age: number;
  nationality: string;
  overall: number;
  potential: number;
  club: string;
  position: string;
  jerseyNumber?: number;
  height?: string;
  weight?: string;
}

export interface TeamStats {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  points: number;
}

export interface HeadToHead {
  team1: string;
  team2: string;
  team1Wins: number;
  team2Wins: number;
  draws: number;
  matches: Match[];
}

export interface CompetitionStanding {
  position: number;
  team: string;
  points: number;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
}

export interface BiggestWin {
  match: Match;
  goalDifference: number;
}

export interface Competition {
  name: string;
  season: number;
}
