export interface Match {
  id: string;
  datetime?: Date;
  date?: string;
  time?: string;
  season: number;
  competition: string;
  round?: string;
  stage?: string;
  home_team: string;
  home_team_state?: string;
  away_team: string;
  away_team_state?: string;
  home_goal: number;
  away_goal: number;
  winner?: 'home' | 'away' | 'draw';
  stadium?: string;
  source: string;
}

export interface Player {
  id: number;
  name: string;
  age?: number;
  nationality?: string;
  overall?: number;
  potential?: number;
  club?: string;
  position?: string;
  jerseyNumber?: string;
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
  homeMatches?: TeamStats;
  awayMatches?: TeamStats;
}

export interface CompetitionStanding {
  position: number;
  team: string;
  points: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
}
