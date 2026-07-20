/**
 * Core domain types for the Brazilian soccer knowledge graph.
 */

/** Competitions covered by the provided datasets. */
export enum Competition {
  BrasileiraoSerieA = "Brasileirão Série A",
  SerieB = "Série B",
  SerieC = "Série C",
  CopaDoBrasil = "Copa do Brasil",
  Libertadores = "Copa Libertadores",
}

/** Canonical team node in the knowledge graph. */
export interface Team {
  /** Canonical key, e.g. "palmeiras-sp", "atletico-mg", "santos". */
  key: string;
  /** Human-friendly display name, e.g. "Palmeiras". */
  name: string;
  /** State/region abbreviation when known (e.g. "SP", "RJ"), else null. */
  uf: string | null;
  /** Normalized aliases that resolve to this team. */
  aliases: Set<string>;
}

/** A normalized match record, merged across all datasets. */
export interface Match {
  id: string;
  competition: Competition;
  season: number | null;
  /** Round or stage label ("1".."38", "final", "group stage", ...). */
  round: string | null;
  /** ISO date YYYY-MM-DD (null when unknown). */
  date: string | null;
  /** Kick-off time HH:MM when known. */
  time: string | null;
  homeTeam: Team;
  awayTeam: Team;
  /** Final score; null when the match was not played / score unknown. */
  homeGoals: number | null;
  awayGoals: number | null;
  stadium: string | null;
  /** Optional extended statistics (from BR-Football-Dataset). */
  stats: MatchStats | null;
  /** Source CSV files this match was found in (dedupe provenance). */
  sources: string[];
}

export interface MatchStats {
  homeCorners: number | null;
  awayCorners: number | null;
  homeShots: number | null;
  awayShots: number | null;
  homeAttacks: number | null;
  awayAttacks: number | null;
  halfTimeHomeGoals: number | null;
  halfTimeAwayGoals: number | null;
}

/** A FIFA player record (only the columns useful for querying). */
export interface Player {
  id: number;
  name: string;
  age: number | null;
  nationality: string;
  overall: number | null;
  potential: number | null;
  club: string | null;
  position: string | null;
  jerseyNumber: number | null;
  height: string | null;
  weight: string | null;
  preferredFoot: string | null;
  skills: Record<string, number | null>;
  /** Resolved canonical team key when the club is a known Brazilian team. */
  teamKey: string | null;
}

export type MatchResult = "home" | "away" | "draw";

/** Result of a played match (null goals => not played). */
export function matchResult(m: Match): MatchResult | null {
  if (m.homeGoals === null || m.awayGoals === null) return null;
  if (m.homeGoals > m.awayGoals) return "home";
  if (m.homeGoals < m.awayGoals) return "away";
  return "draw";
}
