export interface Match {
  id: string;
  date: string; // ISO YYYY-MM-DD
  datetime?: string;
  season: number;
  competition: string;
  round?: string;
  stage?: string;
  homeTeam: string;
  awayTeam: string;
  homeTeamState?: string;
  awayTeamState?: string;
  homeGoal: number;
  awayGoal: number;
  stadium?: string;
  source: string;
  rawHome: string;
  rawAway: string;
}

export interface Player {
  id: number;
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
  goalDifference: number;
  homeMatches: number;
  awayMatches: number;
  homeWins: number;
  awayWins: number;
}

export interface StandingRecord {
  team: string;
  points: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  matches: number;
}
