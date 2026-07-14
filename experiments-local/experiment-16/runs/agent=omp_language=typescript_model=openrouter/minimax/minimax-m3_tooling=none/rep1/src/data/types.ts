/**
 * Domain types shared by the loader, normalizer, query layer and MCP tools.
 *
 * Every match coming out of the loader is normalized to the {@link Match}
 * shape regardless of the originating CSV, so downstream code never has to
 * branch on competition/source.
 */

export type Competition =
  | 'brasileirao'
  | 'copa_do_brasil'
  | 'libertadores'
  | 'brasileirao_historical'
  | 'br_football';

export interface Match {
  /** Stable id derived from competition + season + round + teams + date. */
  id: string;
  competition: Competition;
  season: number;
  round: string;
  /** ISO-8601 yyyy-mm-dd (no time component). */
  date: string;
  /** 24h hh:mm:ss or empty. */
  time: string;
  homeTeam: string;
  awayTeam: string;
  homeGoal: number | null;
  awayGoal: number | null;
  /** Optional extra context per source. */
  homeState?: string;
  awayState?: string;
  stage?: string;
  stadium?: string;
  winner?: 'home' | 'away' | 'draw';
  homeCorners?: number | null;
  awayCorners?: number | null;
  homeShots?: number | null;
  awayShots?: number | null;
  homeAttacks?: number | null;
  awayAttacks?: number | null;
  halfTimeHome?: number | null;
  halfTimeAway?: number | null;
}

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
  value: string;
  wage: string;
}

export interface DatasetSnapshot {
  matches: Match[];
  players: Player[];
  /** Map from canonical team name to list of raw variants seen. */
  teamAliases: Map<string, string[]>;
  /** All canonical team names. */
  teams: string[];
}
