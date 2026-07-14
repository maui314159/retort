/**
 * Type definitions for the Brazilian Soccer MCP Server.
 * Covers match, player, and competition data models with
 * normalization support across multiple dataset formats.
 */

/** Normalized match record from any source CSV */
export interface Match {
  date: string;           // ISO date string YYYY-MM-DD
  homeTeam: string;       // Normalized team name (no state suffix)
  awayTeam: string;       // Normalized team name (no state suffix)
  homeGoals: number;
  awayGoals: number;
  competition: string;    // "Brasileirão", "Copa do Brasil", "Libertadores", etc.
  season: number;
  round: string;          // Round number or stage name
  homeState?: string;     // State abbreviation if available
  awayState?: string;
  stadium?: string;
  source: string;         // Which CSV file this came from
}

/** FIFA player record */
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
}

/** Team statistics computed from match data */
export interface TeamStats {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  homeWins: number;
  homeDraws: number;
  homeLosses: number;
  homeGoalsFor: number;
  homeGoalsAgainst: number;
  awayWins: number;
  awayDraws: number;
  awayLosses: number;
  awayGoalsFor: number;
  awayGoalsAgainst: number;
}

/** Head-to-head record between two teams */
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
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  points: number;
}

/** Aggregate statistics */
export interface AggregateStats {
  totalMatches: number;
  totalGoals: number;
  averageGoalsPerMatch: number;
  homeWins: number;
  awayWins: number;
  draws: number;
  homeWinRate: number;
  awayWinRate: number;
  drawRate: number;
}

/** All loaded data */
export interface SoccerData {
  matches: Match[];
  players: Player[];
}

/** Team name normalization map */
export type NameMap = Map<string, string>;
