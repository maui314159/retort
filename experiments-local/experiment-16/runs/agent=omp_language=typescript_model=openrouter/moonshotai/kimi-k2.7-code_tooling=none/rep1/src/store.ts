/**
 * In-memory data store and query engine.
 *
 * All CSV rows are loaded once into memory. This keeps lookups fast (<2s) and
 * lets the MCP tools focus on formatting while the store answers the actual
 * soccer questions.
 */

import type { DataStore, HeadToHead, Match, Player, TeamRecord } from "./types.js";
import { normalizeCompetition, parseDate, teamDisplay, teamKey } from "./normalize.js";

export interface MatchFilters {
  team?: string;
  opponent?: string;
  from?: string | Date | null;
  to?: string | Date | null;
  competition?: string;
  season?: number;
  round?: string;
  venue?: "home" | "away" | "all";
  limit?: number;
}

export interface TeamStatFilters {
  season?: number;
  competition?: string;
  venue?: "home" | "away" | "all";
}

export interface PlayerFilters {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  limit?: number;
}

function toDate(value: string | Date | null | undefined): Date | null {
  if (value instanceof Date) return value;
  if (typeof value === "string" && value !== "") return parseDate(value);
  return null;
}

function dateCompare(a: Date | null, b: Date | null): number {
  if (a && b) return b.getTime() - a.getTime();
  if (a) return -1;
  if (b) return 1;
  return 0;
}

function matchesCompetition(match: Match, competition: string): boolean {
  return match.competition.toLowerCase().includes(competition.toLowerCase().trim());
}

export class SoccerStore {
  readonly matches: Match[];
  readonly players: Player[];
  private readonly teamDisplays = new Map<string, string>();

  constructor(data: DataStore) {
    this.matches = data.matches;
    this.players = data.players;
    this.indexTeamDisplays();
  }

  private indexTeamDisplays(): void {
    for (const match of this.matches) {
      if (!this.teamDisplays.has(match.homeKey)) {
        this.teamDisplays.set(match.homeKey, match.homeTeam);
      }
      if (!this.teamDisplays.has(match.awayKey)) {
        this.teamDisplays.set(match.awayKey, match.awayTeam);
      }
    }
    for (const player of this.players) {
      if (player.clubKey && !this.teamDisplays.has(player.clubKey)) {
        this.teamDisplays.set(player.clubKey, teamDisplay(player.club, player.clubKey));
      }
    }
  }

  displayFor(key: string): string {
    return this.teamDisplays.get(key) ?? teamDisplay("", key);
  }

  searchMatches(filters: MatchFilters): Match[] {
    const teamKeyFilter = filters.team ? teamKey(filters.team) : undefined;
    const opponentKey = filters.opponent ? teamKey(filters.opponent) : undefined;
    const from = toDate(filters.from);
    const to = toDate(filters.to);
    const competition = filters.competition ? normalizeCompetition(filters.competition) : undefined;
    const round = filters.round?.toLowerCase();

    const results = this.matches.filter((m) => {
      if (teamKeyFilter) {
        const isHome = m.homeKey === teamKeyFilter;
        const isAway = m.awayKey === teamKeyFilter;
        if (!isHome && !isAway) return false;
        if (filters.venue === "home" && !isHome) return false;
        if (filters.venue === "away" && !isAway) return false;
      }
      if (opponentKey) {
        if (m.homeKey !== opponentKey && m.awayKey !== opponentKey) return false;
        if (teamKeyFilter) {
          const hasBoth =
            (m.homeKey === teamKeyFilter && m.awayKey === opponentKey) ||
            (m.homeKey === opponentKey && m.awayKey === teamKeyFilter);
          if (!hasBoth) return false;
        }
      }
      if (competition && !matchesCompetition(m, competition)) return false;
      if (filters.season !== undefined && m.season !== filters.season) return false;
      if (from && m.date && m.date < from) return false;
      if (to && m.date && m.date > to) return false;
      if (round && (!m.round || !m.round.toLowerCase().includes(round))) return false;
      return true;
    });

    results.sort((a, b) => dateCompare(a.date, b.date));
    return filters.limit ? results.slice(0, filters.limit) : results;
  }

  teamStatistics(team: string, filters: TeamStatFilters = {}): TeamRecord {
    const key = teamKey(team);
    const venue = filters.venue ?? "all";
    const competition = filters.competition ? normalizeCompetition(filters.competition) : undefined;

    let matches = 0;
    let wins = 0;
    let draws = 0;
    let losses = 0;
    let goalsFor = 0;
    let goalsAgainst = 0;

    for (const m of this.matches) {
      if (filters.season !== undefined && m.season !== filters.season) continue;
      if (competition && !matchesCompetition(m, competition)) continue;

      const isHome = m.homeKey === key;
      const isAway = m.awayKey === key;
      if (!isHome && !isAway) continue;
      if (venue === "home" && !isHome) continue;
      if (venue === "away" && !isAway) continue;
      if (m.homeGoals === null || m.awayGoals === null) continue;

      matches++;
      const forGoals = isHome ? m.homeGoals : m.awayGoals;
      const againstGoals = isHome ? m.awayGoals : m.homeGoals;
      goalsFor += forGoals;
      goalsAgainst += againstGoals;

      if (forGoals > againstGoals) wins++;
      else if (forGoals === againstGoals) draws++;
      else losses++;
    }

    return {
      team: this.displayFor(key),
      key,
      matches,
      wins,
      draws,
      losses,
      goalsFor,
      goalsAgainst,
      points: wins * 3 + draws,
    };
  }

