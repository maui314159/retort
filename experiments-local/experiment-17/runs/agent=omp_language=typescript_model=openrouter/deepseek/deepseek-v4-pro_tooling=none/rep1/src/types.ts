/**
 * Brazilian Soccer MCP Server - Data Types
 *
 * Normalized data models for all 6 CSV sources.
 * All team names are stored stripped of state suffix and lowercased
 * for consistent matching; display names preserve the original.
 */

// ── Match ────────────────────────────────────────────────────────────

export interface NormalizedMatch {
  date: string;            // ISO date string YYYY-MM-DD
  homeTeam: string;        // normalized (lowercase, no suffix)
  homeTeamDisplay: string; // original display name
  awayTeam: string;
  awayTeamDisplay: string;
  homeGoal: number;
  awayGoal: number;
  season: number;
  competition: string;     // standardized: "brasileirao" | "copa_do_brasil" | "libertadores"
  round: string;           // round label
  stage: string;           // tournament stage (libertadores)
  // Extended stats (optional, from BR-Football-Dataset)
  homeCorner?: number;
  awayCorner?: number;
  homeShots?: number;
  awayShots?: number;
  homeAttack?: number;
  awayAttack?: number;
  stadium?: string;
}

// ── Player ───────────────────────────────────────────────────────────

export interface NormalizedPlayer {
  id: number;
  name: string;
  age: number;
  nationality: string;
  overall: number;
  potential: number;
  club: string;            // normalized club name
  clubDisplay: string;     // original club name
  position: string;
  jerseyNumber: number;
  height: number;          // cm
  weight: number;          // kg
  preferredFoot: string;
  skillMoves: number;
  weakFoot: number;
  workRate: string;
  // Selected skill ratings
  pace: number;
  shooting: number;
  passing: number;
  dribbling: number;
  defending: number;
  physical: number;
}

// ── Team Stats ───────────────────────────────────────────────────────

export interface TeamStats {
  team: string;
  teamDisplay: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  points: number;          // 3 per win, 1 per draw
}

export interface TeamRecord extends TeamStats {
  homeStats: TeamStats;
  awayStats: TeamStats;
  competitions: Record<string, TeamStats>;
}

// ── Standings ────────────────────────────────────────────────────────

export interface StandingEntry {
  position: number;
  team: string;
  teamDisplay: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  points: number;
}

// ── Head-to-Head ─────────────────────────────────────────────────────

export interface HeadToHead {
  team1: string;
  team1Display: string;
  team2: string;
  team2Display: string;
  totalMatches: number;
  team1Wins: number;
  team2Wins: number;
  draws: number;
  team1Goals: number;
  team2Goals: number;
  matches: NormalizedMatch[];
}

// ── Query Parameters ─────────────────────────────────────────────────

export interface MatchQuery {
  team?: string;
  opponent?: string;
  competition?: string;
  season?: number;
  dateFrom?: string;
  dateTo?: string;
  limit?: number;
}

export interface PlayerQuery {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minRating?: number;
  maxRating?: number;
  limit?: number;
  sortBy?: string;
}
