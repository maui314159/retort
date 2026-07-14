export interface Match {
  date: string;
  home: string;
  away: string;
  homeGoals: number | null;
  awayGoals: number | null;
  season: number | null;
  competition: string;
  round: string | null;
  stage: string | null;
  sourceFile: string;
  originalDate: string;
}

export interface Player {
  id: string;
  name: string;
  age: number | null;
  nationality: string | null;
  overall: number | null;
  potential: number | null;
  club: string | null;
  position: string | null;
  jerseyNumber: string | null;
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
  homeRecord: {
    matches: number;
    wins: number;
    draws: number;
    losses: number;
    goalsFor: number;
    goalsAgainst: number;
  };
  awayRecord: {
    matches: number;
    wins: number;
    draws: number;
    losses: number;
    goalsFor: number;
    goalsAgainst: number;
  };
}

export interface StandingRow {
  rank: number;
  team: string;
  points: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
}
