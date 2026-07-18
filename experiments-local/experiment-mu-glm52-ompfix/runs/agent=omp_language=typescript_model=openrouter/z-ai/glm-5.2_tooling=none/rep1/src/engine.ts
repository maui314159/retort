/**
 * brazilian-soccer-mcp — query engine
 *
 * Context block
 * ============
 * See src/types.ts for the top-level project context block.
 *
 * The `SoccerDatabase` holds the loaded, normalised match + player records
 * and answers the structured queries that back the MCP tools:
 *   • findMatches       — filter by team(s), competition, season, date range.
 *   • teamStats         — W/D/L, goals, home/away split, for a team/season.
 *   • headToHead        — pairwise record + match list.
 *   • playerSearch      — name/nationality/club filters, sorted by rating.
 *   • standings         — computed league table for a competition+season.
 *   • biggestWins       — largest goal-difference victories.
 *   • averageGoals      — mean goals-per-match and home-win rate.
 *   • competitionsFor   — distinct competitions a team appears in.
 *   • lastMatchBetween   — most recent fixture between two teams.
 *
 * All filtering uses the tolerant `teamsMatch` helper so "Palmeiras",
 * "Palmeiras-SP" and "São Paulo" vs "São Paulo FC" all resolve correctly.
 */

import type {
  HeadToHead,
  MatchRecord,
  PlayerRecord,
  StandingRow,
  TeamStats,
} from "./types.js";
import { teamsMatch } from "./normalize.js";

export interface MatchFilter {
  team?: string;
  opponent?: string;
  competition?: string;
  season?: number;
  fromDate?: string; // YYYY-MM-DD inclusive
  toDate?: string; // YYYY-MM-DD inclusive
  limit?: number;
}

export class SoccerDatabase {
  constructor(
    public readonly matches: MatchRecord[],
    public readonly players: PlayerRecord[],
  ) {}

  /** All matches involving `team` (home or away). */
  matchesForTeam(team: string): MatchRecord[] {
    return this.matches.filter(
      (m) => teamsMatch(m.homeTeam, team) || teamsMatch(m.awayTeam, team),
    );
  }

  /** General match filter. */
  findMatches(filter: MatchFilter): MatchRecord[] {
    let rows = this.matches;
    if (filter.team) {
      rows = rows.filter(
        (m) =>
          teamsMatch(m.homeTeam, filter.team!) ||
          teamsMatch(m.awayTeam, filter.team!),
      );
    }
    if (filter.opponent) {
      rows = rows.filter(
        (m) =>
          teamsMatch(m.homeTeam, filter.opponent!) ||
          teamsMatch(m.awayTeam, filter.opponent!),
      );
    }
    if (filter.team && filter.opponent) {
      rows = rows.filter(
        (m) =>
          (teamsMatch(m.homeTeam, filter.team!) &&
            teamsMatch(m.awayTeam, filter.opponent!)) ||
          (teamsMatch(m.homeTeam, filter.opponent!) &&
            teamsMatch(m.awayTeam, filter.team!)),
      );
    }
    if (filter.competition) {
      const c = filter.competition.toLowerCase();
      rows = rows.filter((m) => m.competition.toLowerCase().includes(c));
    }
    if (filter.season != null) {
      rows = rows.filter((m) => m.season === filter.season);
    }
    if (filter.fromDate) {
      rows = rows.filter((m) => (m.date ?? "") >= filter.fromDate!);
    }
    if (filter.toDate) {
      rows = rows.filter((m) => (m.date ?? "") <= filter.toDate!);
    }
    rows = rows
      .slice()
      .sort((a, b) => (b.date ?? "").localeCompare(a.date ?? ""));
    if (filter.limit != null) rows = rows.slice(0, filter.limit);
    return rows;
  }

  /** Most recent fixture between two teams (any direction), or null. */
  lastMatchBetween(teamA: string, teamB: string): MatchRecord | null {
    const rows = this.findMatches({ team: teamA, opponent: teamB });
    return rows[0] ?? null;
  }

