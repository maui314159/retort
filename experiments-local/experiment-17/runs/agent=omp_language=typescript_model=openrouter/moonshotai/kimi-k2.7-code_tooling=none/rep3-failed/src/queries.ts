/**
 * Query engine.
 *
 * Implements all domain-level questions described in the specification:
 * match searches, head-to-head records, team statistics, player lookups,
 * competition standings, and aggregate analytics.
 */

import type { Match, Player, TeamRecord, HeadToHead } from "./models.js";
import type { SoccerRepository } from "./loaders.js";
import { teamMatches, normalizeTeamName } from "./normalize.js";
import { inRange } from "./dates.js";

export interface MatchFilters {
  team?: string;
  opponent?: string;
  home?: string;
  away?: string;
  competition?: string;
  season?: number;
  startDate?: string;
  endDate?: string;
  round?: string | number;
  stage?: string;
  limit?: number;
}

export interface TeamStatsParams {
  team: string;
  season?: number;
  competition?: string;
  venue?: "home" | "away" | "both";
}

export interface PlayerFilters {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  limit?: number;
}

export interface StandingParams {
  competition?: string;
  season: number;
}

export class QueryEngine {
  constructor(private readonly repo: SoccerRepository) {}

  /** Find matches by flexible filters. */
  findMatches(filters: MatchFilters = {}): Match[] {
    let out = this.repo.matches;

    if (filters.team) {
      out = out.filter(
        (m) => teamMatches(filters.team!, m.homeTeam) || teamMatches(filters.team!, m.awayTeam),
      );
    }

    if (filters.opponent) {
      out = out.filter(
        (m) =>
          (teamMatches(filters.opponent!, m.homeTeam) || teamMatches(filters.opponent!, m.awayTeam)) &&
          (!filters.team ||
            teamMatches(filters.team!, m.homeTeam) ||
            teamMatches(filters.team!, m.awayTeam)),
      );
    }

    if (filters.home) {
      out = out.filter((m) => teamMatches(filters.home!, m.homeTeam));
    }

    if (filters.away) {
      out = out.filter((m) => teamMatches(filters.away!, m.awayTeam));
    }

    if (filters.competition) {
      const q = normalizeTeamName(filters.competition);
      out = out.filter((m) => normalizeTeamName(m.competition).includes(q));
    }

    if (filters.season !== undefined) {
      out = out.filter((m) => m.season === filters.season);
    }

    if (filters.startDate || filters.endDate) {
      out = out.filter((m) => inRange(m.date, filters.startDate, filters.endDate));
    }

    if (filters.round !== undefined) {
      const r = String(filters.round);
      out = out.filter((m) => m.round !== undefined && String(m.round) === r);
    }

    if (filters.stage) {
      const q = normalizeTeamName(filters.stage);
      out = out.filter((m) => m.stage && normalizeTeamName(m.stage).includes(q));
    }

    out = out.sort((a, b) => b.date.localeCompare(a.date));

    if (filters.limit !== undefined && filters.limit > 0) {
      out = out.slice(0, filters.limit);
    }

    return out;
  }

  /** Head-to-head record between two teams. */
  headToHead(teamA: string, teamB: string): HeadToHead {
    const matches = this.findMatches({ team: teamA, opponent: teamB }).sort((a, b) =>
      b.date.localeCompare(a.date),
    );

    let teamAWins = 0;
    let teamBWins = 0;
    let draws = 0;

    for (const m of matches) {
      const aHome = teamMatches(teamA, m.homeTeam);
      const aScore = aHome ? m.homeGoal : m.awayGoal;
      const bScore = aHome ? m.awayGoal : m.homeGoal;

      if (aScore > bScore) teamAWins++;
      else if (bScore > aScore) teamBWins++;
      else draws++;
    }

    return { teamA, teamB, matches, teamAWins, teamBWins, draws };
  }

  /** Team statistics (wins, draws, losses, goals, points). */
  teamStats(params: TeamStatsParams): TeamRecord {
    let matches = this.repo.matches.filter((m) =>
      teamMatches(params.team, m.homeTeam) || teamMatches(params.team, m.awayTeam),
    );

    if (params.season !== undefined) {
      matches = matches.filter((m) => m.season === params.season);
    }

    if (params.competition) {
      const q = normalizeTeamName(params.competition);
      matches = matches.filter((m) => normalizeTeamName(m.competition).includes(q));
    }

    if (params.venue === "home") {
      matches = matches.filter((m) => teamMatches(params.team, m.homeTeam));
    } else if (params.venue === "away") {
      matches = matches.filter((m) => teamMatches(params.team, m.awayTeam));
    }

    let wins = 0;
    let draws = 0;
    let losses = 0;
    let goalsFor = 0;
    let goalsAgainst = 0;

    for (const m of matches) {
      const isHome = teamMatches(params.team, m.homeTeam);
      const gf = isHome ? m.homeGoal : m.awayGoal;
      const ga = isHome ? m.awayGoal : m.homeGoal;

      goalsFor += gf;
      goalsAgainst += ga;

      if (gf > ga) wins++;
      else if (gf === ga) draws++;
      else losses++;
    }

    return {
      team: params.team,
      matches: matches.length,
      wins,
      draws,
      losses,
      goalsFor,
      goalsAgainst,
      points: wins * 3 + draws,
    };
  }

