/**
 * Core domain models for the Brazilian Soccer MCP server.
 *
 * Matches are normalized from the six provided CSV files so that every
 * record shares the same shape regardless of its source. Players are
 * sourced from the FIFA player database.
 */

export interface Match {
  /** Stable identifier; synthetic when the source file does not provide one. */
  id: string;
  /** ISO date string (YYYY-MM-DD) in local Brazilian time. */
  date: string;
  /** Optional datetime string from the source file. */
  datetime?: string;
  /** Season / year of the competition. */
  season: number;
  /** Competition name, e.g. "Brasileirão", "Copa do Brasil", "Copa Libertadores". */
  competition: string;
  /** Round or matchday when available. */
  round?: string | number;
  /** Tournament stage when available (e.g. "group stage", "final"). */
  stage?: string;
  /** Canonical/normalized home team name. */
  homeTeam: string;
  /** Canonical/normalized away team name. */
  awayTeam: string;
  /** State abbreviation of the home team, when known. */
  homeTeamState?: string;
  /** State abbreviation of the away team, when known. */
  awayTeamState?: string;
  /** Goals scored by the home team. */
  homeGoal: number;
  /** Goals scored by the away team. */
  awayGoal: number;
  /** Stadium / arena name, when known. */
  stadium?: string;
  /** Extended match statistics from BR-Football-Dataset.csv. */
  homeCorner?: number;
  awayCorner?: number;
  homeAttack?: number;
  awayAttack?: number;
  homeShots?: number;
  awayShots?: number;
}

export interface Player {
  /** FIFA player identifier. */
  id: number;
  /** Player name. */
  name: string;
  /** Player age. */
  age: number;
  /** Nationality / country. */
  nationality: string;
  /** FIFA overall rating. */
  overall: number;
  /** FIFA potential rating. */
  potential: number;
  /** Current club at the time of the dataset. */
  club: string;
  /** Primary playing position. */
  position: string;
  /** Shirt number, when known. */
  jerseyNumber?: number;
  /** Height string, when known. */
  height?: string;
  /** Weight string, when known. */
  weight?: string;
}

export interface TeamRecord {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  points: number;
}

export interface HeadToHead {
  teamA: string;
  teamB: string;
  matches: Match[];
  teamAWins: number;
  teamBWins: number;
  draws: number;
}
