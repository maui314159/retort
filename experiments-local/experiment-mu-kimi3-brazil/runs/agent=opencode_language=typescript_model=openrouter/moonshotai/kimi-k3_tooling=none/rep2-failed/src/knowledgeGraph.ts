/**
 * In-memory knowledge graph over the loaded datasets.
 *
 * Nodes: teams, players, competitions, seasons, matches.
 * Edges (indexes): team->matches, competition->matches, season->matches,
 * club->players, nationality->players, name->players.
 *
 * All query methods are pure lookups over these indexes, so simple lookups
 * are O(result size) and aggregates are O(matches in scope).
 */

import type {
  LoadedData,
  Match,
  MatchFilter,
  Player,
  PlayerFilter,
  StandingRow,
  TeamRecord,
} from "./types.js";
import {
  competitionMatches,
  stripAccents,
  teamNamesMatch,
} from "./normalize.js";
import { canonicalTeamKey } from "./teams.js";

export class KnowledgeGraph {
  readonly matches: Match[];
  readonly players: Player[];

  /** teamKey -> matches involving that team (home or away). */
  private readonly matchesByTeam = new Map<string, Match[]>();
  /** competition -> matches */
  private readonly matchesByCompetition = new Map<string, Match[]>();
  /** All distinct team keys, for fuzzy resolution. */
  private readonly teamKeys = new Set<string>();
  /** club lowercase -> players */
  private readonly playersByClub = new Map<string, Player[]>();
  /** nationality lowercase -> players */
  private readonly playersByNationality = new Map<string, Player[]>();
  /** normalized player name -> players */
  private readonly playersByName = new Map<string, Player[]>();

  constructor(data: LoadedData) {
    // The source datasets overlap (e.g. Brasileirão 2019 appears in three
    // files). Deduplicate fixtures so aggregates (standings, records) are
    // not double-counted. Two records are the same fixture when the
    // canonical home/away keys match and the dates are at most 1 day apart
    // (one source records late kick-offs on the following calendar day).
    const DAY_MS = 24 * 60 * 60 * 1000;
    const byPair = new Map<string, number[]>();
    const undated = new Set<string>();
    this.matches = data.matches.filter((m) => {
      const pair = `${m.homeKey}|${m.awayKey}`;
      if (m.date) {
        const day = Date.parse(`${m.date}T00:00:00Z`) / DAY_MS;
        const days = byPair.get(pair);
        if (days && days.some((d) => Math.abs(d - day) <= 1)) return false;
        if (days) days.push(day);
        else byPair.set(pair, [day]);
        return true;
      }
      const key = `${pair}|s${m.season ?? "?"}r${m.round ?? "?"}`;
      if (undated.has(key)) return false;
      undated.add(key);
      return true;
    });
    this.players = data.players;

    for (const m of this.matches) {
      for (const key of [m.homeKey, m.awayKey]) {
        if (!key) continue;
        this.teamKeys.add(key);
        let arr = this.matchesByTeam.get(key);
        if (!arr) this.matchesByTeam.set(key, (arr = []));
        arr.push(m);
      }
      let byComp = this.matchesByCompetition.get(m.competition);
      if (!byComp) this.matchesByCompetition.set(m.competition, (byComp = []));
      byComp.push(m);
    }

    for (const p of this.players) {
      const clubKey = p.club.toLowerCase();
      if (clubKey) {
        let arr = this.playersByClub.get(clubKey);
        if (!arr) this.playersByClub.set(clubKey, (arr = []));
        arr.push(p);
      }
      const natKey = p.nationality.toLowerCase();
      if (natKey) {
        let arr = this.playersByNationality.get(natKey);
        if (!arr) this.playersByNationality.set(natKey, (arr = []));
        arr.push(p);
      }
      const nameKey = stripAccents(p.name).toLowerCase();
      if (nameKey) {
        let arr = this.playersByName.get(nameKey);
        if (!arr) this.playersByName.set(nameKey, (arr = []));
        arr.push(p);
      }
    }
  }

  /** List of competitions present in the data. */
  competitions(): string[] {
    return [...this.matchesByCompetition.keys()].sort();
  }

  /**
   * Resolve a user-supplied team name to the set of team keys it may refer
   * to. Canonical exact resolution first, fuzzy fallback second.
   */
  resolveTeamKeys(query: string): string[] {
    const exact = canonicalTeamKey(query);
    if (this.teamKeys.has(exact)) return [exact];

    const out = new Set<string>();
    for (const key of this.teamKeys) {
      if (teamNamesMatch(key, query)) out.add(key);
    }
    return [...out];
  }

