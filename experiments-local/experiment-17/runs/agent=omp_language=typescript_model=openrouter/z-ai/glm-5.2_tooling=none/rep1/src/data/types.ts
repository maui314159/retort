/**
 * Brazilian Soccer MCP Server — Core domain types.
 *
 * Context block
 * -------------
 * This file defines the unified in-memory model that the MCP server exposes
 * as a knowledge graph over the six provided Kaggle CSV datasets:
 *
 *   1. Brasileirao_Matches.csv      -> Brasileirão Série A (2012-2023)
 *   2. Brazilian_Cup_Matches.csv    -> Copa do Brasil
 *   3. Libertadores_Matches.csv     -> Copa Libertadores
 *   4. BR-Football-Dataset.csv      -> Extended stats across many tournaments
 *   5. novo_campeonato_brasileiro.csv -> Historical Brasileirão (2003-2019)
 *   6. fifa_data.csv                -> FIFA player database (~18k players)
 *
 * Each CSV uses different column names and naming conventions, so the loader
 * normalizes every row into the `MatchRecord` / `Player` shapes defined here.
 * Team names are canonicalized (see normalize.ts) so that "Palmeiras-SP",
 * "Palmeiras - SP" and "Palmeiras" all resolve to the same graph node.
 */

/** Logical competition a match belongs to. */
export type Competition =
  | "Brasileirão"
  | "Copa do Brasil"
  | "Copa Libertadores"
  | "Historical Brasileirão"
  | "Other";

/**
 * Unified match record. `home*`/`away*` goals and optional advanced stats
 * (corners/shots/attacks) are present only when the source file provides them.
 */
export interface MatchRecord {
  /** Canonical match id (stable, derived from source file + row). */
  id: string;
  /** Source CSV file. */
  source: string;
  /** Logical competition. */
  competition: Competition;
  /** Original tournament string (when available, e.g. from BR-Football). */
  tournament?: string;
  /** Parsed kickoff date (UTC midnight for date-only rows), or null if unparseable. */
  date: Date | null;
  /** Raw date string as it appeared in the source. */
  rawDate: string;
  /** Canonical home team display name. */
  homeTeam: string;
  /** Canonical away team display name. */
  awayTeam: string;
  /** Home team state (UF) when known. */
  homeState?: string;
  /** Away team state (UF) when known. */
  awayState?: string;
  /** Goals scored by home team, or null if missing. */
  homeGoal: number | null;
  /** Goals scored by away team, or null if missing. */
  awayGoal: number | null;
  /** Season year, or null if missing. */
  season: number | null;
  /** Round/stage label as in source (e.g. "22", "Final", "group stage"). */
  round?: string;
  /** Tournament stage (Libertadores). */
  stage?: string;
  /** Stadium name when known. */
  arena?: string;
  /** Half-time home score when known. */
  htHome?: number | null;
  /** Half-time away score when known. */
  htAway?: number | null;
  /** Advanced stat: home corner kicks. */
  homeCorner?: number | null;
  /** Advanced stat: away corner kicks. */
  awayCorner?: number | null;
  /** Advanced stat: home shots. */
  homeShots?: number | null;
  /** Advanced stat: away shots. */
  awayShots?: number | null;
  /** Advanced stat: home attacks. */
  homeAttack?: number | null;
  /** Advanced stat: away attacks. */
  awayAttack?: number | null;
}

/** FIFA player record (subset of columns relevant for querying). */
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
  preferredFoot?: string;
  height?: string;
  weight?: string;
  value?: string;
  wage?: string;
  /** Selected skill ratings, parsed to base integers (e.g. "88+2" -> 88). */
  skills: Record<string, number>;
}

/** Match outcome for a given team perspective. */
export type Outcome = "win" | "draw" | "loss";

/** Aggregated team record over a set of matches. */
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

/** A standing row in a computed competition table. */
export interface StandingRow {
  team: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  points: number;
}
