import { Match, Player, StandingRow, TeamStats } from "./types.js";
import { normalizeTeamName, teamMatches } from "./normalize.js";

export interface MatchFilters {
  team?: string;
  home?: string;
  away?: string;
  teamA?: string;
  teamB?: string;
  competition?: string;
  season?: number;
  fromDate?: string;
  toDate?: string;
  round?: string;
  stage?: string;
  limit?: number;
}

export interface PlayerFilters {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  limit?: number;
  minOverall?: number;
}

export class SoccerEngine {
  constructor(
    public matches: Match[],
    public players: Player[],
  ) {}

  findMatches(filters: MatchFilters = {}): Match[] {
    let result = this.matches.filter((m) => this.matchFilter(m, filters));

    if (filters.teamA && filters.teamB) {
      result = result.filter(
        (m) =>
          (teamMatches(m.home, filters.teamA!) && teamMatches(m.away, filters.teamB!)) ||
          (teamMatches(m.home, filters.teamB!) && teamMatches(m.away, filters.teamA!)),
      );
    }

    result.sort((a, b) => b.date.localeCompare(a.date));

    if (filters.limit && filters.limit > 0) {
      result = result.slice(0, filters.limit);
    }

    return result;
  }

  findMatchesBetween(teamA: string, teamB: string, filters: Omit<MatchFilters, "teamA" | "teamB"> = {}): Match[] {
    return this.findMatches({ ...filters, teamA, teamB });
  }

  getTeamStats(team: string, filters: Omit<MatchFilters, "team"> = {}): TeamStats {
    const teamMatchesList = this.matches.filter((m) => this.matchFilter(m, filters) && this.teamInMatch(m, team));

    let wins = 0;
    let draws = 0;
    let losses = 0;
    let goalsFor = 0;
    let goalsAgainst = 0;

    const homeStats = { matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0 };
    const awayStats = { matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0 };

    for (const m of teamMatchesList) {
      const isHome = teamMatches(m.home, team);
      const teamGoals = isHome ? m.homeGoals : m.awayGoals;
      const opponentGoals = isHome ? m.awayGoals : m.homeGoals;

      if (teamGoals === null || opponentGoals === null) continue;

      goalsFor += teamGoals;
      goalsAgainst += opponentGoals;

      if (isHome) {
        homeStats.matches++;
        homeStats.goalsFor += teamGoals;
        homeStats.goalsAgainst += opponentGoals;
      } else {
        awayStats.matches++;
        awayStats.goalsFor += teamGoals;
        awayStats.goalsAgainst += opponentGoals;
      }

      if (teamGoals > opponentGoals) {
        wins++;
        if (isHome) homeStats.wins++;
        else awayStats.wins++;
      } else if (teamGoals === opponentGoals) {
        draws++;
        if (isHome) homeStats.draws++;
        else awayStats.draws++;
      } else {
        losses++;
        if (isHome) homeStats.losses++;
        else awayStats.losses++;
      }
    }

    return {
      team: normalizeTeamName(team),
      matches: teamMatchesList.length,
      wins,
      draws,
      losses,
      goalsFor,
      goalsAgainst,
      winRate: teamMatchesList.length ? (wins / teamMatchesList.length) * 100 : 0,
      homeRecord: homeStats,
      awayRecord: awayStats,
    };
  }

  getHeadToHead(teamA: string, teamB: string, filters: Omit<MatchFilters, "teamA" | "teamB"> = {}): {
    matches: Match[];
    winsA: number;
    winsB: number;
    draws: number;
  } {
    const matches = this.findMatchesBetween(teamA, teamB, filters);
    let winsA = 0;
    let winsB = 0;
    let draws = 0;

    for (const m of matches) {
      if (m.homeGoals === null || m.awayGoals === null) continue;
      if (teamMatches(m.home, teamA)) {
        if (m.homeGoals > m.awayGoals) winsA++;
        else if (m.homeGoals < m.awayGoals) winsB++;
        else draws++;
      } else {
        if (m.awayGoals > m.homeGoals) winsA++;
        else if (m.awayGoals < m.homeGoals) winsB++;
        else draws++;
      }
    }

    return { matches, winsA, winsB, draws };
  }

  getStandings(season: number, competition?: string): StandingRow[] {
    const filtered = this.matches.filter(
      (m) => m.season === season && (!competition || this.competitionMatches(m.competition, competition)) && m.homeGoals !== null && m.awayGoals !== null,
    );

    const map = new Map<string, StandingRow>();

    for (const m of filtered) {
      const home = m.home;
      const away = m.away;
      const hg = m.homeGoals!;
      const ag = m.awayGoals!;

      this.addStanding(map, home, hg, ag);
      this.addStanding(map, away, ag, hg);
    }

    const rows = Array.from(map.values());
    rows.sort((a, b) => b.points - a.points || b.goalDifference - a.goalDifference || b.goalsFor - a.goalsFor);
    rows.forEach((r, i) => (r.rank = i + 1));

    return rows;
  }

  getTopScorers(season?: number, competition?: string, limit = 10): { team: string; goalsFor: number }[] {
    const filtered = this.matches.filter(
      (m) =>
        m.homeGoals !== null &&
        m.awayGoals !== null &&
        (!season || m.season === season) &&
        (!competition || this.competitionMatches(m.competition, competition)),
    );

    const map = new Map<string, number>();
    for (const m of filtered) {
      map.set(m.home, (map.get(m.home) || 0) + m.homeGoals!);
      map.set(m.away, (map.get(m.away) || 0) + m.awayGoals!);
    }

    return Array.from(map.entries())
      .map(([team, goalsFor]) => ({ team, goalsFor }))
      .sort((a, b) => b.goalsFor - a.goalsFor)
      .slice(0, limit);
  }

