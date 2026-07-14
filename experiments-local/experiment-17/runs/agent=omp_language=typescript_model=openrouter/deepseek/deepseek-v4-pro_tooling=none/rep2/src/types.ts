/**
 * Brazilian Soccer MCP Server — Normalized Types
 *
 * All match records across different CSV files are unified into this single
 * normalized representation. Team names are stored in their canonical form
 * (state suffix stripped, diacritics preserved, case-normalized for lookup).
 */

export type Competition =
  | "Brasileirão"
  | "Copa do Brasil"
  | "Copa Libertadores"
  | "Brasileirão (Histórico)";

/** A single match in normalized form across all data sources. */
export interface NormalizedMatch {
  /** Competition name */
  competition: Competition;
  /** ISO date string (YYYY-MM-DD) */
  date: string;
  /** Optional time string */
  time?: string;
  /** Canonical home team name (no state suffix) */
  homeTeam: string;
  /** Canonical away team name (no state suffix) */
  awayTeam: string;
  /** Home goals */
  homeGoal: number;
  /** Away goals */
  awayGoal: number;
  /** Season year */
  season: number;
  /** Round or stage description */
  round?: string;
  /** Original source file for traceability */
  source: string;
}

/** A player record from the FIFA dataset. */
export interface Player {
  id: number;
  name: string;
  age: number;
  nationality: string;
  overall: number;
  potential: number;
  club: string;
  position: string;
  jerseyNumber: number | null;
  height: string;
  weight: string;
  preferredFoot: string;
  skillMoves: number;
  weakFoot: number;
  workRate: string;
}

/** Team statistics summary. */
export interface TeamStats {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  winRate: number;
}

/** Head-to-head record between two teams. */
export interface HeadToHead {
  teamA: string;
  teamB: string;
  matches: NormalizedMatch[];
  teamAWins: number;
  teamBWins: number;
  draws: number;
}

/** Competition standings for a season. */
export interface Standing {
  position: number;
  team: string;
  points: number;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
}

/** Loaded dataset in memory. */
export interface SoccerData {
  matches: NormalizedMatch[];
  players: Player[];
}

/**
 * Normalize a team name for consistent matching.
 * - Strips state suffixes like "-SP", "-RJ", " - SP"
 * - Removes parenthetical disambiguation like "(URU)"
 * - Trims whitespace
 */
export function normalizeTeamName(name: string): string {
  let n = name.trim();
  // Strip parenthetical suffixes like "(URU)", "(antigo ...)"
  n = n.replace(/\s*\(.*?\)\s*/g, " ").trim();
  // Strip state suffix patterns: "-SP", " - SP", "-RJ", " - RJ"
  n = n.replace(/\s*-\s*[A-Z]{2}\s*$/i, "").trim();
  return n;
}

/**
 * Fuzzy-match a user-provided team name against the set of known teams.
 * Returns the canonical name if found, or the normalized input otherwise.
 */
export function lookupTeam(
  input: string,
  knownTeams: Set<string>,
): string | undefined {
  const normalized = normalizeTeamName(input).toLowerCase();

  // Exact match (case-insensitive)
  for (const t of knownTeams) {
    if (t.toLowerCase() === normalized) return t;
  }

  // Contains match (e.g., "Flamengo" matches "Flamengo")
  for (const t of knownTeams) {
    if (t.toLowerCase().includes(normalized)) return t;
  }

  // Reverse contains (e.g., "São Paulo" matches "São Paulo FC")
  for (const t of knownTeams) {
    if (normalized.includes(t.toLowerCase())) return t;
  }

  return undefined;
}

/** Build a set of all known team names from match data. */
export function buildKnownTeams(matches: NormalizedMatch[]): Set<string> {
  const teams = new Set<string>();
  for (const m of matches) {
    teams.add(m.homeTeam);
    teams.add(m.awayTeam);
  }
  return teams;
}