  /** Display name for a team key: most frequent raw name among its matches. */
  teamDisplayName(teamKey: string): string {
    const counts = new Map<string, number>();
    for (const m of this.matchesByTeam.get(teamKey) ?? []) {
      const name = m.homeKey === teamKey ? m.homeTeam : m.awayTeam;
      counts.set(name, (counts.get(name) ?? 0) + 1);
    }
    let best = teamKey;
    let bestN = -1;
    for (const [name, n] of counts) if (n > bestN) { best = name; bestN = n; }
    return best;
  }

  private matchInScope(m: Match, filter: MatchFilter): boolean {
    if (filter.competition && !competitionMatches(filter.competition, m.competition)) return false;
    if (filter.season !== undefined && m.season !== filter.season) return false;
    if (filter.dateFrom && (!m.date || m.date < filter.dateFrom)) return false;
    if (filter.dateTo && (!m.date || m.date > filter.dateTo)) return false;
    return true;
  }

  /** Search matches by team / pair of teams / competition / season / dates. */
  findMatches(filter: MatchFilter): Match[] {
    let candidates: Match[];
    if (filter.teamA && filter.teamB) {
      const keysA = this.resolveTeamKeys(filter.teamA);
      const keysB = this.resolveTeamKeys(filter.teamB);
      const setA = new Set(keysA);
      const setB = new Set(keysB);
      const pool = keysA.length
        ? keysA.flatMap((k) => this.matchesByTeam.get(k) ?? [])
        : this.matches;
      candidates = pool.filter((m) => {
        const homeInA = setA.has(m.homeKey);
        const awayInA = setA.has(m.awayKey);
        const homeInB = setB.has(m.homeKey);
        const awayInB = setB.has(m.awayKey);
        return (homeInA && awayInB) || (homeInB && awayInA);
      });
    } else {
      const team = filter.team ?? filter.teamA ?? filter.teamB;
      if (team) {
        const keys = this.resolveTeamKeys(team);
        candidates = keys.flatMap((k) => this.matchesByTeam.get(k) ?? []);
      } else if (filter.competition) {
        candidates = this.matches.filter((m) =>
          competitionMatches(filter.competition!, m.competition),
        );
      } else {
        candidates = this.matches;
      }
    }

    const seen = new Set<string>();
    const out: Match[] = [];
    for (const m of candidates) {
      if (seen.has(m.id)) continue;
      seen.add(m.id);
      if (!this.matchInScope(m, filter)) continue;
      out.push(m);
    }
    out.sort((a, b) => (a.date ?? "").localeCompare(b.date ?? ""));
    const limit = filter.limit ?? 50;
    return out.slice(0, limit);
  }

  /** Most recent dated match between two teams, or null. */
  lastMatch(teamA: string, teamB: string): Match | null {
    const matches = this.findMatches({ teamA, teamB, limit: 10000 }).filter((m) => m.date);
    if (!matches.length) return null;
    return matches[matches.length - 1];
  }

  /** Head-to-head summary between two teams. */
  headToHead(teamA: string, teamB: string) {
    const matches = this.findMatches({ teamA, teamB, limit: 10000 });
    let winsA = 0;
    let winsB = 0;
    let draws = 0;
    for (const m of matches) {
      if (m.homeGoals === null || m.awayGoals === null) continue;
      if (m.homeGoals === m.awayGoals) {
        draws++;
      } else {
        const homeIsA = teamNamesMatch(m.homeTeam, teamA);
        const homeWon = m.homeGoals > m.awayGoals;
        if ((homeIsA && homeWon) || (!homeIsA && !homeWon)) winsA++;
        else winsB++;
      }
    }
    return { teamA, teamB, matches, winsA, winsB, draws, total: matches.length };
  }

