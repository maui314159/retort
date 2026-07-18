/**
 * brazilian-soccer-mcp — shared domain types
 *
 * Context block
 * ============
 * Project : Brazilian Soccer MCP Server (TS implementation)
 * Purpose : Provide an MCP tool interface over six Kaggle CSV datasets
 *           (Brasileirão, Copa do Brasil, Libertadores, extended stats,
 *           historical Brasileirão 2003-2019, and FIFA player database).
 * Datasets: data/kaggle/*.csv — see TASK.md for schemas & licenses.
 * Design   : All datasets are normalised into a single `MatchRecord` /
 *            `PlayerRecord` shape so the query engine can treat the
 *            five match files uniformly regardless of source column
 *            naming (Portuguese vs English, state-suffixed team names,
 *            ISO vs DD/MM/YYYY dates).
 * License  : MIT (code); data retains upstream Kaggle licenses.
 */

/** A single normalised match drawn from any of the five match CSVs. */
export interface MatchRecord {
  /** Source dataset identifier. */
  source:
    | "brasileirao"
    | "copa_do_brasil"
    | "libertadores"
    | "br_football"
    | "historical_brasileirao";
  /** Human-readable competition name (e.g. "Brasileirão", "Copa do Brasil"). */
  competition: string;
  /** ISO 8601 date (YYYY-MM-DD) when the match was played, if known. */
  date: string | null;
  /** Full ISO datetime string if the source recorded time, else null. */
  datetime: string | null;
  /** Normalised home team name (no state suffix, accents preserved). */
  homeTeam: string;
  /** Normalised away team name. */
  awayTeam: string;
  /** Home team state/UF abbreviation when available (e.g. "SP"), else null. */
  homeState: string | null;
  awayState: string | null;
  /** Home goals (parsed to number; null if not scoreable). */
  homeGoal: number | null;
  awayGoal: number | null;
  /** Season year (4-digit). */
  season: number | null;
  /** Round/stage label as recorded by the source. */
  round: string | null;
  /** Stadium/arena when recorded. */
  arena: string | null;
  /** Extended stats — only populated from BR-Football-Dataset. */
  stats?: MatchStats;
}

export interface MatchStats {
  homeCorner: number | null;
  awayCorner: number | null;
  homeAttack: number | null;
  awayAttack: number | null;
  homeShots: number | null;
  awayShots: number | null;
  totalCorners: number | null;
  halfTimeHome: number | null;
  halfTimeAway: number | null;
}

/** A normalised FIFA player row. */
export interface PlayerRecord {
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
}

/** Outcome of a match from a single team's perspective. */
export type Outcome = "win" | "loss" | "draw";

export interface TeamStats {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  points: number;
  /** Per-venue breakdown. */
  home: Omit<TeamStats, "team" | "home" | "away">;
  away: Omit<TeamStats, "team" | "home" | "away">;
}

export interface HeadToHead {
  teamA: string;
  teamB: string;
  matches: number;
  teamAWins: number;
  teamBWins: number;
  draws: number;
  teamAGoals: number;
  teamBGoals: number;
  matchesList: MatchRecord[];
}

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
