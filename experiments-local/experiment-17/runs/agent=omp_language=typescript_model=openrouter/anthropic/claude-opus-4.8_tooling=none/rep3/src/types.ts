/**
 * Context
 * -------
 * Shared domain types for the Brazilian Soccer MCP server. Every CSV row from
 * the six Kaggle datasets is mapped into one of two unified shapes — `Match`
 * (any competition fixture) or `Player` (FIFA database entry) — so the query
 * engine can operate over a single in-memory model regardless of source file.
 *
 * Goal differences are stored as optional numbers because a small number of
 * historical rows are missing scores; consumers must guard for `undefined`.
 */

/** Competitions represented across the datasets. */
export type Competition =
  | "Brasileirão Série A"
  | "Brasileirão Série B"
  | "Brasileirão Série C"
  | "Copa do Brasil"
  | "Copa Libertadores"
  | "Other";

/** Source dataset a record was loaded from (for provenance/debugging). */
export type SourceFile =
  | "Brasileirao_Matches.csv"
  | "Brazilian_Cup_Matches.csv"
  | "Libertadores_Matches.csv"
  | "BR-Football-Dataset.csv"
  | "novo_campeonato_brasileiro.csv";

/** A single match/fixture unified across all match datasets. */
export interface Match {
  /** Stable synthetic id: `${source}#${rowIndex}`. */
  id: string;
  competition: Competition;
  source: SourceFile;
  /** ISO `YYYY-MM-DD`, or undefined when the source date was unparseable. */
  date?: string;
  season?: number;
  round?: string;
  stage?: string;
  /** Cleaned, human-readable team names. */
  homeTeam: string;
  awayTeam: string;
  /** Canonical matching keys (accent-folded, suffix-stripped). */
  homeKey: string;
  awayKey: string;
  homeGoals?: number;
  awayGoals?: number;
  arena?: string;
  /** Optional extended statistics (only BR-Football-Dataset.csv). */
  stats?: MatchStats;
}

/** Extended per-match statistics available only in BR-Football-Dataset.csv. */
export interface MatchStats {
  homeShots?: number;
  awayShots?: number;
  homeCorners?: number;
  awayCorners?: number;
  homeAttacks?: number;
  awayAttacks?: number;
  totalCorners?: number;
  halfTimeHome?: string;
  halfTimeAway?: string;
}

/** A FIFA player database entry (subset of useful columns). */
export interface Player {
  id: string;
  name: string;
  age?: number;
  nationality: string;
  overall?: number;
  potential?: number;
  club: string;
  /** Canonical key for the player's club. */
  clubKey: string;
  position: string;
  jerseyNumber?: number;
  height?: string;
  weight?: string;
  preferredFoot?: string;
}

/** The fully loaded, in-memory knowledge base. */
export interface SoccerData {
  matches: Match[];
  players: Player[];
}
