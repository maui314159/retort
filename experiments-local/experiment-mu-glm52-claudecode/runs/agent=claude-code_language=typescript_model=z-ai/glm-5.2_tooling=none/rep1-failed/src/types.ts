/**
 * Brazilian Soccer MCP Server — shared type definitions
 * =====================================================
 * Context block:
 *   This module defines the canonical, in-memory record types that the query
 *   engine operates on. All six Kaggle CSV files are normalized into one of two
 *   record shapes: `MatchRecord` (one per match, drawn from the five match
 *   datasets) or `PlayerRecord` (one per player, drawn from the FIFA dataset).
 *
 *   The design deliberately keeps a *normalized* team key (`homeKey`/`awayKey`)
 *   alongside a human-readable display name so that the same team can be
 *   matched across files that use different naming conventions (e.g.
 *   "Palmeiras-SP", "Palmeiras", "São Paulo FC"). See `src/normalize.ts`.
 */

/** A single match, normalized across all five match CSV files. */
export interface MatchRecord {
  /** ISO date string (YYYY-MM-DD) when known; raw text fallback otherwise. */
  dateStr: string;
  /** Parsed date, or null when unparseable. */
  date: Date | null;
  /** Display name of the home team (state suffix removed, accents kept). */
  home: string;
  /** Display name of the away team. */
  away: string;
  /** Normalized lookup key for the home team. */
  homeKey: string;
  /** Normalized lookup key for the away team. */
  awayKey: string;
  /** Optional 2-letter state of the home team (e.g. "SP"). */
  homeState?: string;
  /** Optional 2-letter state of the away team. */
  awayState?: string;
  /** Goals scored by the home team, or null when missing. */
  homeGoal: number | null;
  /** Goals scored by the away team, or null when missing. */
  awayGoal: number | null;
  /** Season year, or null when missing (e.g. Libertadores "NA"). */
  season: number | null;
  /** Canonical competition label (see COMPETITIONS in normalize.ts). */
  competition: string;
  /** Source file identifier. */
  source: string;
  /** Round number/label when present. */
  round?: string;
  /** Tournament stage (Libertadores). */
  stage?: string;
  /** Stadium name (historical Brasileirão). */
  arena?: string;
  /** Winner token from the historical file ("Mandante"|"Visitante"|"Empate"). */
  winner?: string;

  // Extended statistics (BR-Football-Dataset only).
  homeCorner?: number | null;
  awayCorner?: number | null;
  homeShots?: number | null;
  awayShots?: number | null;
  homeAttack?: number | null;
  awayAttack?: number | null;
  htResult?: string;
  atResult?: string;
  totalCorners?: number | null;
}

/** A single FIFA player row. */
export interface PlayerRecord {
  id: string;
  name: string;
  age: number | null;
  nationality: string;
  overall: number | null;
  potential: number | null;
  club: string;
  position: string;
  jerseyNumber: string;
  height: string;
  weight: string;
  preferredFoot: string;
  /** Raw row kept for attribute drill-downs (Crossing, Finishing, ...). */
  raw: Record<string, string>;
}

/** Win/draw/loss tally plus goals for/against. */
export interface TeamTally {
  team: string;
  teamKey: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  /** Points using 3-for-win, 1-for-draw. */
  points: number;
}

/** A queryable team reference resolved from user input. */
export interface TeamRef {
  /** Normalized name key (accent-stripped, lowercased). */
  nameKey: string;
  /** Optional 2-letter state, when the user supplied one. */
  state?: string;
  /** Original user-supplied text, for display. */
  raw: string;
}
