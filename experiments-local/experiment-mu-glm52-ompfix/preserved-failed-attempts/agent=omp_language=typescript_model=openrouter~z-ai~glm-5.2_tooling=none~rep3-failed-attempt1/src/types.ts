/**
 * brazilian-soccer-mcp — Core domain types.
 *
 * Context: This file defines the unified in-memory model used across the whole
 * MCP server. The six Kaggle CSV datasets use heterogeneous schemas and naming
 * conventions, so every source record is projected into one of the normalized
 * types below (`Match`, `Player`) before being indexed and queried. The MCP
 * tools and the query engine only ever touch these normalized shapes.
 */

/** Normalized competition identifiers used across the server. */
export const Competitions = {
  BRASILEIRAO_SERIE_A: "Brasileirão Serie A",
  SERIE_B: "Serie B",
  SERIE_C: "Serie C",
  COPA_DO_BRASIL: "Copa do Brasil",
  LIBERTADORES: "Copa Libertadores",
  HISTORICAL_BRASILEIRAO: "Brasileirão (2003-2019)",
} as const;

export type Competition = (typeof Competitions)[keyof typeof Competitions];

/**
 * A single soccer match, normalized from any of the five match CSV sources.
 *
 * - `homeTeam`/`awayTeam` carry the cleaned *display* name (state/country
 *   suffixes stripped, accents preserved, whitespace collapsed).
 * - `homeTeamKey`/`awayTeamKey` carry a case- and accent-folded key used for
 *   fast, tolerant lookups across files with inconsistent spelling.
 * - `homeGoals`/`awayGoals` are `null` only if the source row had no score
 *   (none of the provided files actually do, but the type is defensive).
 */
export interface Match {
  id: string;
  competition: string;
  /** Tournament name exactly as recorded by the source (e.g. "Serie A"). */
  tournamentRaw: string;
  season: number | null;
  /** Parsed UTC date, or null when the source value is blank/NA. */
  date: Date | null;
  dateRaw: string;
  homeTeam: string;
  homeTeamRaw: string;
  homeTeamKey: string;
  awayTeam: string;
  awayTeamRaw: string;
  awayTeamKey: string;
  homeGoals: number | null;
  awayGoals: number | null;
  round: string | null;
  /** Libertadores tournament stage (group stage, final, ...). */
  stage: string | null;
  /** Stadium name from the historical dataset, when available. */
  venue: string | null;
  /** Extended statistics (only present for BR-Football-Dataset rows). */
  homeCorners: number | null;
  awayCorners: number | null;
  homeShots: number | null;
  awayShots: number | null;
  homeAttacks: number | null;
  awayAttacks: number | null;
  halfTimeResult: string | null;
  totalCorners: number | null;
}

/** A FIFA player row, projected to the fields the server exposes. */
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
  preferredFoot: string | null;
  internationalReputation: number | null;
  value: string | null;
  wage: string | null;
  /** Selected skill ratings (base value, with any "+N" bonus stripped). */
  skills: Record<string, number>;
}

/** Result classification for one team in one match. */
export type MatchOutcome = "win" | "draw" | "loss";

/** Aggregated record for a team over a set of matches. */
export interface TeamRecord {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  points: number;
  winRate: number;
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

/** One row of a calculated standings table. */
export interface StandingsRow {
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
  isChampion: boolean;
}

/** A scoreable result used by "biggest wins" queries. */
export interface BiggestWin {
  date: string;
  competition: string;
  season: number | null;
  winner: string;
  loser: string;
  winnerGoals: number;
  loserGoals: number;
  margin: number;
}
