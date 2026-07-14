/**
 * Brazilian Soccer MCP Server - Player Database
 *
 * Query interface for FIFA player data.
 * Supports search by name, nationality, club, position, and rating range.
 */

import { loadFIFAPlayers, type FIFAPlayer } from "./data-loader.js";
import { normalizeTeam, teamMatches } from "./team-normalizer.js";

// --- Cache ---

let _players: FIFAPlayer[] | null = null;

export function getAllPlayers(): FIFAPlayer[] {
  if (!_players) {
    _players = loadFIFAPlayers();
  }
  return _players;
}

// --- Query Functions ---

export interface PlayerSearchFilters {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  maxOverall?: number;
  minPotential?: number;
  sortBy?: "overall" | "potential" | "age" | "name";
  sortDir?: "asc" | "desc";
  limit?: number;
}

export interface ClubSummary {
  club: string;
  playerCount: number;
  avgRating: number;
  topPlayer: string;
  topRating: number;
}

/**
 * Search players with multiple filter criteria.
 */
export function searchPlayers(filters: PlayerSearchFilters): FIFAPlayer[] {
  let results = getAllPlayers();

  if (filters.name) {
    const q = filters.name.toLowerCase();
    results = results.filter((p) => p.name.toLowerCase().includes(q));
  }

  if (filters.nationality) {
    const q = filters.nationality.toLowerCase();
    results = results.filter((p) => p.nationality.toLowerCase() === q ||
      p.nationality.toLowerCase().includes(q));
  }

  if (filters.club) {
    // Match club name with partial matching and team normalization
    results = results.filter((p) => {
      const clubName = p.club.toLowerCase();
      const query = filters.club!.toLowerCase();
      // Direct substring match
      if (clubName.includes(query)) return true;
      // Try normalized match
      return teamMatches(p.club, filters.club!);
    });
  }

  if (filters.position) {
    const q = filters.position.toUpperCase();
    results = results.filter((p) => {
      const positions = p.position.toUpperCase().split(/[/, ]+/);
      return positions.some((pos) => pos === q || pos.includes(q));
    });
  }

  if (filters.minOverall !== undefined) {
    results = results.filter((p) => p.overall >= filters.minOverall!);
  }

  if (filters.maxOverall !== undefined) {
    results = results.filter((p) => p.overall <= filters.maxOverall!);
  }

  if (filters.minPotential !== undefined) {
    results = results.filter((p) => p.potential >= filters.minPotential!);
  }

  // Sort
  const sortBy = filters.sortBy || "overall";
  const sortDir = filters.sortDir || "desc";

  results.sort((a, b) => {
    let cmp: number;
    switch (sortBy) {
      case "overall":
        cmp = a.overall - b.overall;
        break;
      case "potential":
        cmp = a.potential - b.potential;
        break;
      case "age":
        cmp = a.age - b.age;
        break;
      case "name":
        cmp = a.name.localeCompare(b.name);
        break;
      default:
        cmp = 0;
    }
    return sortDir === "desc" ? -cmp : cmp;
  });

  if (filters.limit && filters.limit > 0) {
    results = results.slice(0, filters.limit);
  }

  return results;
}

/**
 * Get detailed info for a specific player by name lookup.
 */
export function getPlayerDetails(name: string): FIFAPlayer | null {
  const q = name.toLowerCase();
  const players = getAllPlayers();

  // Try exact match first
  let match = players.find((p) => p.name.toLowerCase() === q);
  if (match) return match;

  // Try contains match
  match = players.find((p) => p.name.toLowerCase().includes(q));
  return match || null;
}

/**
 * Get club summaries (player counts and avg ratings) for clubs matching a query.
 */
export function getClubSummaries(clubFilter?: string): ClubSummary[] {
  const clubMap = new Map<string, { ratings: number[]; topPlayer: string; topRating: number }>();

  for (const p of getAllPlayers()) {
    if (!p.club) continue;
    if (clubFilter && !p.club.toLowerCase().includes(clubFilter.toLowerCase())) continue;

    const key = p.club;
    if (!clubMap.has(key)) {
      clubMap.set(key, { ratings: [], topPlayer: p.name, topRating: p.overall });
    }
    const entry = clubMap.get(key)!;
    entry.ratings.push(p.overall);
    if (p.overall > entry.topRating) {
      entry.topRating = p.overall;
      entry.topPlayer = p.name;
    }
  }

  const summaries: ClubSummary[] = [];
  for (const [club, data] of clubMap) {
    const avg = data.ratings.reduce((s, r) => s + r, 0) / data.ratings.length;
    summaries.push({
      club,
      playerCount: data.ratings.length,
      avgRating: Math.round(avg * 10) / 10,
      topPlayer: data.topPlayer,
      topRating: data.topRating,
    });
  }

  summaries.sort((a, b) => b.avgRating - a.avgRating);
  return summaries;
}

/**
 * Get the top players by overall rating, optionally filtered.
 */
export function getTopPlayers(limit: number = 10, nationality?: string, club?: string): FIFAPlayer[] {
  return searchPlayers({
    nationality,
    club,
    sortBy: "overall",
    sortDir: "desc",
    limit,
  });
}

/**
 * Format a player for display.
 */
export function formatPlayer(p: FIFAPlayer): string {
  return [
    `${p.name} (#${p.jersey_number || "N/A"})`,
    `  Overall: ${p.overall} | Potential: ${p.potential}`,
    `  Position: ${p.position} | Age: ${p.age}`,
    `  Nationality: ${p.nationality}`,
    `  Club: ${p.club}`,
    `  Height: ${p.height} | Weight: ${p.weight}`,
    `  Preferred Foot: ${p.preferred_foot} | Weak Foot: ${p.weak_foot}★ | Skill Moves: ${p.skill_moves}★`,
    `  Work Rate: ${p.work_rate}`,
    `  Value: ${p.value} | Wage: ${p.wage}`,
    `  Key Stats: PAC ${Math.round((p.acceleration + p.sprint_speed) / 2)} | SHO ${p.finishing} | PAS ${p.short_passing} | DRI ${p.dribbling} | DEF ${Math.round((p.marking + p.standing_tackle + p.sliding_tackle) / 3)} | PHY ${Math.round((p.stamina + p.strength) / 2)}`,
  ].join("\n");
}

/**
 * Format a compact player summary.
 */
export function formatPlayerCompact(p: FIFAPlayer): string {
  return `${p.name} - Overall: ${p.overall}, Position: ${p.position}, Club: ${p.club}, Age: ${p.age}, Nationality: ${p.nationality}`;
}