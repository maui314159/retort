/**
 * Core data types for the Brazilian Soccer MCP server.
 * All matches are normalized to this common structure regardless of source CSV.
 */

export interface Match {
  /** ISO YYYY-MM-DD */
  date: string;
  /** Original team name from CSV (may include state suffix like "Palmeiras-SP") */
  homeTeam: string;
  /** Original team name from CSV */
  awayTeam: string;
  homeGoals: number;
  awayGoals: number;
  /** 'brasileirao' | 'copa_do_brasil' | 'libertadores' | 'historico' | tournament name from extended dataset */
  competition: string;
  /** 0 if unknown */
  season: number;
  round?: string;
  stage?: string;
  arena?: string;
  /** Extended stats from BR-Football-Dataset */
  homeCorners?: number;
  awayCorners?: number;
  homeShots?: number;
  awayShots?: number;
  homeAttacks?: number;
  awayAttacks?: number;
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
}

export interface DataStore {
  matches: Match[];
  players: Player[];
}

export interface TeamRecord {
  team: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  points: number;
}

export interface HeadToHeadResult {
  matches: Match[];
  team1Wins: number;
  team2Wins: number;
  draws: number;
  team1Goals: number;
  team2Goals: number;
}