  /** Win/draw/loss record for a team, optionally scoped and venue-split. */
  teamStats(
    team: string,
    opts: { season?: number; competition?: string; venue?: "home" | "away" | "all" } = {},
  ): TeamRecord & { team: string } {
    const keys = this.resolveTeamKeys(team);
    const rec: TeamRecord = { matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0 };
    const venue = opts.venue ?? "all";
    const keySet = new Set(keys);

    for (const key of keys) {
      for (const m of this.matchesByTeam.get(key) ?? []) {
        if (opts.season !== undefined && m.season !== opts.season) continue;
        if (opts.competition && !competitionMatches(opts.competition, m.competition)) continue;
        if (m.homeGoals === null || m.awayGoals === null) continue;

        const isHome = m.homeKey === key || (keySet.has(m.homeKey) && !keySet.has(m.awayKey));
        if (venue === "home" && !isHome) continue;
        if (venue === "away" && isHome) continue;

        const gf = isHome ? m.homeGoals : m.awayGoals;
        const ga = isHome ? m.awayGoals : m.homeGoals;
        rec.matches++;
        rec.goalsFor += gf;
        rec.goalsAgainst += ga;
        if (gf > ga) rec.wins++;
        else if (gf < ga) rec.losses++;
        else rec.draws++;
      }
    }
    return { team, ...rec };
  }

  /** League table computed from match results (3 pts for a win). */
  standings(season: number, competition = "Brasileirão Série A"): StandingRow[] {
    const table = new Map<string, StandingRow>();
    const scoped = this.matches.filter(
      (m) =>
        m.season === season &&
        competitionMatches(competition, m.competition) &&
        m.homeGoals !== null &&
        m.awayGoals !== null,
    );
    for (const m of scoped) {
      for (const side of ["home", "away"] as const) {
        const key = side === "home" ? m.homeKey : m.awayKey;
        if (!key) continue;
        let row = table.get(key);
        if (!row) {
          row = {
            team: side === "home" ? m.homeTeam : m.awayTeam,
            teamKey: key,
            played: 0, wins: 0, draws: 0, losses: 0,
            goalsFor: 0, goalsAgainst: 0, goalDifference: 0, points: 0,
          };
          table.set(key, row);
        }
        const gf = side === "home" ? m.homeGoals! : m.awayGoals!;
        const ga = side === "home" ? m.awayGoals! : m.homeGoals!;
        row.played++;
        row.goalsFor += gf;
        row.goalsAgainst += ga;
        if (gf > ga) { row.wins++; row.points += 3; }
        else if (gf < ga) row.losses++;
        else { row.draws++; row.points += 1; }
        row.goalDifference = row.goalsFor - row.goalsAgainst;
      }
    }
    return [...table.values()].sort(
      (a, b) =>
        b.points - a.points ||
        b.wins - a.wins ||
        b.goalDifference - a.goalDifference ||
        b.goalsFor - a.goalsFor,
    );
  }

  /** Teams that scored the most goals in a season/competition. */
  topScoringTeams(season?: number, competition?: string, limit = 10) {
    const totals = new Map<string, { team: string; goals: number }>();
    for (const m of this.matches) {
      if (season !== undefined && m.season !== season) continue;
      if (competition && !competitionMatches(competition, m.competition)) continue;
      if (m.homeGoals === null || m.awayGoals === null) continue;
      for (const [key, team, goals] of [
        [m.homeKey, m.homeTeam, m.homeGoals],
        [m.awayKey, m.awayTeam, m.awayGoals],
      ] as const) {
        if (!key) continue;
        const cur = totals.get(key) ?? { team, goals: 0 };
        cur.goals += goals;
        totals.set(key, cur);
      }
    }
    return [...totals.values()].sort((a, b) => b.goals - a.goals).slice(0, limit);
  }

  /** Competitions a team appears in, with match counts. */
  teamCompetitions(team: string): { competition: string; matches: number }[] {
    const keys = this.resolveTeamKeys(team);
    const counts = new Map<string, number>();
    for (const key of keys) {
      for (const m of this.matchesByTeam.get(key) ?? []) {
        counts.set(m.competition, (counts.get(m.competition) ?? 0) + 1);
      }
    }
    return [...counts.entries()]
      .map(([competition, matches]) => ({ competition, matches }))
      .sort((a, b) => b.matches - a.matches);
  }

  /** Biggest wins by margin, then by goals scored. */
  biggestWins(filter: { competition?: string; season?: number } = {}, limit = 10): Match[] {
    return this.matches
      .filter((m) => {
        if (m.homeGoals === null || m.awayGoals === null) return false;
        if (filter.season !== undefined && m.season !== filter.season) return false;
        if (filter.competition && !competitionMatches(filter.competition, m.competition)) return false;
        return true;
      })
      .map((m) => ({ m, margin: Math.abs(m.homeGoals! - m.awayGoals!), total: m.homeGoals! + m.awayGoals! }))
      .sort((a, b) => b.margin - a.margin || b.total - a.total || (a.m.date ?? "").localeCompare(b.m.date ?? ""))
      .slice(0, limit)
      .map((x) => x.m);
  }

