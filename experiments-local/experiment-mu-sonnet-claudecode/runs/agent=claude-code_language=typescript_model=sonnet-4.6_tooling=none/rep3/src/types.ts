export interface Match {
  datetime: Date | null;
  homeTeam: string;
  awayTeam: string;
  homeGoals: number;
  awayGoals: number;
  season: number;
  competition: "brasileirao" | "copa_do_brasil" | "libertadores" | "extended" | "historical";
  round?: string;
  stage?: string;
  homeState?: string;
  awayState?: string;
  tournament?: string;
  arena?: string;
  winner?: string;
  homeCorners?: number;
  awayCorners?: number;
  homeAttacks?: number;
  awayAttacks?: number;
  homeShots?: number;
  awayShots?: number;
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
  value?: string;
  wage?: string;
  preferredFoot?: string;
  internationalReputation?: number;
  weakFoot?: number;
  skillMoves?: number;
  workRate?: string;
  crossing?: number;
  finishing?: number;
  dribbling?: number;
  passing?: number;
  shooting?: number;
  pace?: number;
  defending?: number;
  physical?: number;
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
