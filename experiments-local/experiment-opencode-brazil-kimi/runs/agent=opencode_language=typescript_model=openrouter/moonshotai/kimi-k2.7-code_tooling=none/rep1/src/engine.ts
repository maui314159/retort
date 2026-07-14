/*
 * Brazilian Soccer MCP Server - Query engine
 *
 * Provides the analytical primitives used by the MCP server to answer
 * natural-language questions about matches, teams, players, and competitions.
 * All methods operate directly on the in-memory DataStore.
 */

import {
  Match,
  Player,
  Standing,
  TeamRecord,
  HeadToHead,
  ExtendedMatchStats
} from './types.js';
import { DataStore } from './loader.js';
import {
  normalizeForSearch,
  normalizeTeamName,
  teamNamesMatch,
  teamNameContains,
  inferResult,
  winnerTeam
} from './normalizer.js';

export interface MatchFilters {
  team?: string;
  homeTeam?: string;
  awayTeam?: string;
  teamA?: string;
  teamB?: string;
  competition?: string;
  season?: number;
  fromDate?: string;
  toDate?: string;
  round?: string;
  stage?: string;
}

export interface PlayerFilters {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  limit?: number;
}

export class QueryEngine {
  constructor(private readonly store: DataStore) {}

  /* ------------------------------------------------------------------ */
  /* Match queries                                                      */
  /* ------------------------------------------------------------------ */

  findMatches(filters: MatchFilters): Match[] {
    let result = this.store.matches;

    if (filters.competition) {
      const target = filters.competition.toLowerCase();
      result = result.filter((m) => m.competition.toLowerCase().includes(target));
    }

    if (filters.season) {
      result = result.filter((m) => m.season === filters.season);
    }

    if (filters.team) {
      const team = filters.team;
      result = result.filter(
        (m) => teamNameContains(m.homeTeam, team) || teamNameContains(m.awayTeam, team)
      );
    }

    if (filters.homeTeam) {
      const homeTeam = filters.homeTeam;
      result = result.filter((m) => teamNameContains(m.homeTeam, homeTeam));
    }

    if (filters.awayTeam) {
      const awayTeam = filters.awayTeam;
      result = result.filter((m) => teamNameContains(m.awayTeam, awayTeam));
    }

    if (filters.teamA && filters.teamB) {
      const teamA = filters.teamA;
      const teamB = filters.teamB;
      result = result.filter(
        (m) =>
          (teamNameContains(m.homeTeam, teamA) && teamNameContains(m.awayTeam, teamB)) ||
          (teamNameContains(m.homeTeam, teamB) && teamNameContains(m.awayTeam, teamA))
      );
    } else if (filters.teamA) {
      const teamA = filters.teamA;
      result = result.filter(
        (m) => teamNameContains(m.homeTeam, teamA) || teamNameContains(m.awayTeam, teamA)
      );
    }

    if (filters.fromDate) {
      result = result.filter((m) => m.date >= filters.fromDate!);
    }

    if (filters.toDate) {
      result = result.filter((m) => m.date <= filters.toDate!);
    }

    if (filters.round) {
      result = result.filter((m) => m.round && normalizeForSearch(m.round).includes(normalizeForSearch(filters.round!)));
    }

    if (filters.stage) {
      result = result.filter(
        (m) => m.stage && m.stage.toLowerCase().includes(filters.stage!.toLowerCase())
      );
    }

    return result;
  }

  findMatchesBetween(teamA: string, teamB: string, filters: MatchFilters = {}): Match[] {
    return this.findMatches({ ...filters, teamA, teamB });
  }

  findLastMatch(teamA: string, teamB?: string): Match | undefined {
    const matches = teamB
      ? this.findMatchesBetween(teamA, teamB)
      : this.findMatches({ team: teamA });
    return matches[0];
  }

  /* ------------------------------------------------------------------ */
  /* Team queries                                                       */
  /* ------------------------------------------------------------------ */

  getTeamRecord(
    team: string,
    filters: MatchFilters = {},
    side: 'home' | 'away' | 'both' = 'both'
  ): TeamRecord {
    const matches = this.findMatches(filters).filter((m) => {
      if (side === 'home') return teamNameContains(m.homeTeam, team);
      if (side === 'away') return teamNameContains(m.awayTeam, team);
      return teamNameContains(m.homeTeam, team) || teamNameContains(m.awayTeam, team);
    });

    let wins = 0;
    let draws = 0;
    let losses = 0;
    let goalsFor = 0;
    let goalsAgainst = 0;

    for (const match of matches) {
      if (match.homeGoal === null || match.awayGoal === null) continue;
      const isHome = teamNameContains(match.homeTeam, team);
      const teamGoals = isHome ? match.homeGoal : match.awayGoal;
      const oppGoals = isHome ? match.awayGoal : match.homeGoal;

      goalsFor += teamGoals;
      goalsAgainst += oppGoals;

      if (teamGoals > oppGoals) wins++;
      else if (teamGoals === oppGoals) draws++;
      else losses++;
    }

    return {
      team: normalizeTeamName(team),
      matches: matches.length,
      wins,
      draws,
      losses,
      goalsFor,
      goalsAgainst,
      points: wins * 3 + draws
    };
  }

