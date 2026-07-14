export interface MatchRow {
  date: string;
  homeTeam: string;
  awayTeam: string;
  homeTeamClean: string;
  awayTeamClean: string;
  homeGoals: number;
  awayGoals: number;
  season: string;
  competition: string;
  round?: string;
  stage?: string;
}

export interface PlayerRow {
  id: string;
  name: string;
  age: number;
  nationality: string;
  overall: number;
  potential: number;
  club: string;
  position: string;
}

export interface TeamStats {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  winRate: number;
}

export interface HeadToHead {
  team1: string;
  team2: string;
  matches: number;
  team1Wins: number;
  team2Wins: number;
  draws: number;
  recentMatches: MatchRow[];
}

export interface StandingRow {
  team: string;
  points: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
}
