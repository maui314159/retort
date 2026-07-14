/**
 * Brazilian Soccer MCP Server - Type Definitions
 *
 * Defines unified types for match and player data across all CSV sources.
 * Each match record is normalized to a common shape regardless of origin file.
 * Player records map FIFA data columns to a consistent interface.
 */

/** Normalized match record from any CSV source */
export interface Match {
  date: string;           // ISO date string YYYY-MM-DD
  homeTeam: string;       // Normalized team name (no state suffix)
  awayTeam: string;       // Normalized team name (no state suffix)
  homeGoals: number;
  awayGoals: number;
  season: number;
  competition: Competition;
  round?: string;         // Round number or cup round name
  stage?: string;         // Tournament stage (Libertadores)
  stadium?: string;       // Arena name (historical Brasileirão)
  homeState?: string;     // State abbreviation
  awayState?: string;     // State abbreviation
  // Extended stats (BR-Football-Dataset only)
  homeCorners?: number;
  awayCorners?: number;
  homeAttacks?: number;
  awayAttacks?: number;
  homeShots?: number;
  awayShots?: number;
}

/** Player record from FIFA data */
export interface Player {
  id: number;
  name: string;
  age: number;
  nationality: string;
  overall: number;
  potential: number;
  club: string;
  position: string;
  jerseyNumber: number;
  height: string;
  weight: string;
  preferredFoot: string;
  crossing: number;
  finishing: number;
  dribbling: number;
  shortPassing: number;
  longPassing: number;
  ballControl: number;
  acceleration: number;
  sprintSpeed: number;
  stamina: number;
  strength: number;
  shotPower: number;
  vision: number;
}

export type Competition =
  | "Brasileirão"
  | "Copa do Brasil"
  | "Copa Libertadores"
  | "Serie A"
  | "Serie B"
  | "Copa Sudamericana"
  | string;

/** Team win/draw/loss record */
export interface TeamRecord {
  team: string;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  matches: number;
  points: number;
}

/** Head-to-head comparison */
export interface HeadToHead {
  team1: string;
  team2: string;
  team1Wins: number;
  team2Wins: number;
  draws: number;
  matches: Match[];
}

/** Competition standings entry */
export interface StandingEntry {
  position: number;
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