  getBiggestWins(limit = 10, filters: MatchFilters = {}): Match[] {
    return this.matches
      .filter((m) => this.matchFilter(m, filters) && m.homeGoals !== null && m.awayGoals !== null)
      .map((m) => ({ m, diff: Math.abs(m.homeGoals! - m.awayGoals!) }))
      .sort((a, b) => b.diff - a.diff)
      .map((x) => x.m)
      .slice(0, limit);
  }

  getAverageGoals(filters: MatchFilters = {}): { totalMatches: number; averageGoals: number; homeWinRate: number } {
    const filtered = this.matches.filter(
      (m) => this.matchFilter(m, filters) && m.homeGoals !== null && m.awayGoals !== null,
    );
    const totalGoals = filtered.reduce((sum, m) => sum + m.homeGoals! + m.awayGoals!, 0);
    const homeWins = filtered.filter((m) => m.homeGoals! > m.awayGoals!).length;

    return {
      totalMatches: filtered.length,
      averageGoals: filtered.length ? totalGoals / filtered.length : 0,
      homeWinRate: filtered.length ? (homeWins / filtered.length) * 100 : 0,
    };
  }

  getPlayers(filters: PlayerFilters = {}): Player[] {
    let result = this.players;

    if (filters.name) {
      const term = filters.name.toLowerCase();
      result = result.filter((p) => p.name.toLowerCase().includes(term));
    }

    if (filters.nationality) {
      const term = filters.nationality.toLowerCase();
      result = result.filter((p) => (p.nationality || "").toLowerCase().includes(term));
    }

    if (filters.club) {
      const term = filters.club.toLowerCase();
      result = result.filter((p) => (p.club || "").toLowerCase().includes(term));
    }

    if (filters.position) {
      const term = filters.position.toUpperCase();
      result = result.filter((p) => (p.position || "").toUpperCase().includes(term));
    }

    if (filters.minOverall !== undefined) {
      result = result.filter((p) => (p.overall || 0) >= filters.minOverall!);
    }

    result.sort((a, b) => (b.overall || 0) - (a.overall || 0));

    if (filters.limit && filters.limit > 0) {
      result = result.slice(0, filters.limit);
    }

    return result;
  }

  getCompetitionsForTeam(team: string): string[] {
    const competitions = new Set<string>();
    for (const m of this.matches) {
      if (this.teamInMatch(m, team)) competitions.add(m.competition);
    }
    return Array.from(competitions).sort();
  }

  getDerbies(filters: MatchFilters = {}): Match[] {
    const rivalryPairs = [
      ["Flamengo", "Fluminense"],
      ["Flamengo", "Vasco"],
      ["Flamengo", "Botafogo"],
      ["Fluminense", "Vasco"],
      ["Corinthians", "Palmeiras"],
      ["Corinthians", "Sao Paulo"],
      ["Corinthians", "Santos"],
      ["Palmeiras", "Sao Paulo"],
      ["Palmeiras", "Santos"],
      ["Sao Paulo", "Santos"],
      ["Gremio", "Internacional"],
      ["Atletico Mineiro", "Cruzeiro"],
      ["Athletico Paranaense", "Coritiba"],
      ["Bahia", "Vitoria"],
      ["Ceara", "Fortaleza"],
    ];

    return this.matches.filter(
      (m) =>
        this.matchFilter(m, filters) &&
        rivalryPairs.some(([a, b]) => (teamMatches(m.home, a) && teamMatches(m.away, b)) || (teamMatches(m.home, b) && teamMatches(m.away, a))),
    );
  }

  private matchFilter(m: Match, filters: MatchFilters): boolean {
    if (filters.competition && !this.competitionMatches(m.competition, filters.competition)) return false;
    if (filters.season !== undefined && m.season !== filters.season) return false;
    if (filters.fromDate && m.date < filters.fromDate) return false;
    if (filters.toDate && m.date > filters.toDate) return false;
    if (filters.round !== undefined && String(m.round) !== String(filters.round)) return false;
    if (filters.stage !== undefined && m.stage !== filters.stage) return false;
    if (filters.team && !this.teamInMatch(m, filters.team)) return false;
    if (filters.home && !teamMatches(m.home, filters.home)) return false;
    if (filters.away && !teamMatches(m.away, filters.away)) return false;
    return true;
  }

  private teamInMatch(m: Match, team: string): boolean {
    return teamMatches(m.home, team) || teamMatches(m.away, team);
  }

  private competitionMatches(actual: string, query: string): boolean {
    return actual.toLowerCase().includes(query.toLowerCase()) || query.toLowerCase().includes(actual.toLowerCase());
  }

  private addStanding(map: Map<string, StandingRow>, team: string, gf: number, ga: number): void {
    const row = map.get(team) || {
      rank: 0,
      team,
      points: 0,
      wins: 0,
      draws: 0,
      losses: 0,
      goalsFor: 0,
      goalsAgainst: 0,
      goalDifference: 0,
    };

    row.goalsFor += gf;
    row.goalsAgainst += ga;
    row.goalDifference = row.goalsFor - row.goalsAgainst;

    if (gf > ga) {
      row.wins++;
      row.points += 3;
    } else if (gf === ga) {
      row.draws++;
      row.points += 1;
    } else {
      row.losses++;
    }

    map.set(team, row);
  }
}
