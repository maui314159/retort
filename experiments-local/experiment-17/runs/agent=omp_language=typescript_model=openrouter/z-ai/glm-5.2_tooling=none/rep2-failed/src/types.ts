/**
 * brazilian-soccer-mcp / src/types.ts
 *
 * Shared domain types for the Brazilian Soccer MCP server.
 *
 * Context block:
 * This server unifies six Kaggle CSV datasets (4 match files covering the
 * Brasileirão, Copa do Brasil, Copa Libertadores, an extended-stats file and
 * a historical 2003-2019 Brasileirão file, plus a FIFA player database) into a
 * single in-memory knowledge graph. Each match is normalized to a common
 * `Match` shape regardless of source schema; each player to a `Player` shape.
 * Team names are normalized to a diacritic- and state-suffix-free key so the
 * same club can be matched across files that spell it differently
 * ("Palmeiras-SP", "Palmeiras", "São Paulo" vs "Sao Paulo").
 */

/** A single normalized match from any of the match CSV files. */
export interface Match {
  /** Stable normalized competition label (e.g. "Brasileirão", "Copa do Brasil"). */
  competition: string;
  /** Source CSV filename, for provenance. */
  sourceFile: string;
  /** ISO date `YYYY-MM-DD`, or null if the raw date could not be parsed. */
  date: string | null;
  /** Original date string from the CSV. */
  rawDate: string;
  /** Season year, or null if absent. */
  season: number | null;
  /** Round or stage label as a string (e.g. "22", "final", "group stage"). */
  round: string | null;
  /** Display home team name (state suffix / parentheticals stripped, accents kept). */
  homeTeam: string;
  /** Display away team name. */
  awayTeam: string;
  /** Disambiguated club key for the home team (core, or core-state if ambiguous). */
  homeTeamKey: string;
  /** Disambiguated club key for the away team. */
  awayTeamKey: string;
  /** Core matching key for the home team (state-stripped); used for queries. */
  homeTeamCore: string;
  /** Core matching key for the away team. */
  awayTeamCore: string;
  /** Resolved home team state/country (e.g. "SP", "URU"), or null. */
  homeState: string | null;
  /** Resolved away team state/country, or null. */
  awayState: string | null;
  /** Home goals, or null if missing/unparseable. */
  homeGoal: number | null;
  /** Away goals, or null if missing/unparseable. */
  awayGoal: number | null;
  /** Tournament stage (Libertadores), when available. */
  stage: string | null;
  /** Stadium / arena name, when available. */
  venue: string | null;
  // ---- Extended statistics (from BR-Football-Dataset.csv; null otherwise) ----
  homeCorner?: number | null;
  awayCorner?: number | null;
  homeShots?: number | null;
  awayShots?: number | null;
  homeAttack?: number | null;
  awayAttack?: number | null;
  totalCorners?: number | null;
  htResult?: string | null;
  atResult?: string | null;
}

/** A single normalized FIFA player record. */
export interface Player {
  id: number;
  name: string;
  age: number | null;
  nationality: string;
  overall: number | null;
  potential: number | null;
  club: string;
  /** Normalized matching key for the club. */
  clubKey: string;
  /** Playing position code (e.g. "ST", "GK", "CDM"). */
  position: string;
  jerseyNumber: number | null;
  /** Raw market value string (e.g. "€110.5M"). */
  value: string;
  /** Raw wage string (e.g. "€565K"). */
  wage: string;
}

/** Venue filter for team statistics. */
export type Venue = "home" | "away" | "all";

/** Sort keys for player search. */
export type PlayerSort = "overall" | "potential" | "age" | "name";

/** Coarse position group. */
export type PositionGroup = "goalkeeper" | "defender" | "midfielder" | "forward";

/** Team win/draw/loss aggregate. */
export interface TeamStat {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  winRate: number;
}

/** A standings table row (points-based, for round-robin leagues). */
export interface StandingRow {
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
