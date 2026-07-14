/**
 * Brazilian Soccer MCP Server - Type Definitions
 *
 * Defines the core data types for match, player, and competition data
 * across all 6 CSV datasets. Each type mirrors the column structure
 * of its source file, with optional fields for columns that may be
 * missing or empty.
 */

// ─── Match Types ────────────────────────────────────────────────────

/** Brasileirão Serie A match record (Brasileirao_Matches.csv) */
export interface BrasileiraoMatch {
  datetime: string;
  homeTeam: string;
  homeTeamState: string;
  awayTeam: string;
  awayTeamState: string;
  homeGoal: number;
  awayGoal: number;
  season: number;
  round: number;
}

/** Copa do Brasil match record (Brazilian_Cup_Matches.csv) */
export interface CopaBrasilMatch {
  round: string;
  datetime: string;
  homeTeam: string;
  awayTeam: string;
  homeGoal: number;
  awayGoal: number;
  season: number;
}

/** Copa Libertadores match record (Libertadores_Matches.csv) */
export interface LibertadoresMatch {
  datetime: string;
  homeTeam: string;
  awayTeam: string;
  homeGoal: number;
  awayGoal: number;
  season: number;
  stage: string;
}

/** Extended match with statistics (BR-Football-Dataset.csv) */
export interface ExtendedMatch {
  tournament: string;
  home: string;
  away: string;
  homeGoal: number;
  awayGoal: number;
  homeCorner: number | null;
  awayCorner: number | null;
  homeAttack: number | null;
  awayAttack: number | null;
  homeShots: number | null;
  awayShots: number | null;
  time: string;
  date: string;
  htResult: string | null;
  atResult: string | null;
  totalCorners: number | null;
}

/** Historical Brasileirão match (novo_campeonato_brasileiro.csv) */
export interface HistoricalMatch {
  id: string;
  date: string;
  year: number;
  round: number;
  homeTeam: string;
  awayTeam: string;
  homeGoal: number;
  awayGoal: number;
  homeState: string;
  awayState: string;
  winner: string;
  arena: string;
}

// ─── Unified Match ──────────────────────────────────────────────────

/** Competition source identifiers */
export type Competition =
  | "Brasileirão"
  | "Copa do Brasil"
  | "Libertadores"
  | "Serie B"
  | "Copa Sudamericana"
  | "Other";

/** Normalized match record used across all queries */
export interface UnifiedMatch {
  date: string;          // ISO date string YYYY-MM-DD
  homeTeam: string;      // Normalized team name
  awayTeam: string;      // Normalized team name
  homeGoal: number;
  awayGoal: number;
  competition: Competition;
  season: number;
  round: string;         // Round number or stage name
  homeTeamState?: string;
  awayTeamState?: string;
  stage?: string;        // Tournament stage (Libertadores)
  arena?: string;
  // Extended stats (may be null)
  homeCorner?: number | null;
  awayCorner?: number | null;
  homeShots?: number | null;
  awayShots?: number | null;
}

// ─── Player Type ───────────────────────────────────────────────────

/** FIFA player record (fifa_data.csv) */
export interface Player {
  id: number;
  name: string;
  age: number;
  nationality: string;
  overall: number;
  potential: number;
  club: string;
  position: string;
  jerseyNumber: number | null;
  height: string;
  weight: string;
  crossing: number;
  finishing: number;
  dribbling: number;
  shortPassing: number;
  shotPower: number;
  stamina: number;
  strength: number;
  vision: number;
  composure: number;
}

// ─── Query Result Types ─────────────────────────────────────────────

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
}

export interface HeadToHead {
  team1: string;
  team2: string;
  team1Wins: number;
  team2Wins: number;
  draws: number;
  matches: UnifiedMatch[];
}

export interface AggregatedStats {
  totalMatches: number;
  totalGoals: number;
  averageGoalsPerMatch: number;
  homeWins: number;
  awayWins: number;
  draws: number;
  homeWinRate: number;
  awayWinRate: number;
}
