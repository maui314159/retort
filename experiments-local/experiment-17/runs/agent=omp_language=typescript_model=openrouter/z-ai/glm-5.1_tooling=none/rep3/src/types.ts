/**
 * Brazilian Soccer MCP Server - Type Definitions
 *
 * Defines all shared types for the MCP server including match records,
 * player records, team statistics, competition standings, and query
 * parameters. Types are organized by data domain (matches, players,
 * statistics) to support the unified data access layer.
 */

// ── Match Types ──────────────────────────────────────────────────────

export type Competition =
  | "Brasileirão"
  | "Copa do Brasil"
  | "Libertadores"
  | "Historical Brasileirão"
  | "Other";

export interface MatchRecord {
  /** ISO date string (YYYY-MM-DD or YYYY-MM-DDTHH:mm:ss) */
  date: string;
  homeTeam: string;
  awayTeam: string;
  homeGoals: number;
  awayGoals: number;
  season: number;
  competition: Competition;
  round?: string;
  stage?: string;
  stadium?: string;
  /** Extended stats (BR-Football-Dataset only) */
  homeCorners?: number;
  awayCorners?: number;
  homeAttacks?: number;
  awayAttacks?: number;
  homeShots?: number;
  awayShots?: number;
  homeState?: string;
  awayState?: string;
}

// ── Player Types ─────────────────────────────────────────────────────

export interface PlayerRecord {
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
  headingAccuracy: number;
  shortPassing: number;
  dribbling: number;
  curve: number;
  fkAccuracy: number;
  longPassing: number;
  ballControl: number;
  acceleration: number;
  sprintSpeed: number;
  agility: number;
  reactions: number;
  balance: number;
  shotPower: number;
  stamina: number;
  strength: number;
  longShots: number;
  aggression: number;
  interceptions: number;
  positioning: number;
  vision: number;
  penalties: number;
  composure: number;
}

// ── Statistics Types ─────────────────────────────────────────────────

export interface TeamStats {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  winRate: string;
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

export interface HeadToHeadResult {
  teamA: string;
  teamB: string;
  matches: number;
  teamAWins: number;
  teamBWins: number;
  draws: number;
  teamAGoals: number;
  teamBGoals: number;
  recentMatches: MatchRecord[];
}

export interface AggregateStats {
  totalMatches: number;
  totalGoals: number;
  avgGoalsPerMatch: string;
  homeWins: number;
  awayWins: number;
  draws: number;
  homeWinRate: string;
  awayWinRate: string;
  biggestWins: { date: string; winner: string; loser: string; score: string; competition: string }[];
}

// ── Query Parameter Types ────────────────────────────────────────────

export interface MatchQuery {
  team?: string;
  opponent?: string;
  competition?: Competition;
  season?: number;
  startDate?: string;
  endDate?: string;
  limit?: number;
}

export interface PlayerQuery {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  maxOverall?: number;
  limit?: number;
}

export interface StandingsQuery {
  competition: Competition;
  season: number;
}

export interface StatsQuery {
  competition?: Competition;
  season?: number;
  team?: string;
}
