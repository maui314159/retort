/**
 * Context
 * -------
 * Shared domain types for the Brazilian Soccer MCP server.
 *
 * Six heterogeneous CSV files are projected onto two unified shapes:
 *   - `Match`  : one game (any competition / source), with optional extended
 *                statistics where the source provides them.
 *   - `Player` : one FIFA player row, with the subset of attributes the spec
 *                exercises (rating, club, position, nationality, physicals).
 *
 * Team names are kept both raw (for display) and pre-parsed (for matching) so
 * query code never re-parses on the hot path.
 */

import type { ParsedDate, ParsedTeam } from "./normalize.js";

/** Canonical competition label assigned at load time. */
export type Competition =
  | "Brasileirão Série A"
  | "Brasileirão Série B"
  | "Brasileirão Série C"
  | "Copa do Brasil"
  | "Copa Libertadores";

/** Which source file a match came from (for provenance / debugging). */
export type SourceFile =
  | "Brasileirao_Matches.csv"
  | "Brazilian_Cup_Matches.csv"
  | "Libertadores_Matches.csv"
  | "BR-Football-Dataset.csv"
  | "novo_campeonato_brasileiro.csv";

/** Optional per-match extended statistics (only BR-Football-Dataset.csv). */
export interface MatchStats {
  readonly homeCorners?: number;
  readonly awayCorners?: number;
  readonly totalCorners?: number;
  readonly homeShots?: number;
  readonly awayShots?: number;
  readonly homeAttacks?: number;
  readonly awayAttacks?: number;
  readonly htHomeGoals?: number;
  readonly htAwayGoals?: number;
}

export interface Match {
  readonly source: SourceFile;
  readonly competition: Competition;
  readonly season: number;
  readonly date?: ParsedDate;
  /** Round number/name where the source records it. */
  readonly round?: string;
  /** Libertadores tournament stage ("group stage", "round of 16", ...). */
  readonly stage?: string;
  readonly stadium?: string;

  readonly homeTeamRaw: string;
  readonly awayTeamRaw: string;
  readonly home: ParsedTeam;
  readonly away: ParsedTeam;
  readonly homeGoals: number;
  readonly awayGoals: number;

  /** Mutable so a later richer source can attach stats to a deduped match. */
  stats?: MatchStats;
}

export interface Player {
  readonly id: number;
  readonly name: string;
  readonly age?: number;
  readonly nationality: string;
  readonly overall?: number;
  readonly potential?: number;
  readonly club: string;
  readonly position: string;
  readonly jerseyNumber?: number;
  readonly height?: string;
  readonly weight?: string;
  readonly preferredFoot?: string;
}

/** Result of a single match from one team's perspective. */
export type Outcome = "win" | "draw" | "loss";

export interface TeamRecord {
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
}
