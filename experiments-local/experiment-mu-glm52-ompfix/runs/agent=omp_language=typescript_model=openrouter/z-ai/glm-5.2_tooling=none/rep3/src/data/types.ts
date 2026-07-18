/**
 * Brazilian Soccer MCP Server — Shared Types
 * -----------------------------------------------------------------------------
 * Context block:
 *   This file defines the canonical, normalized data model used across the
 *   entire MCP server. All six provided Kaggle CSV datasets are parsed into the
 *   unified `Match` shape below (with per-dataset `source` provenance), and the
 *   FIFA player dataset is parsed into `Player`. Keeping a single normalized
 *   model lets every query tool reason about matches uniformly regardless of
 *   the originating file, while the `source` field preserves provenance so
 *   callers can scope queries to a specific dataset.
 *
 *   Competition naming: the datasets overlap (e.g. the modern Brasileirão file
 *   and the historical 2003-2019 file both cover Serie A for 2012-2019). We do
 *   NOT deduplicate; instead each match carries both a machine `competition`
 *   key and a human `competitionLabel`, and aggregate tools operate on an
 *   explicitly requested (competition, source, season) scope so overlapping
 *   datasets never silently double-count.
 */

/** A machine-readable competition key. */
export type CompetitionKey =
  | "brasileirao"
  | "copa-do-brasil"
  | "libertadores"
  | "brasileirao-historical"
  | "serie-a"
  | "serie-b"
  | "serie-c"
  | "copa-do-brasil-ext";

/** Which physical dataset a match came from. */
export type SourceKey =
  | "Brasileirao_Matches"
  | "Brazilian_Cup_Matches"
  | "Libertadores_Matches"
  | "novo_campeonato_brasileiro"
  | "BR-Football-Dataset";

/** Venue filter for team-stat queries. */
export type Venue = "home" | "away" | "either";

/** A normalized match record covering all six match datasets. */
export interface Match {
  /** Stable id, unique within a source. */
  id: string;
  /** Physical dataset the record came from. */
  source: SourceKey;
  /** Machine competition key. */
  competition: CompetitionKey;
  /** Human-readable competition name, e.g. "Brasileirão Serie A". */
  competitionLabel: string;
  /** Season year, or null when missing (e.g. the Libertadores NA row). */
  season: number | null;
  /** ISO date `YYYY-MM-DD`, or null when unparseable. */
  date: string | null;
  /** Full ISO datetime string when available. */
  datetime: string | null;
  /** Normalized display home team name (state suffix / country parens stripped). */
  homeTeam: string;
  /** Normalized display away team name. */
  awayTeam: string;
  /** Original home team string from the CSV. */
  homeTeamRaw: string;
  /** Original away team string from the CSV. */
  awayTeamRaw: string;
  /** State abbreviation when known. */
  homeState: string | null;
  awayState: string | null;
  /** Goals, or null when not recorded (unscored/scheduled). */
  homeGoals: number | null;
  awayGoals: number | null;
  /** Round number/label when present. */
  round: string | null;
  /** Tournament stage (Libertadores / knockouts), when present. */
  stage: string | null;
  /** Stadium name when present (historical dataset). */
  stadium: string | null;
  /** Half-time result label for home side, when present. */
  htResult: string | null;
  /** Half-time result label for away side, when present. */
  atResult: string | null;
  /** Extended statistics from BR-Football-Dataset, when present. */
  homeCorners: number | null;
  awayCorners: number | null;
  homeShots: number | null;
  awayShots: number | null;
  homeAttacks: number | null;
  awayAttacks: number | null;
  totalCorners: number | null;
}

/** A normalized FIFA player record. */
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
  preferredFoot: string | null;
  height: string | null;
  weight: string | null;
  /** Selected skill ratings, parsed to numbers where possible. */
  crossing: number | null;
  finishing: number | null;
  dribbling: number | null;
  shortPassing: number | null;
  longPassing: number | null;
  shotPower: number | null;
  internationalReputation: number | null;
}

/** Win/draw/loss + goals tally for a team over a set of matches. */
export interface TeamStat {
  team: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  /** Points (3 per win, 1 per draw) — meaningful for league standings. */
  points: number;
  winRate: number;
}

/** A single row in a computed standings table. */
export interface StandingRow extends TeamStat {
  position: number;
}

/** Head-to-head summary between two teams. */
export interface HeadToHead {
  team1: string;
  team2: string;
  team1Wins: number;
  team2Wins: number;
  draws: number;
  played: number;
  team1Goals: number;
  team2Goals: number;
  matches: Match[];
}

/** Aggregate statistics for a scoped set of matches. */
export interface MatchStatistics {
  matches: number;
  scoredMatches: number;
  totalGoals: number;
  averageGoals: number;
  homeWins: number;
  awayWins: number;
  draws: number;
  homeWinRate: number;
  awayWinRate: number;
  drawRate: number;
  averageHomeGoals: number;
  averageAwayGoals: number;
  biggestHomeWin: Match | null;
  biggestAwayWin: Match | null;
}

/** Brazilian players at Brazilian clubs, grouped by club. */
export interface ClubBrazilianPlayers {
  club: string;
  count: number;
  averageOverall: number;
  topPlayer: string | null;
}

/** A catalog entry describing an available dataset/competition. */
export interface CompetitionInfo {
  competition: CompetitionKey;
  label: string;
  source: SourceKey;
  seasons: number[];
  matchCount: number;
}

/** The full in-memory dataset loaded once at server startup. */
export interface Dataset {
  matches: Match[];
  players: Player[];
  competitions: CompetitionInfo[];
}