  /** Search players by name, nationality, club, position. */
  searchPlayers(filters: PlayerFilters = {}): Player[] {
    let out = this.repo.players;

    if (filters.name) {
      const q = normalizeTeamName(filters.name);
      out = out.filter((p) => normalizeTeamName(p.name).includes(q));
    }

    if (filters.nationality) {
      const q = normalizeTeamName(filters.nationality);
      out = out.filter((p) => normalizeTeamName(p.nationality).includes(q));
    }

    if (filters.club) {
      const q = normalizeTeamName(filters.club);
      out = out.filter((p) => normalizeTeamName(p.club).includes(q));
    }

    if (filters.position) {
      const q = filters.position.toUpperCase();
      out = out.filter((p) => p.position.toUpperCase().includes(q));
    }

    if (filters.minOverall !== undefined) {
      out = out.filter((p) => p.overall >= filters.minOverall!);
    }

    out = out.sort((a, b) => b.overall - a.overall);

    if (filters.limit !== undefined && filters.limit > 0) {
      out = out.slice(0, filters.limit);
    }

    return out;
  }

  /**
   * Compute league standings for a season/competition using the standard
   * points system (3 for a win, 1 for a draw). Ties are broken by goal
   * difference and then goals scored.
   */
  standings(params: StandingParams): TeamRecord[] {
    const matches = this.repo.matches.filter(
      (m) => m.season === params.season && (!params.competition || normalizeTeamName(m.competition).includes(normalizeTeamName(params.competition))),
    );

    const table = new Map<string, TeamRecord>();

    const get = (team: string): TeamRecord => {
      if (!table.has(team)) {
        table.set(team, {
          team,
          matches: 0,
          wins: 0,
          draws: 0,
          losses: 0,
          goalsFor: 0,
          goalsAgainst: 0,
          points: 0,
        });
      }
      return table.get(team)!;
    };

    for (const m of matches) {
      const home = get(m.homeTeam);
      const away = get(m.awayTeam);

      home.matches++;
      away.matches++;
      home.goalsFor += m.homeGoal;
      home.goalsAgainst += m.awayGoal;
      away.goalsFor += m.awayGoal;
      away.goalsAgainst += m.homeGoal;

      if (m.homeGoal > m.awayGoal) {
        home.wins++;
        away.losses++;
        home.points += 3;
      } else if (m.homeGoal < m.awayGoal) {
        away.wins++;
        home.losses++;
        away.points += 3;
      } else {
        home.draws++;
        away.draws++;
        home.points++;
        away.points++;
      }
    }

    return Array.from(table.values()).sort((a, b) => {
      if (b.points !== a.points) return b.points - a.points;
      const aDiff = a.goalsFor - a.goalsAgainst;
      const bDiff = b.goalsFor - b.goalsAgainst;
      if (bDiff !== aDiff) return bDiff - aDiff;
      return b.goalsFor - a.goalsFor;
    });
  }

  /** Matches with the largest goal-difference margins. */
  biggestWins(limit = 10, competition?: string): Match[] {
    let matches = this.repo.matches.slice();
    if (competition) {
      const q = normalizeTeamName(competition);
      matches = matches.filter((m) => normalizeTeamName(m.competition).includes(q));
    }

    return matches
      .map((m) => ({ m, margin: Math.abs(m.homeGoal - m.awayGoal) }))
      .filter((x) => x.margin > 0)
      .sort((a, b) => b.margin - a.margin || b.m.date.localeCompare(a.m.date))
      .slice(0, limit)
      .map((x) => x.m);
  }

  /** Aggregate goals-per-match average, optionally filtered by competition. */
  averageGoals(competition?: string): { matches: number; totalGoals: number; average: number } {
    let matches = this.repo.matches;
    if (competition) {
      const q = normalizeTeamName(competition);
      matches = matches.filter((m) => normalizeTeamName(m.competition).includes(q));
    }

    const totalGoals = matches.reduce((sum, m) => sum + m.homeGoal + m.awayGoal, 0);
    return {
      matches: matches.length,
      totalGoals,
      average: matches.length ? totalGoals / matches.length : 0,
    };
  }

  /** Home vs away win/draw rates across the dataset. */
  homeAwaySummary(competition?: string): {
    homeWins: number;
    awayWins: number;
    draws: number;
    homeWinRate: number;
    awayWinRate: number;
    drawRate: number;
  } {
    let matches = this.repo.matches.filter((m) => m.homeGoal !== m.awayGoal || m.homeGoal === 0 || m.awayGoal === 0);
    if (competition) {
      const q = normalizeTeamName(competition);
      matches = matches.filter((m) => normalizeTeamName(m.competition).includes(q));
    }

    let homeWins = 0;
    let awayWins = 0;
    let draws = 0;

    for (const m of matches) {
      if (m.homeGoal > m.awayGoal) homeWins++;
      else if (m.awayGoal > m.homeGoal) awayWins++;
      else draws++;
    }

    const total = matches.length;
    return {
      homeWins,
      awayWins,
      draws,
      homeWinRate: total ? homeWins / total : 0,
      awayWinRate: total ? awayWins / total : 0,
      drawRate: total ? draws / total : 0,
    };
  }

  /** Which competitions a given team appears in. */
  competitionsForTeam(team: string): string[] {
    const set = new Set<string>();
    for (const m of this.repo.matches) {
      if (teamMatches(team, m.homeTeam) || teamMatches(team, m.awayTeam)) {
        set.add(m.competition);
      }
    }
    return Array.from(set).sort();
  }
}
