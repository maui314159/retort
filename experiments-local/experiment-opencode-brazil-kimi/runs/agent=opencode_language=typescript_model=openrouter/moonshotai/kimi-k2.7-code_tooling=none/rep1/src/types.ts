/*
 * Brazilian Soccer MCP Server - Core data models
 *
 * This module defines the domain types shared across the loader, query engine,
 * and MCP server surface.
 */

export type CompetitionName =
  | 'Brasileirão'
  | 'Copa do Brasil'
  | 'Copa Libertadores'
  | string;

export interface Match {
  id?: string;
  datetime: Date;
  date: string; // ISO date part (YYYY-MM-DD)
  season: number;
  competition: CompetitionName;
  round?: string;
  stage?: string;
  homeTeam: string;
  homeTeamState?: string;
  awayTeam: string;
  awayTeamState?: string;
  homeGoal: number | null;
  awayGoal: number | null;
  stadium?: string;
  source: string;
}

export interface ExtendedMatchStats extends Match {
  homeCorner?: number | null;
  awayCorner?: number | null;
  homeAttack?: number | null;
  awayAttack?: number | null;
  homeShots?: number | null;
  awayShots?: number | null;
  halfTimeResult?: string;
  totalCorners?: number | null;
}

export interface Player {
  id?: string;
  name: string;
  age?: number;
  nationality: string;
  overall?: number;
  potential?: number;
  club?: string;
  position?: string;
  jerseyNumber?: string;
  height?: string;
  weight?: string;
  source: string;
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

export interface Standing extends TeamRecord {
  goalDifference: number;
  position?: number;
}

export interface HeadToHead {
  teamA: string;
  teamB: string;
  teamAWins: number;
  teamBWins: number;
  draws: number;
  teamAGoals: number;
  teamBGoals: number;
  matches: Match[];
}

export type SortDirection = 'asc' | 'desc';
