/**
 * Context
 * -------
 * Shared domain model for the Brazilian Soccer MCP server. Every match across
 * the five match datasets is projected into a single `Match` shape so query
 * code never branches on source file. Players come from the FIFA dataset and
 * are projected into `Player`. Keeping one unified shape per entity is what
 * makes cross-file queries ("player + match", "all competitions for a team")
 * trivial downstream.
 */

/** Canonical competition identifiers. */
export type Competition =
  | "Brasileirão"
  | "Copa do Brasil"
  | "Libertadores"
  | "Serie B"
  | "Serie C";

/** A single match, normalized from any source dataset. */
export interface Match {
  /** Source dataset filename (provenance). */
  source: string;
  competition: Competition;
  /** Normalized ISO date (YYYY-MM-DD) when parseable, else null. */
  date: string | null;
  /** Original date string from the dataset. */
  dateRaw: string;
  season: number | null;
  /** Round / stage label when available ("22", "group stage", "final"). */
  round: string | null;
  /** Display home-team name (as stored). */
  homeTeam: string;
  /** Display away-team name (as stored). */
  awayTeam: string;
  /** Canonical match key for the home team. */
  homeKey: string;
  /** Canonical match key for the away team. */
  awayKey: string;
  homeGoal: number | null;
  awayGoal: number | null;
  /** Stadium when present (novo_campeonato_brasileiro only). */
  arena: string | null;
}

/** A FIFA player record, projected to the fields we expose. */
export interface Player {
  id: string;
  name: string;
  age: number | null;
  nationality: string;
  overall: number | null;
  potential: number | null;
  club: string;
  /** Canonical key for the club, for joining with match teams. */
  clubKey: string;
  position: string;
  jerseyNumber: string;
  height: string;
  weight: string;
}

/** Outcome of a single match from one team's perspective. */
export type Outcome = "win" | "draw" | "loss";

/** Aggregated win/draw/loss + goals record. */
export interface TeamRecord {
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
}