  headToHead(teamA: string, teamB: string, filters: Omit<TeamStatFilters, "venue"> = {}): HeadToHead {
    const keyA = teamKey(teamA);
    const keyB = teamKey(teamB);
    const competition = filters.competition ? normalizeCompetition(filters.competition) : undefined;

    const matches = this.matches.filter((m) => {
      const hasA = m.homeKey === keyA || m.awayKey === keyA;
      const hasB = m.homeKey === keyB || m.awayKey === keyB;
      if (!hasA || !hasB) return false;
      if (filters.season !== undefined && m.season !== filters.season) return false;
      if (competition && !matchesCompetition(m, competition)) return false;
      if (m.homeGoals === null || m.awayGoals === null) return false;
      return true;
    });

    matches.sort((a, b) => dateCompare(a.date, b.date));

    let winsA = 0;
    let winsB = 0;
    let draws = 0;
    for (const m of matches) {
      const aIsHome = m.homeKey === keyA;
      const aGoals = aIsHome ? m.homeGoals! : m.awayGoals!;
      const bGoals = aIsHome ? m.awayGoals! : m.homeGoals!;
      if (aGoals > bGoals) winsA++;
      else if (aGoals < bGoals) winsB++;
      else draws++;
    }

    return {
      teamA: this.displayFor(keyA),
      teamB: this.displayFor(keyB),
      matches,
      winsA,
      winsB,
      draws,
    };
  }

  competitionStandings(competition: string, season: number): TeamRecord[] {
    const norm = normalizeCompetition(competition);
    const table = new Map<string, TeamRecord>();

    for (const m of this.matches) {
      if (m.season !== season) continue;
      if (!matchesCompetition(m, norm)) continue;
      if (m.homeGoals === null || m.awayGoals === null) continue;

      this.updateStanding(table, m.homeKey, m.homeGoals, m.awayGoals);
      this.updateStanding(table, m.awayKey, m.awayGoals, m.homeGoals);
    }

    return Array.from(table.values()).sort((a, b) => {
      if (b.points !== a.points) return b.points - a.points;
      const diffA = a.goalsFor - a.goalsAgainst;
      const diffB = b.goalsFor - b.goalsAgainst;
      if (diffB !== diffA) return diffB - diffA;
      return b.goalsFor - a.goalsFor;
    });
  }

  private updateStanding(
    table: Map<string, TeamRecord>,
    key: string,
    forGoals: number,
    againstGoals: number
  ): void {
    const existing = table.get(key);
    const record = existing ?? {
      team: this.displayFor(key),
      key,
      matches: 0,
      wins: 0,
      draws: 0,
      losses: 0,
      goalsFor: 0,
      goalsAgainst: 0,
      points: 0,
    };
    record.matches++;
    record.goalsFor += forGoals;
    record.goalsAgainst += againstGoals;
    if (forGoals > againstGoals) {
      record.wins++;
      record.points += 3;
    } else if (forGoals === againstGoals) {
      record.draws++;
      record.points += 1;
    } else {
      record.losses++;
    }
    if (!existing) table.set(key, record);
  }

  biggestWins(filters: Omit<MatchFilters, "team" | "opponent" | "venue"> = {}): Match[] {
    const competition = filters.competition ? normalizeCompetition(filters.competition) : undefined;
    const from = toDate(filters.from);
    const to = toDate(filters.to);

    const results = this.matches.filter((m) => {
      if (filters.season !== undefined && m.season !== filters.season) return false;
      if (competition && !matchesCompetition(m, competition)) return false;
      if (from && m.date && m.date < from) return false;
      if (to && m.date && m.date > to) return false;
      return m.homeGoals !== null && m.awayGoals !== null;
    });

    results.sort((a, b) => {
      const diffA = Math.abs((a.homeGoals ?? 0) - (a.awayGoals ?? 0));
      const diffB = Math.abs((b.homeGoals ?? 0) - (b.awayGoals ?? 0));
      return diffB - diffA;
    });

    return filters.limit ? results.slice(0, filters.limit) : results;
  }

  searchPlayers(filters: PlayerFilters): Player[] {
    const clubKey = filters.club ? teamKey(filters.club) : undefined;
    const nameLower = filters.name?.toLowerCase().trim();
    const nationalityLower = filters.nationality?.toLowerCase().trim();
    const positionUpper = filters.position?.toUpperCase().trim();

    const results = this.players.filter((p) => {
      if (nameLower && !p.name.toLowerCase().includes(nameLower)) return false;
      if (nationalityLower && !p.nationality?.toLowerCase().includes(nationalityLower)) return false;
      if (clubKey && p.clubKey !== clubKey) return false;
      if (positionUpper && p.position?.toUpperCase() !== positionUpper) return false;
      if (filters.minOverall !== undefined && (p.overall ?? 0) < filters.minOverall) return false;
      return true;
    });

    results.sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
    return filters.limit ? results.slice(0, filters.limit) : results;
  }

  averageGoalsPerMatch(filters: Omit<MatchFilters, "team" | "opponent" | "venue"> = {}): number {
    const competition = filters.competition ? normalizeCompetition(filters.competition) : undefined;
    let total = 0;
    let count = 0;
    for (const m of this.matches) {
      if (filters.season !== undefined && m.season !== filters.season) continue;
      if (competition && !matchesCompetition(m, competition)) continue;
      if (m.homeGoals === null || m.awayGoals === null) continue;
      total += m.homeGoals + m.awayGoals;
      count++;
    }
    return count === 0 ? 0 : total / count;
  }
}