  getHeadToHead(teamA: string, teamB: string, filters: MatchFilters = {}): HeadToHead {
    const matches = this.findMatchesBetween(teamA, teamB, filters);
    let teamAWins = 0;
    let teamBWins = 0;
    let draws = 0;
    let teamAGoals = 0;
    let teamBGoals = 0;

    for (const match of matches) {
      if (match.homeGoal === null || match.awayGoal === null) continue;
      const aIsHome = teamNameContains(match.homeTeam, teamA);
      const aGoals = aIsHome ? match.homeGoal : match.awayGoal;
      const bGoals = aIsHome ? match.awayGoal : match.homeGoal;
      teamAGoals += aGoals;
      teamBGoals += bGoals;

      if (aGoals > bGoals) teamAWins++;
      else if (bGoals > aGoals) teamBWins++;
      else draws++;
    }

    return {
      teamA: normalizeTeamName(teamA),
      teamB: normalizeTeamName(teamB),
      teamAWins,
      teamBWins,
      draws,
      teamAGoals,
      teamBGoals,
      matches
    };
  }

  /* ------------------------------------------------------------------ */
  /* Player queries                                                     */
  /* ------------------------------------------------------------------ */

  findPlayers(filters: PlayerFilters): Player[] {
    let result = this.store.players;

    if (filters.name) {
      const target = normalizeForSearch(filters.name);
      result = result.filter((p) => normalizeForSearch(p.name).includes(target));
    }

    if (filters.nationality) {
      const target = filters.nationality.toLowerCase();
      result = result.filter(
        (p) =>
          p.nationality.toLowerCase() === target ||
          p.nationality.toLowerCase().includes(target)
      );
    }

    if (filters.club) {
      const target = filters.club.toLowerCase();
      result = result.filter(
        (p) => p.club && p.club.toLowerCase().includes(target)
      );
    }

    if (filters.position) {
      const target = filters.position.toUpperCase();
      result = result.filter(
        (p) => p.position && p.position.toUpperCase().includes(target)
      );
    }

    if (filters.minOverall) {
      result = result.filter((p) => (p.overall ?? 0) >= filters.minOverall!);
    }

    result = result.sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));

    if (filters.limit && filters.limit > 0) {
      result = result.slice(0, filters.limit);
    }

    return result;
  }

  /* ------------------------------------------------------------------ */
  /* Competition queries                                                */
  /* ------------------------------------------------------------------ */

  calculateStandings(
    competition: string,
    season: number,
    filters: Omit<MatchFilters, 'competition' | 'season'> = {}
  ): Standing[] {
    const matches = this.findMatches({ ...filters, competition, season });
    const map = new Map<string, Standing>();

    for (const match of matches) {
      if (match.homeGoal === null || match.awayGoal === null) continue;
      const home = normalizeTeamName(match.homeTeam);
      const away = normalizeTeamName(match.awayTeam);

      ensureTeam(map, home);
      ensureTeam(map, away);

      const homeStanding = map.get(home)!;
      const awayStanding = map.get(away)!;

      homeStanding.matches++;
      awayStanding.matches++;
      homeStanding.goalsFor += match.homeGoal;
      homeStanding.goalsAgainst += match.awayGoal;
      awayStanding.goalsFor += match.awayGoal;
      awayStanding.goalsAgainst += match.homeGoal;

      if (match.homeGoal > match.awayGoal) {
        homeStanding.wins++;
        homeStanding.points += 3;
        awayStanding.losses++;
      } else if (match.awayGoal > match.homeGoal) {
        awayStanding.wins++;
        awayStanding.points += 3;
        homeStanding.losses++;
      } else {
        homeStanding.draws++;
        awayStanding.draws++;
        homeStanding.points++;
        awayStanding.points++;
      }
    }

    const standings = Array.from(map.values()).sort((a, b) => {
      if (b.points !== a.points) return b.points - a.points;
      const gdA = a.goalsFor - a.goalsAgainst;
      const gdB = b.goalsFor - b.goalsAgainst;
      if (gdB !== gdA) return gdB - gdA;
      if (b.wins !== a.wins) return b.wins - a.wins;
      return b.goalsFor - a.goalsFor;
    });

    standings.forEach((s, idx) => {
      s.position = idx + 1;
      s.goalDifference = s.goalsFor - s.goalsAgainst;
    });

    return standings;
  }

  /* ------------------------------------------------------------------ */
  /* Statistical queries                                                */
  /* ------------------------------------------------------------------ */

  averageGoals(filters: MatchFilters = {}): number {
    const matches = this.findMatches(filters).filter(
      (m) => m.homeGoal !== null && m.awayGoal !== null
    );
    if (matches.length === 0) return 0;
    const total = matches.reduce((sum, m) => sum + m.homeGoal! + m.awayGoal!, 0);
    return total / matches.length;
  }

  homeWinRate(filters: MatchFilters = {}): number {
    const matches = this.findMatches(filters).filter(
      (m) => m.homeGoal !== null && m.awayGoal !== null
    );
    if (matches.length === 0) return 0;
    const homeWins = matches.filter((m) => m.homeGoal! > m.awayGoal!).length;
    return homeWins / matches.length;
  }

  biggestWins(filters: MatchFilters = {}, limit = 10): Match[] {
    return this.findMatches(filters)
      .filter((m) => m.homeGoal !== null && m.awayGoal !== null)
      .sort((a, b) => {
        const diffA = Math.abs(a.homeGoal! - a.awayGoal!);
        const diffB = Math.abs(b.homeGoal! - b.awayGoal!);
        return diffB - diffA;
      })
      .slice(0, limit);
  }

  bestAwayRecord(filters: MatchFilters = {}): TeamRecord[] {
    const matches = this.findMatches(filters).filter(
      (m) => m.homeGoal !== null && m.awayGoal !== null
    );
    const map = new Map<string, TeamRecord>();

    for (const match of matches) {
      const away = normalizeTeamName(match.awayTeam);
      if (!map.has(away)) {
        map.set(away, emptyRecord(away));
      }
      const record = map.get(away)!;
      record.matches++;
      record.goalsFor += match.awayGoal!;
      record.goalsAgainst += match.homeGoal!;
      if (match.awayGoal! > match.homeGoal!) {
        record.wins++;
        record.points += 3;
      } else if (match.awayGoal! === match.homeGoal!) {
        record.draws++;
        record.points++;
      } else {
        record.losses++;
      }
    }

    return Array.from(map.values()).sort(
      (a, b) => b.points / b.matches - a.points / a.matches
    );
  }

  topScorerTeams(filters: MatchFilters = {}, limit = 10): TeamRecord[] {
    const matches = this.findMatches(filters).filter(
      (m) => m.homeGoal !== null && m.awayGoal !== null
    );
    const map = new Map<string, TeamRecord>();

    for (const match of matches) {
      [match.homeTeam, match.awayTeam].forEach((team) => {
        const key = normalizeTeamName(team);
        if (!map.has(key)) {
          map.set(key, emptyRecord(key));
        }
        const record = map.get(key)!;
        const goals = teamNamesMatch(team, match.homeTeam) ? match.homeGoal! : match.awayGoal!;
        record.goalsFor += goals;
      });
    }

    return Array.from(map.values())
      .sort((a, b) => b.goalsFor - a.goalsFor)
      .slice(0, limit);
  }

  playerClubsSummary(clubFilter?: string): Map<string, { count: number; average: number }> {
    const players = this.findPlayers({ club: clubFilter });
    const map = new Map<string, number[]>();

    for (const player of players) {
      if (!player.club) continue;
      const key = player.club;
      if (!map.has(key)) map.set(key, []);
      if (player.overall !== undefined) {
        map.get(key)!.push(player.overall);
      }
    }

    const summary = new Map<string, { count: number; average: number }>();
    for (const [club, ratings] of map.entries()) {
      const average =
        ratings.length > 0 ? ratings.reduce((a, b) => a + b, 0) / ratings.length : 0;
      summary.set(club, { count: ratings.length, average: Math.round(average * 10) / 10 });
    }
    return summary;
  }

  /* ------------------------------------------------------------------ */
  /* Relationships / metadata                                           */
  /* ------------------------------------------------------------------ */

  listCompetitions(team?: string): string[] {
    const matches = team ? this.findMatches({ team }) : this.store.matches;
    return Array.from(new Set(matches.map((m) => m.competition).filter(Boolean))).sort();
  }

  listSeasons(competition?: string): number[] {
    const matches = competition
      ? this.findMatches({ competition })
      : this.store.matches;
    return Array.from(new Set(matches.map((m) => m.season).filter((s) => s > 0))).sort(
      (a, b) => a - b
    );
  }
}

function emptyRecord(team: string): TeamRecord {
  return {
    team,
    matches: 0,
    wins: 0,
    draws: 0,
    losses: 0,
    goalsFor: 0,
    goalsAgainst: 0,
    points: 0
  };
}

function ensureTeam(map: Map<string, Standing>, team: string): void {
  const key = normalizeTeamName(team);
  if (!map.has(key)) {
    map.set(key, {
      ...emptyRecord(key),
      position: undefined,
      goalDifference: 0
    });
  }
}
