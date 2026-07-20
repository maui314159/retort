/**
 * Core domain types for the Brazilian Soccer MCP server.
 */

/** Canonical competitions exposed by the server. */
export type Competition =
  | 'Brasileirão Série A'
  | 'Brasileirão Série B'
  | 'Brasileirão Série C'
  | 'Copa do Brasil'
  | 'Copa Libertadores';

/** Which CSV file a match originated from. */
export type SourceDataset =
  | 'brasileirao' // Brasileirao_Matches.csv
  | 'cup' // Brazilian_Cup_Matches.csv
  | 'libertadores' // Libertadores_Matches.csv
  | 'brfootball' // BR-Football-Dataset.csv
  | 'historico'; // novo_campeonato_brasileiro.csv

/**
 * Canonical team identity: simplified base name + optional Brazilian state.
 * Two clubs that share a base name but play in different states
 * (e.g. "Botafogo-RJ" vs "Botafogo PB") are distinct identities.
 */
export interface TeamIdentity {
  /** Unique key, e.g. "flamengo#rj" or "river plate" (no state). */
  key: string;
  /** Simplified (lower-case, accent-free) base name, e.g. "flamengo". */
  base: string;
  /** Brazilian state code (e.g. "RJ") when known. */
  state?: string;
  /** Preferred human-readable name, e.g. "Flamengo". */
  displayName: string;
  /** All raw name variants seen in the datasets. */
  variants: Set<string>;
  /** Number of matches in the store (filled after load). */
  matchCount: number;
}

export interface Match {
  /** Stable dedupe key: "yyyy-mm-dd|homeKey|awayKey" (+ source suffix when date unknown). */
  id: string;
  /** ISO date "yyyy-mm-dd", or undefined when the source has no parseable date. */
  date?: string;
  /** Kick-off time "HH:MM" when present in the source. */
  time?: string;
  competition: Competition;
  season?: number;
  /** Round / stage label, e.g. "Round 22", "Final", "Group Stage". */
  round?: string;
  homeTeam: TeamIdentity;
  awayTeam: TeamIdentity;
  /** Goals; undefined when the match was not played (source had NA/-). */
  homeGoals?: number;
  awayGoals?: number;
  /** False when goals are missing (scheduled/cancelled games). */
  played: boolean;
  stadium?: string;
  source: SourceDataset;
  /** Extended stats (only present for BR-Football-Dataset rows). */
  stats?: {
    homeCorners?: number;
    awayCorners?: number;
    homeShots?: number;
    awayShots?: number;
    homeAttacks?: number;
    awayAttacks?: number;
    halfTimeResult?: string;
  };
}

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
  preferredFoot?: string;
  value?: string;
  wage?: string;
  skills: Record<string, number>;
}

/** Fully loaded in-memory dataset with lookup indexes. */
export interface DatasetStore {
  matches: Match[];
  /** Deduped view used for statistics. */
  dedupedMatches: Match[];
  players: Player[];
  teams: Map<string, TeamIdentity>;
  /** competition -> set of seasons present */
  competitions: Map<Competition, Set<number>>;
  loadedAt: Date;
}

export interface TeamRecord {
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
}

export interface StandingRow extends TeamRecord {
  position: number;
  team: TeamIdentity;
  points: number;
  goalDifference: number;
}

export interface HeadToHead {
  teamA: TeamIdentity;
  teamB: TeamIdentity;
  matches: Match[];
  winsA: number;
  winsB: number;
  draws: number;
  goalsA: number;
  goalsB: number;
}
