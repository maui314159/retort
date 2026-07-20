/**
 * Core domain types for the Brazilian Soccer knowledge graph.
 */

/** Unified, normalized view of a single match from any of the CSV sources. */
export interface Match {
  /** Stable id: `<source>:<rowIndex>` */
  id: string;
  /** CSV file this match came from. */
  source: string;
  /** Normalized competition label (e.g. "Brasileirão Série A", "Copa do Brasil"). */
  competition: string;
  /** Raw competition/tournament label as found in the source. */
  competitionRaw: string;
  /** ISO date (YYYY-MM-DD) or null when unparseable. */
  date: string | null;
  /** Season year when known. */
  season: number | null;
  /** Round / stage label when known. */
  round: string | null;
  /** Tournament stage (Libertadores) when known. */
  stage: string | null;
  /** Home team display name (as written in the source). */
  homeTeam: string;
  /** Away team display name (as written in the source). */
  awayTeam: string;
  /** Normalized lookup keys for the teams. */
  homeKey: string;
  awayKey: string;
  homeGoals: number | null;
  awayGoals: number | null;
}

/** Player row from the FIFA dataset (subset of columns). */
export interface Player {
  id: number;
  name: string;
  age: number | null;
  nationality: string;
  overall: number | null;
  potential: number | null;
  club: string;
  position: string;
  jerseyNumber: number | null;
}

/** Aggregate record for a team over a set of matches. */
export interface TeamRecord {
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
}

/** One row of a computed league table. */
export interface StandingRow {
  team: string;
  teamKey: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  points: number;
}

/** Filters accepted by the match search. */
export interface MatchFilter {
  /** Single team (home or away). */
  team?: string;
  /** Both teams must be involved (any order). */
  teamA?: string;
  teamB?: string;
  competition?: string;
  season?: number;
  dateFrom?: string;
  dateTo?: string;
  limit?: number;
}

/** Filters accepted by the player search. */
export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  limit?: number;
}

/** Raw loaded datasets before graph indexing. */
export interface LoadedData {
  matches: Match[];
  players: Player[];
}
