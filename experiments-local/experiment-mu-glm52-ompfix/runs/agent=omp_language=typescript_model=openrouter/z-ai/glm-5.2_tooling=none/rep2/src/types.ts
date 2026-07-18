/**
 * Brazilian Soccer MCP Server — shared types
 * -------------------------------------------
 * Context block:
 *   This module defines the in-memory record shapes that every other module
 *   (loader, tools, tests) operates on. All match records are normalised to a
 *   single `Match` shape regardless of which CSV file they came from, so that
 *   cross-file queries (e.g. player + match data) can be expressed uniformly.
 *
 *   Normalisation rules (see normalizer.ts):
 *     - Team names are stripped of their state suffix, de-accented and mapped
 *       to a canonical key via a curated alias table.
 *     - Dates are parsed from the three formats present in the datasets
 *       (ISO "2023-09-24", Brazilian "29/03/2003", ISO+time "2012-05-19 18:30:00").
 *     - Goals that are missing/NA are represented as `null`.
 */

/** A single match, normalised across all five match datasets. */
export interface Match {
  /** Stable id combining source + original row index. */
  id: string;
  /** Originating dataset: brasileirao | copa_do_brasil | libertadores | br_football | historico. */
  source: MatchSource;
  /** Human competition label, e.g. "Brasileirão", "Copa do Brasil", "Copa Libertadores", "Serie B". */
  competition: string;
  /** Canonical home team key (normalised). */
  homeTeam: string;
  /** Display home team name (accented, no state suffix). */
  homeTeamDisplay: string;
  /** Canonical away team key. */
  awayTeam: string;
  /** Display away team name. */
  awayTeamDisplay: string;
  /** Home goals, or null if not available. */
  homeGoal: number | null;
  /** Away goals, or null if not available. */
  awayGoal: number | null;
  /** Season year, or null if unknown. */
  season: number | null;
  /** Match round / stage / rodada, or null. */
  round: string | null;
  /** Parsed JS Date (UTC midnight of the match day), or null if unparseable. */
  date: Date | null;
  /** Raw date string from the source file (for display). */
  rawDate: string;
  /** Optional stadium name (historical dataset only). */
  arena?: string | null;
  /** Extended stats (BR-Football dataset only). */
  stats?: MatchStats;
  /** Tournament stage (Libertadores only, e.g. "group stage", "final"). */
  stage?: string | null;
}

export type MatchSource =
  | "brasileirao"
  | "copa_do_brasil"
  | "libertadores"
  | "br_football"
  | "historico";

export interface MatchStats {
  homeCorner: number | null;
  awayCorner: number | null;
  homeAttack: number | null;
  awayAttack: number | null;
  homeShots: number | null;
  awayShots: number | null;
  homeHalf: number | null;
  awayHalf: number | null;
  totalCorners: number | null;
}

/** A FIFA player record (fifa_data.csv). */
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
  height: string | null;
  weight: string | null;
  /** A subset of skill ratings. */
  skills: PlayerSkills;
}

export interface PlayerSkills {
  crossing: number | null;
  finishing: number | null;
  dribbling: number | null;
  shortPassing: number | null;
  longPassing: number | null;
  shotPower: number | null;
  stamina: number | null;
  strength: number | null;
  interceptions: number | null;
  positioning: number | null;
  vision: number | null;
  composure: number | null;
}

/** Aggregated team statistics over a set of matches. */
export interface TeamStats {
  team: string;
  teamDisplay: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  /** Points using 3-for-a-win. */
  points: number;
  /** Only set when filtering to home/away; otherwise null. */
  homeAway?: "home" | "away" | "all";
}

/** A standings row. */
export interface StandingRow {
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

/** Head-to-head summary between two teams. */
export interface HeadToHead {
  teamA: string;
  teamB: string;
  matches: number;
  teamAWins: number;
  teamBWins: number;
  draws: number;
  teamAGoals: number;
  teamBGoals: number;
}