  /** Aggregated stats for a team, optionally restricted to a season. */
  teamStats(team: string, season?: number): TeamStats {
    let rows = this.matchesForTeam(team);
    if (season != null) rows = rows.filter((m) => m.season === season);

    const empty = () => ({
      matches: 0,
      wins: 0,
      draws: 0,
      losses: 0,
      goalsFor: 0,
      goalsAgainst: 0,
      points: 0,
    });
    const total = empty();
    const home = empty();
    const away = empty();

    for (const m of rows) {
      const isHome = teamsMatch(m.homeTeam, team);
      const isAway = teamsMatch(m.awayTeam, team);
      if (!isHome && !isAway) continue;
      const own = isHome ? m.homeGoal : m.awayGoal;
      const opp = isHome ? m.awayGoal : m.homeGoal;
      if (own == null || opp == null) continue;
      const venue = isHome ? home : away;
      venue.matches++;
      venue.goalsFor += own;
      venue.goalsAgainst += opp;
      if (own > opp) {
        venue.wins++;
        venue.points += 3;
      } else if (own === opp) {
        venue.draws++;
        venue.points += 1;
      } else {
        venue.losses++;
      }
    }
    for (const v of [home, away]) {
      total.matches += v.matches;
      total.wins += v.wins;
      total.draws += v.draws;
      total.losses += v.losses;
      total.goalsFor += v.goalsFor;
      total.goalsAgainst += v.goalsAgainst;
      total.points += v.points;
    }
    return {
      team,
      matches: total.matches,
      wins: total.wins,
      draws: total.draws,
      losses: total.losses,
      goalsFor: total.goalsFor,
      goalsAgainst: total.goalsAgainst,
      points: total.points,
      home,
      away,
    };
  }

  /** Head-to-head record between two teams. */
  headToHead(teamA: string, teamB: string): HeadToHead {
    const rows = this.findMatches({ team: teamA, opponent: teamB });
    let teamAWins = 0;
    let teamBWins = 0;
    let draws = 0;
    let teamAGoals = 0;
    let teamBGoals = 0;
    for (const m of rows) {
      const aIsHome = teamsMatch(m.homeTeam, teamA);
      const aGoals = aIsHome ? m.homeGoal : m.awayGoal;
      const bGoals = aIsHome ? m.awayGoal : m.homeGoal;
      if (aGoals == null || bGoals == null) continue;
      teamAGoals += aGoals;
      teamBGoals += bGoals;
      if (aGoals > bGoals) teamAWins++;
      else if (aGoals < bGoals) teamBWins++;
      else draws++;
    }
    return {
      teamA,
      teamB,
      matches: rows.length,
      teamAWins,
      teamBWins,
      draws,
      teamAGoals,
      teamBGoals,
      matchesList: rows,
    };
  }

  /** Distinct competitions a team appears in. */
  competitionsFor(team: string): string[] {
    const set = new Set<string>();
    for (const m of this.matchesForTeam(team)) {
      if (m.competition) set.add(m.competition);
    }
    return [...set].sort();
  }

  /** Search players by name substring, nationality, club, position. */
  playerSearch(opts: {
    name?: string;
    nationality?: string;
    club?: string;
    position?: string;
    limit?: number;
    sortBy?: "overall" | "potential" | "name";
    desc?: boolean;
  }): PlayerRecord[] {
    let rows = this.players;
    if (opts.name) {
      const q = opts.name.toLowerCase();
      rows = rows.filter((p) => p.name.toLowerCase().includes(q));
    }
    if (opts.nationality) {
      const q = opts.nationality.toLowerCase();
      rows = rows.filter((p) => p.nationality.toLowerCase().includes(q));
    }
    if (opts.club) {
      const q = opts.club.toLowerCase();
      rows = rows.filter((p) => p.club.toLowerCase().includes(q));
    }
    if (opts.position) {
      const q = opts.position.toLowerCase();
      rows = rows.filter((p) => p.position.toLowerCase().includes(q));
    }
    const sortBy = opts.sortBy ?? "overall";
    const desc = opts.desc ?? true;
    const sorted = rows.slice().sort((a, b) => {
      let av: number | string = 0;
      let bv: number | string = 0;
      if (sortBy === "name") {
        av = a.name.toLowerCase();
        bv = b.name.toLowerCase();
      } else {
        av = (a[sortBy] ?? 0) as number;
        bv = (b[sortBy] ?? 0) as number;
      }
      if (av < bv) return desc ? 1 : -1;
      if (av > bv) return desc ? -1 : 1;
      return 0;
    });
    if (opts.limit != null) return sorted.slice(0, opts.limit);
    return sorted;
  }

  /** Average Brazilian (by nationality) players grouped by club. */
  brazilianPlayersByClub(): { club: string; count: number; avgRating: number }[] {
    const byClub = new Map<string, PlayerRecord[]>();
    for (const p of this.players) {
      if (!p.club) continue;
      if (
        p.nationality.toLowerCase().includes("brazil") ||
        p.nationality.toLowerCase().includes("brasil")
      ) {
        const arr = byClub.get(p.club) ?? [];
        arr.push(p);
        byClub.set(p.club, arr);
      }
    }
    return [...byClub.entries()]
      .map(([club, arr]) => ({
        club,
        count: arr.length,
        avgRating:
          arr.reduce((s, p) => s + (p.overall ?? 0), 0) / arr.length || 0,
      }))
      .filter((e) => e.count > 0)
      .sort((a, b) => b.count - a.count || b.avgRating - a.avgRating);
  }