  /** Aggregate scoring stats: averages, home win rate, etc. */
  goalsStats(filter: { competition?: string; season?: number; team?: string } = {}) {
    const matches = filter.team
      ? this.findMatches({ team: filter.team, competition: filter.competition, season: filter.season, limit: 100000 })
      : this.matches.filter((m) => {
          if (filter.season !== undefined && m.season !== filter.season) return false;
          if (filter.competition && !competitionMatches(filter.competition, m.competition)) return false;
          return true;
        });
    let played = 0;
    let goals = 0;
    let homeWins = 0;
    let awayWins = 0;
    let draws = 0;
    for (const m of matches) {
      if (m.homeGoals === null || m.awayGoals === null) continue;
      played++;
      goals += m.homeGoals + m.awayGoals;
      if (m.homeGoals > m.awayGoals) homeWins++;
      else if (m.homeGoals < m.awayGoals) awayWins++;
      else draws++;
    }
    return {
      matches: played,
      totalGoals: goals,
      avgGoalsPerMatch: played ? goals / played : 0,
      homeWinRate: played ? homeWins / played : 0,
      awayWinRate: played ? awayWins / played : 0,
      drawRate: played ? draws / played : 0,
    };
  }

  /** Player search with name/nationality/club/position/rating filters. */
  searchPlayers(filter: PlayerFilter): Player[] {
    let candidates: Player[] = this.players;

    if (filter.nationality) {
      const natKey = stripAccents(filter.nationality).toLowerCase();
      candidates = candidates.filter(
        (p) => stripAccents(p.nationality).toLowerCase() === natKey,
      );
    }
    if (filter.club) {
      const clubKeys = this.resolveTeamKeys(filter.club);
      const clubNorms = new Set([
        ...clubKeys,
        canonicalTeamKey(filter.club),
        stripAccents(filter.club).toLowerCase().trim(),
      ]);
      candidates = candidates.filter((p) => {
        const pc = stripAccents(p.club).toLowerCase().trim();
        const pcNorm = canonicalTeamKey(p.club);
        if (clubNorms.has(pc) || clubNorms.has(pcNorm)) return true;
        // substring fallback both directions, e.g. "Flamengo" ~ "CR Flamengo"
        for (const c of clubNorms) {
          if (c.length >= 5 && (pc.includes(c) || pcNorm.includes(c) || (c.includes(pcNorm) && pcNorm.length >= 5))) return true;
        }
        return false;
      });
    }
    if (filter.name) {
      const q = stripAccents(filter.name).toLowerCase().trim();
      candidates = candidates.filter((p) =>
        stripAccents(p.name).toLowerCase().includes(q),
      );
    }
    if (filter.position) {
      const q = filter.position.toUpperCase().trim();
      candidates = candidates.filter((p) => p.position.toUpperCase().includes(q));
    }
    if (filter.minOverall !== undefined) {
      candidates = candidates.filter((p) => (p.overall ?? 0) >= filter.minOverall!);
    }

    const sorted = [...candidates].sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
    return sorted.slice(0, filter.limit ?? 20);
  }

  /** Count + average rating of players grouped by club (for summaries). */
  playersByClubSummary(opts: { nationality?: string; brazilianClubsOnly?: boolean } = {}) {
    const nat = opts.nationality ? stripAccents(opts.nationality).toLowerCase() : null;
    const byClub = new Map<string, { count: number; total: number }>();
    for (const p of this.players) {
      if (nat && stripAccents(p.nationality).toLowerCase() !== nat) continue;
      if (!p.club) continue;
      if (opts.brazilianClubsOnly) {
        const clubKey = canonicalTeamKey(p.club);
        if (!this.teamKeys.has(clubKey)) continue;
      }
      const cur = byClub.get(p.club) ?? { count: 0, total: 0 };
      cur.count++;
      cur.total += p.overall ?? 0;
      byClub.set(p.club, cur);
    }
    return [...byClub.entries()]
      .map(([club, v]) => ({ club, players: v.count, avgOverall: v.count ? v.total / v.count : 0 }))
      .sort((a, b) => b.players - a.players);
  }
}

/** Build a KnowledgeGraph from the on-disk datasets (with a simple cache). */
let cached: Promise<KnowledgeGraph> | null = null;
export function getGraph(): Promise<KnowledgeGraph> {
  if (!cached) {
    cached = import("./dataLoader.js").then(({ loadAll }) => loadAll().then((d) => new KnowledgeGraph(d)));
  }
  return cached;
}
