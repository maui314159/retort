/**
 * Context
 * =======
 * Shared domain types for the Brazilian Soccer MCP server.
 *
 * The six source CSVs are normalized into two flat record shapes — `Match` and
 * `Player` — so every query path operates over one consistent schema regardless
 * of which file a row originated from. `canonicalHome`/`canonicalAway` carry the
 * suffix-stripped, diacritic-folded keys (see normalize.ts) used for matching;
 * `homeTeam`/`awayTeam` keep human-readable display names.
 */

import type { Competition } from './normalize.js';

/** A single match, normalized from any of the five match datasets. */
export interface Match {
  /** Canonical competition label. */
  competition: Competition;
  /** ISO date YYYY-MM-DD, or undefined when the source date was unparseable. */
  date?: string;
  /** Season year (e.g. 2019). undefined when not present in source. */
  season?: number;
  /** Round / stage label as a string (numeric round or e.g. "group stage"). */
  round?: string;
  /** Display name of the home team (accents preserved, suffix stripped). */
  homeTeam: string;
  /** Display name of the away team. */
  awayTeam: string;
  /** Canonical (matchable) key for the home team. */
  canonicalHome: string;
  /** Canonical (matchable) key for the away team. */
  canonicalAway: string;
  /** Goals scored by the home team. */
  homeGoals: number;
  /** Goals scored by the away team. */
  awayGoals: number;
  /** Source file identifier for provenance / dedupe. */
  source: string;
}

/** A FIFA player record, normalized from fifa_data.csv. */
export interface Player {
  id: number;
  name: string;
  age?: number;
  nationality: string;
  overall: number;
  potential: number;
  club: string;
  /** Canonical club key for matching. */
  canonicalClub: string;
  position?: string;
  jerseyNumber?: number;
  height?: string;
  weight?: string;
}

/** Win/draw/loss + goals aggregate for a team. */
export interface TeamRecord {
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
}

/** A standings row for a competition+season table. */
export interface StandingRow {
  team: string;
  points: number;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
}
