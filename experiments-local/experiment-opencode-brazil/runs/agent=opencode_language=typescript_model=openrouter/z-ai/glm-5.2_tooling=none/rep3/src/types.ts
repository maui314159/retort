/**
 * Brazilian Soccer MCP Server - Domain Types
 * ------------------------------------------
 * Context: This file defines the canonical domain model used across the
 * Brazilian Soccer MCP server. The server ingests six Kaggle CSV datasets
 * (Brasileirao, Copa do Brasil, Libertadores, BR-Football extended stats,
 * historical Brasileirao 2003-2019, and FIFA player database) and normalizes
 * them into the types below so that the query layer and MCP tools can treat
 * all competitions uniformly.
 *
 * Design goals:
 *  - One canonical `Match` shape covers every competition we ingest.
 *  - `Player` exposes the small subset of FIFA columns we actually serve.
 *  - `TeamStats` / `HeadToHead` / `Standing` are pre-computed aggregates.
 */

/** A normalized soccer match from any of the source datasets. */
export interface Match {
  /** ISO date (YYYY-MM-DD). Time portion is dropped for cross-dataset consistency. */
  date: string;
  /** Raw home team string as it appeared in the source CSV (may include state suffix). */
  homeTeamRaw: string;
  /** Raw away team string as it appeared in the source CSV. */
  awayTeamRaw: string;
  /** Normalized home team key (see normalizeTeamName). */
  homeTeam: string;
  /** Normalized away team key. */
  awayTeam: string;
  /** Home team state/UF (e.g. "SP") when known, otherwise null. */
  homeState: string | null;
  /** Away team state/UF when known, otherwise null. */
  awayState: string | null;
  /** Goals scored by the home team. */
  homeGoal: number;
  /** Goals scored by the away team. */
  awayGoal: number;
  /** Season year, e.g. 2023. */
  season: number;
  /** Competition slug: "brasileirao" | "copa-do-brasil" | "libertadores" | "brasileirao-historico" | "ext-stats". */
  competition: Competition;
  /** Human-readable competition name. */
  competitionLabel: string;
  /** Round/stage label from the source (round number, cup round, Libertadores stage, etc.). */
  round: string | null;
  /** Stadium name when known (only the historical dataset provides this), otherwise null. */
  stadium: string | null;
  /** Winner: "home" | "away" | "draw". */
  winner: "home" | "away" | "draw";
  /** Optional extended statistics (only present for matches from BR-Football-Dataset). */
  stats?: MatchStats;
}

/** Extended per-match statistics from BR-Football-Dataset.csv. */
export interface MatchStats {
  homeCorners: number;
  awayCorners: number;
  homeAttacks: number;
  awayAttacks: number;
  homeShots: number;
  awayShots: number;
  totalCorners: number;
  htResult: string | null;
  atResult: string | null;
  tournament: string;
}

/** Competitions recognized by the server. */
export type Competition =
  | "brasileirao"
  | "copa-do-brasil"
  | "libertadores"
  | "brasileirao-historico"
  | "ext-stats";

/** A subset of the FIFA player database row. */
export interface Player {
  id: number;
  name: string;
  age: number;
  nationality: string;
  overall: number;
  potential: number;
  club: string;
  position: string;
  jerseyNumber: number | null;
  height: string | null;
  weight: string | null;
  /** Preferred foot, e.g. "Left" / "Right". */
  preferredFoot: string | null;
}

/** Aggregated team statistics over a set of matches. */
export interface TeamStats {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  points: number;
  /** Per-venue breakdown. */
  home: VenueStats;
  away: VenueStats;
}

export interface VenueStats {
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
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
  /** Most recent match first. */
  recent: Match[];
}

/** A single row in a computed league table. */
export interface Standing {
  position: number;
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

/** Filter options accepted by the match query tool. */
export interface MatchQuery {
  team?: string;
  opponent?: string;
  competition?: Competition | "any";
  season?: number;
  startDate?: string;
  endDate?: string;
  limit?: number;
}

/** Filter options accepted by the player query tool. */
export interface PlayerQuery {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  limit?: number;
  sortBy?: "overall" | "potential" | "age" | "name";
  descending?: boolean;
}
