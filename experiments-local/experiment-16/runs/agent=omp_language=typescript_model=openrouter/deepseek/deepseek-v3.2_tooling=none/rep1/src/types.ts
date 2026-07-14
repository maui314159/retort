/**
 * Brazilian Soccer MCP Server - Type Definitions
 * 
 * Defines data models for Brazilian soccer datasets including matches, players,
 * and competitions. Handles team name normalization and date format variations.
 */

export interface Match {
  // Common fields across datasets
  date: Date;
  homeTeam: string;
  awayTeam: string;
  homeGoals: number;
  awayGoals: number;
  season: number;
  
  // Dataset-specific fields
  competition?: string;
  round?: number | string;
  stage?: string;
  stadium?: string;
  winner?: 'home' | 'away' | 'draw';
  
  // Extended statistics (from BR-Football-Dataset.csv)
  homeCorners?: number;
  awayCorners?: number;
  homeAttacks?: number;
  awayAttacks?: number;
  homeShots?: number;
  awayShots?: number;
  totalCorners?: number;
  
  // Original data for reference
  source: string;
  originalData: Record<string, unknown>;
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
  preferredFoot?: string;
  value?: string;
  wage?: string;
  originalData: Record<string, unknown>;
  // Skill ratings
  crossing?: number;
  finishing?: number;
  headingAccuracy?: number;
  shortPassing?: number;
  dribbling?: number;
  shotPower?: number;
  stamina?: number;
  strength?: number;
  aggression?: number;
  composure?: number;
  
  source: string;
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
  winRate: number;
  
  // Competition-specific
  competition?: string;
  season?: number;
  homeRecord?: TeamStats;
  awayRecord?: TeamStats;
}

export interface CompetitionStandings {
  competition: string;
  season: number;
  teams: {
    team: string;
    points: number;
    matches: number;
    wins: number;
    draws: number;
    losses: number;
    goalsFor: number;
    goalsAgainst: number;
    goalDifference: number;
  }[];
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

export interface QueryFilters {
  team?: string;
  teams?: string[];
  dateFrom?: Date;
  dateTo?: Date;
  season?: number;
  competition?: string;
  homeTeam?: string;
  awayTeam?: string;
  limit?: number;
}

export interface TeamNormalizationRule {
  pattern: RegExp;
  normalized: string;
  aliases: string[];
}

export type DatasetType = 
  | 'brasileirao' 
  | 'copa-do-brasil' 
  | 'libertadores' 
  | 'extended-stats' 
  | 'historical' 
  | 'fifa';