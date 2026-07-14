/**
 * brazilian-soccer-mcp / src/types.ts
 *
 * Shared domain types for the Brazilian Soccer MCP server.
 *
 * Context block:
 * This MCP server exposes Brazilian soccer datasets (Brasileirão, Copa do
 * Brasil, Libertadores, an extended stats dataset, historical Brasileirão
 * 2003-2019, and a FIFA player database) as queryable records. All match
 * records are normalized into a single `Match` shape regardless of source
 * file so that cross-file queries (e.g. "all Palmeiras matches across every
 * competition") work uniformly. Player records are normalized into `Player`.
 */

/** A normalized match record derived from any of the match CSV files. */
export interface Match {
  /** Stable id: `<source>:<lineNumber>`. */
  id: string;
  /** Source file basename. */
  source: string;
  /** Normalized competition name, e.g. "Brasileirão", "Copa do Brasil", "Libertadores". */
  competition: string;
  /** Season year (4-digit). */
  season: number | null;
  /** Parsed date (UTC midnight when only a date was given), or null if unparseable. */
  date: Date | null;
  /** Original date string as found in the source file. */
  dateRaw: string;
  /** Normalized home team display name (state suffixes / country markers stripped). */
  homeTeam: string;
  /** Normalized away team display name. */
  awayTeam: string;
  /** Canonical matching key for the home team. */
  homeTeamKey: string;
  /** Canonical matching key for the away team. */
  awayTeamKey: string;
  /** Home team goals, or null if not recorded. */
  homeGoals: number | null;
  /** Away team goals, or null if not recorded. */
  awayGoals: number | null;
  /** Round label (Brasileirão round number, Copa do Brasil round, etc.). */
  round: string | null;
  /** Tournament stage (Libertadores group/knockout, etc.). */
  stage: string | null;
  /** Stadium / arena name when available. */
  venue: string | null;
  /** Half-time home result label from the extended stats dataset, e.g. "WON"/"DRAW"/"LOST". */
  htHomeResult: string | null;
  // Extended statistics (BR-Football-Dataset only).
  homeCorners: number | null;
  awayCorners: number | null;
  homeShots: number | null;
  awayShots: number | null;
  homeAttacks: number | null;
  awayAttacks: number | null;
}

/** A normalized player record derived from the FIFA player CSV. */
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
  height: string;
  weight: string;
  preferredFoot: string;
  /** Canonical matching key for the club. */
  clubKey: string;
  /** Canonical matching key for the nationality (lowercased). */
  nationalityKey: string;
  // Selected skill ratings (null when blank).
  crossing: number | null;
  finishing: number | null;
  dribbling: number | null;
  shortPassing: number | null;
  longShots: number | null;
  shotPower: number | null;
  stamina: number | null;
  aggression: number | null;
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
  winRate: number;
}

/** Summary of Brazilian players at a single Brazilian club. */
export interface ClubSummary {
  club: string;
  count: number;
  avgOverall: number;
}

/** Head-to-head summary between two teams. */
export interface HeadToHead {
  teamA: string;
  teamB: string;
  matches: number;
  aWins: number;
  bWins: number;
  draws: number;
}

/** A single row in a computed competition standings table. */
export interface StandingRow {
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

/** Aggregate statistics over a set of matches. */
export interface AggregateStats {
  matches: number;
  totalGoals: number;
  averageGoalsPerMatch: number;
  homeWins: number;
  awayWins: number;
  draws: number;
  homeWinRate: number;
  awayWinRate: number;
  drawRate: number;
}
