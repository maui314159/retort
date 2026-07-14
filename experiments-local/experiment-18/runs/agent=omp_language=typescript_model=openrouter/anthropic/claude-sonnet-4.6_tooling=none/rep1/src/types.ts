// Normalized match record shared across all CSV sources
export interface Match {
  date: string;          // ISO YYYY-MM-DD
  competition: Competition;
  season: number;
  round?: string;
  stage?: string;
  homeTeam: string;      // normalized (no state suffix)
  awayTeam: string;
  homeGoals: number;
  awayGoals: number;
  homeState?: string;
  awayState?: string;
  arena?: string;
  homeCorners?: number;
  awayCorners?: number;
  homeShots?: number;
  awayShots?: number;
}

export type Competition =
  | "Brasileirao"
  | "Copa do Brasil"
  | "Libertadores"
  | "Extended";

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
  // skill ratings
  crossing?: number;
  finishing?: number;
  dribbling?: number;
  shortPassing?: number;
  longPassing?: number;
  ballControl?: number;
  acceleration?: number;
  sprintSpeed?: number;
  stamina?: number;
  strength?: number;
  reactions?: number;
  composure?: number;
  gkDiving?: number;
  gkHandling?: number;
  gkKicking?: number;
  gkPositioning?: number;
  gkReflexes?: number;
}

export interface TeamRecord {
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
  matches: Match[];
  team1Wins: number;
  team2Wins: number;
  draws: number;
  team1Goals: number;
  team2Goals: number;
}
