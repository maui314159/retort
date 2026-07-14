/**
 * Core domain types for the Brazilian Soccer MCP server.
 *
 * These types describe a unified view over the six heterogeneous CSV datasets
 * (Brasileirao, Copa do Brasil, Libertadores, extended stats, historical
 * Brasileirao 2003-2019, and the FIFA player database). Each dataset has its
 * own column naming/encoding conventions; the loader normalizes them into the
 * shapes below so the query engine and MCP tools can work against a single,
 * consistent model.
 */

/** Identifier of the competition a match belongs to. */
export type Competition =
  | 'Brasileirao'
  | 'Copa do Brasil'
  | 'Libertadores'
  | 'Historical Brasileirao'
  | 'BR-Football';

/** A single match, normalized across all source files. */
export interface Match {
  /** Source competition identifier. */
  competition: Competition;
  /** Raw tournament/stage label from the source file (e.g. "Serie A", "group stage"). */
  stage?: string;
  /** ISO-8601 date string (YYYY-MM-DD), or null when unparseable. */
  date: string | null;
  /** Original raw date string from the source file. */
  rawDate: string;
  /** Home team name, normalized (state suffix removed, trimmed, accented). */
  homeTeam: string;
  /** Away team name, normalized. */
  awayTeam: string;
  /** Home team state/UF abbreviation if known (e.g. "SP", "RJ"). */
  homeState?: string;
  awayState?: string;
  /** Goals scored by the home team. */
  homeGoal: number | null;
  /** Goals scored by the away team. */
  awayGoal: number | null;
  /** Season year (e.g. 2023). */
  season?: number;
  /** Round number, when available. */
  round?: string | number;
  /** Stadium name, when available. */
  arena?: string;
  /** Extended stats present only in BR-Football-Dataset.csv. */
  stats?: MatchStats;
}

/** Extended match statistics from BR-Football-Dataset.csv. */
export interface MatchStats {
  homeCorner?: number;
  awayCorner?: number;
  homeAttack?: number;
  awayAttack?: number;
  homeShots?: number;
  awayShots?: number;
  totalCorners?: number;
  htResult?: string;
  atResult?: string;
  /** Kick-off time string. */
  time?: string;
}

/** A FIFA player record. */
export interface Player {
  id: number;
  name: string;
  age?: number;
  nationality?: string;
  overall?: number;
  potential?: number;
  club?: string;
  position?: string;
  jerseyNumber?: number;
  height?: string;
  weight?: string;
  /** Preferred foot. */
  preferredFoot?: string;
  /** Selected skill ratings. */
  skills?: PlayerSkills;
}

export interface PlayerSkills {
  crossing?: number;
  finishing?: number;
  dribbling?: number;
  shortPassing?: number;
  longPassing?: number;
  ballControl?: number;
  shotPower?: number;
  stamina?: number;
  strength?: number;
  vision?: number;
  penalties?: number;
  standingTackle?: number;
  slidingTackle?: number;
}

/** Aggregated team record for a set of matches. */
export interface TeamRecord {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  /** Points (3 per win, 1 per draw). */
  points: number;
}

/** Head-to-head comparison between two teams. */
export interface HeadToHead {
  teamA: string;
  teamB: string;
  matches: Match[];
  teamAWins: number;
  teamBWins: number;
  draws: number;
}

/** Filter criteria for match queries. */
export interface MatchFilter {
  team?: string;
  opponent?: string;
  homeTeam?: string;
  awayTeam?: string;
  competition?: Competition | Competition[];
  season?: number;
  fromDate?: string;
  toDate?: string;
  limit?: number;
}

/** The loaded dataset, exposed to the query engine and MCP tools. */
export interface Dataset {
  matches: Match[];
  players: Player[];
}
