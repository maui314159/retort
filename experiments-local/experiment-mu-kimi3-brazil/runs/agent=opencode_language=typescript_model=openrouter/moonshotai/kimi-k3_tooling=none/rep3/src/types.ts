/**
 * Shared domain types for the Brazilian Soccer knowledge graph.
 */

/** Canonical competition labels used across all data sources. */
export const COMPETITIONS = [
  "Brasileirão Série A",
  "Brasileirão Série B",
  "Brasileirão Série C",
  "Copa do Brasil",
  "Copa Libertadores",
] as const;

export type CompetitionLabel = (typeof COMPETITIONS)[number];

/** A normalized reference to a team (club). */
export interface TeamRef {
  /** Canonical slug key, e.g. "flamengo-rj", "sao-paulo-sp", "boca-juniors". */
  key: string;
  /** Human-friendly display name, e.g. "Flamengo". */
  name: string;
  /** Raw name as found in the source CSV. */
  raw: string;
}

/** Optional extended statistics (only present in the BR-Football-Dataset source). */
export interface MatchStats {
  homeCorners?: number;
  awayCorners?: number;
  homeShots?: number;
  awayShots?: number;
  homeAttacks?: number;
  awayAttacks?: number;
  totalCorners?: number;
}

/** A single match, deduplicated across sources. */
export interface Match {
  /** Stable id: `${date}|${homeKey}|${awayKey}` */
  id: string;
  /** ISO date yyyy-mm-dd (empty string when unknown). */
  date: string;
  /** Season year (null when unknown). */
  season: number | null;
  competition: CompetitionLabel;
  /** Round identifier (numeric string for league/cup, null otherwise). */
  round: string | null;
  /** Tournament stage (Libertadores: "group stage", "final", ...). */
  stage: string | null;
  homeTeam: TeamRef;
  awayTeam: TeamRef;
  /** Goals; null when the match was not played / score unavailable. */
  homeGoals: number | null;
  awayGoals: number | null;
  /** Stadium/arena name when known. */
  arena: string | null;
  /** Source file keys that contributed to this record. */
  sources: string[];
  stats?: MatchStats;
}

/** A player from the FIFA dataset. */
export interface Player {
  id: number;
  name: string;
  age: number | null;
  nationality: string;
  overall: number | null;
  potential: number | null;
  club: string | null;
  /** Canonical team key of the club when it resolves to a known team. */
  clubKey: string | null;
  position: string | null;
  jerseyNumber: number | null;
  height: string | null;
  weight: string | null;
}

/** Result of a win/draw/loss record aggregation. */
export interface TeamRecord {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  winRate: number;
}

/** One row of a calculated league standings table. */
export interface StandingRow extends TeamRecord {
  rank: number;
  points: number;
  note?: string;
}
