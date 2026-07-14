/**
 * Shared domain types for the Brazilian Soccer MCP server.
 */

export interface Match {
  /** Source dataset identifier */
  source: string;
  /** Competition name, normalized where possible */
  competition: string;
  /** Season/year */
  season: number | null;
  /** Match date (when available) */
  date: Date | null;
  /** Home team display name */
  homeTeam: string;
  /** Normalized home team key */
  homeKey: string;
  /** Away team display name */
  awayTeam: string;
  /** Normalized away team key */
  awayKey: string;
  /** Goals scored by home team */
  homeGoals: number | null;
  /** Goals scored by away team */
  awayGoals: number | null;
  /** Round / stage / group label */
  round: string | null;
  /** Stadium, when available */
  stadium?: string | null;
}

export interface Player {
  /** Source player ID */
  id: number | null;
  /** Player name */
  name: string;
  /** Age */
  age: number | null;
  /** Nationality */
  nationality: string | null;
  /** FIFA overall rating */
  overall: number | null;
  /** FIFA potential rating */
  potential: number | null;
  /** Club name */
  club: string | null;
  /** Normalized club key */
  clubKey: string | null;
  /** Playing position */
  position: string | null;
  /** Jersey number */
  jerseyNumber: number | null;
}

export interface TeamRecord {
  team: string;
  key: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  points: number;
}

export interface HeadToHead {
  matches: Match[];
  teamA: string;
  teamB: string;
  winsA: number;
  winsB: number;
  draws: number;
}

export interface DataStore {
  matches: Match[];
  players: Player[];
}