  /**
   * Computed league standings for a competition+season.
   * Uses 3-1-0 points; sorts by points, then goal difference, then goals for.
   * Only seasons with a usable home/away double format (Brasileirão-style)
   * produce meaningful tables; other competitions still return a best-effort
   * ranking by points accrued from recorded scored matches.
   */
  standings(competition: string, season: number): StandingRow[] {
    const comp = competition.toLowerCase();
    const rows = this.matches.filter(
      (m) =>
        m.season === season &&
        m.competition.toLowerCase().includes(comp) &&
        m.homeGoal != null &&
        m.awayGoal != null,
    );
    const table = new Map<
      string,
      {
        played: number;
        wins: number;
        draws: number;
        losses: number;
        gf: number;
        ga: number;
        pts: number;
      }
    >();
    const get = (t: string) =>
      table.get(t) ?? {
        played: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        gf: 0,
        ga: 0,
        pts: 0,
      };
    for (const m of rows) {
      const h = get(m.homeTeam);
      const a = get(m.awayTeam);
      h.played++;
      a.played++;
      h.gf += m.homeGoal!;
      h.ga += m.awayGoal!;
      a.gf += m.awayGoal!;
      a.ga += m.homeGoal!;
      if (m.homeGoal! > m.awayGoal!) {
        h.wins++;
        h.pts += 3;
        a.losses++;
      } else if (m.homeGoal! < m.awayGoal!) {
        a.wins++;
        a.pts += 3;
        h.losses++;
      } else {
        h.draws++;
        a.draws++;
        h.pts++;
        a.pts++;
      }
      table.set(m.homeTeam, h);
      table.set(m.awayTeam, a);
    }
    return [...table.entries()]
      .map(([team, s], i) => ({
        position: i + 1,
        team,
        played: s.played,
        wins: s.wins,
        draws: s.draws,
        losses: s.losses,
        goalsFor: s.gf,
        goalsAgainst: s.ga,
        goalDifference: s.gf - s.ga,
        points: s.pts,
      }))
      .sort(
        (a, b) =>
          b.points - a.points ||
          b.goalDifference - a.goalDifference ||
          b.goalsFor - a.goalsFor ||
          a.team.localeCompare(b.team),
      )
      .map((r, i) => ({ ...r, position: i + 1 }));
  }

  /** Biggest victories (largest goal difference), sorted descending. */
  biggestWins(limit = 10, competition?: string): MatchRecord[] {
    let rows = this.matches.filter(
      (m) => m.homeGoal != null && m.awayGoal != null,
    );
    if (competition) {
      const c = competition.toLowerCase();
      rows = rows.filter((m) => m.competition.toLowerCase().includes(c));
    }
    return rows
      .slice()
      .sort((a, b) => {
        const da = Math.abs(a.homeGoal! - a.awayGoal!);
        const db = Math.abs(b.homeGoal! - b.awayGoal!);
        if (db !== da) return db - da;
        return (b.homeGoal! + b.awayGoal!) - (a.homeGoal! + a.awayGoal!);
      })
      .slice(0, limit);
  }

  /** Average goals per match and home-win rate across a competition. */
  averageGoals(competition?: string): {
    matches: number;
    avgGoals: number;
    homeWinRate: number;
    awayWinRate: number;
    drawRate: number;
  } {
    let rows = this.matches.filter(
      (m) => m.homeGoal != null && m.awayGoal != null,
    );
    if (competition) {
      const c = competition.toLowerCase();
      rows = rows.filter((m) => m.competition.toLowerCase().includes(c));
    }
    if (rows.length === 0) {
      return { matches: 0, avgGoals: 0, homeWinRate: 0, awayWinRate: 0, drawRate: 0 };
    }
    let goals = 0;
    let homeWins = 0;
    let awayWins = 0;
    let draws = 0;
    for (const m of rows) {
      goals += m.homeGoal! + m.awayGoal!;
      if (m.homeGoal! > m.awayGoal!) homeWins++;
      else if (m.homeGoal! < m.awayGoal!) awayWins++;
      else draws++;
    }
    const n = rows.length;
    return {
      matches: n,
      avgGoals: goals / n,
      homeWinRate: homeWins / n,
      awayWinRate: awayWins / n,
      drawRate: draws / n,
    };
  }

  /** Which team has the best record at a venue ("home" | "away"). */
  bestRecordAtVenue(venue: "home" | "away", season?: number): TeamStats | null {
    const teams = new Set<string>();
    for (const m of this.matches) {
      teams.add(venue === "home" ? m.homeTeam : m.awayTeam);
    }
    let best: TeamStats | null = null;
    let bestPoints = -1;
    for (const t of teams) {
      const s = this.teamStats(t, season);
      const v = venue === "home" ? s.home : s.away;
      const pts = v.points;
      const rate = v.matches > 0 ? v.wins / v.matches : 0;
      // Prefer win rate, then points, for "best record".
      const score = rate * 1000 + pts;
      if (score > bestPoints) {
        bestPoints = score;
        best = s;
      }
    }
    return best;
  }
}
