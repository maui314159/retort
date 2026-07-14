/**
 * Context
 * -------
 * Query engine for the Brazilian Soccer MCP server. Wraps the loaded
 * `SoccerData` (see loader.ts / types.ts) in a `SoccerKnowledgeBase` that
 * exposes the capabilities required by the spec:
 *   - match search (by team, opponent, competition, season, date range)
 *   - head-to-head records between two clubs
 *   - team statistics (W/D/L, goals, home/away split) per season/competition
 *   - league standings calculated from match results
 *   - player search (name / nationality / club / position) with ratings
 *   - aggregate statistics (avg goals, home-win rate, biggest wins, club squads)
 *
 * All team matching goes through the accent-folded, suffix-stripped keys from
 * normalize.ts so "Palmeiras", "Palmeiras-SP" and "São Paulo" resolve
 * consistently. Methods return plain data; human-readable rendering lives in
 * format.ts. The full dataset (~24k matches, ~18k players) is held in memory,
 * so every query is a linear scan — comfortably within the latency budget.
 */

import { normalizeTeamKey, teamMatches } from "./normalize.js";
import type {
  Competition,
  Match,
  Player,
  SoccerData,
} from "./types.js";

export interface MatchFilter {
  /** Team that must appear in the match (home, away, or either). */
  team?: string;
  /** Restrict `team` to a side. */
  side?: "home" | "away" | "either";
  /** Second team — when set, only matches between `team` and `opponent`. */
  opponent?: string;
  competition?: Competition;
  season?: number;
  /** Inclusive ISO date lower bound (YYYY-MM-DD). */
  from?: string;
  /** Inclusive ISO date upper bound (YYYY-MM-DD). */
  to?: string;
  limit?: number;
}

export interface HeadToHead {
  teamA: string;
  teamB: string;
  totalMatches: number;
  teamAWins: number;
  teamBWins: number;
  draws: number;
  teamAGoals: number;
  teamBGoals: number;
  matches: Match[];
}

export interface TeamRecord {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  /** 0..1 fraction of matches won. */
  winRate: number;
  points: number;
}

export interface StandingRow extends TeamRecord {
  rank: number;
}

export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  limit?: number;
}

export interface ClubSquadSummary {
  club: string;
  playerCount: number;
  averageOverall: number;
}

/** Aggregate outcome/goal statistics over a filtered set of matches. */
export interface AggregateStats {
  matches: number;
  totalGoals: number;
  averageGoals: number;
  homeWins: number;
  awayWins: number;
  draws: number;
  homeWinRate: number;
  awayWinRate: number;
  drawRate: number;
}

/** A team's total goals scored over a competition+season. */
export interface TeamGoalTally {
  team: string;
  goalsFor: number;
  matches: number;
}

const POINTS_WIN = 3;
const POINTS_DRAW = 1;

export class SoccerKnowledgeBase {
  private readonly matches: Match[];
  private readonly players: Player[];

  constructor(data: SoccerData) {
    this.matches = data.matches;
    this.players = data.players;
  }

  get matchCount(): number {
    return this.matches.length;
  }

  get playerCount(): number {
    return this.players.length;
  }

  // ---- Match queries -----------------------------------------------------

  /** Find matches matching all provided criteria, newest first. */
  findMatches(filter: MatchFilter): Match[] {
    const teamKey = filter.team ? normalizeTeamKey(filter.team) : undefined;
    const oppKey = filter.opponent ? normalizeTeamKey(filter.opponent) : undefined;
    const side = filter.side ?? "either";

    const result = this.matches.filter((m) => {
      if (filter.competition && m.competition !== filter.competition) return false;
      if (filter.season !== undefined && m.season !== filter.season) return false;
      if (filter.from && (!m.date || m.date < filter.from)) return false;
      if (filter.to && (!m.date || m.date > filter.to)) return false;

      if (teamKey) {
        const onHome = m.homeKey === teamKey || teamMatches(m.homeTeam, filter.team!);
        const onAway = m.awayKey === teamKey || teamMatches(m.awayTeam, filter.team!);
        if (side === "home" && !onHome) return false;
        if (side === "away" && !onAway) return false;
        if (side === "either" && !onHome && !onAway) return false;
      }

      if (oppKey) {
        const oppOnHome =
          m.homeKey === oppKey || teamMatches(m.homeTeam, filter.opponent!);
        const oppOnAway =
          m.awayKey === oppKey || teamMatches(m.awayTeam, filter.opponent!);
        if (!oppOnHome && !oppOnAway) return false;
      }

      return true;
    });

    result.sort(byDateDesc);
    return typeof filter.limit === "number" ? result.slice(0, filter.limit) : result;
  }

  /** Compute the head-to-head record between two clubs across all data. */
  headToHead(teamA: string, teamB: string): HeadToHead {
    const matches = this.findMatches({ team: teamA, opponent: teamB });
    const keyA = normalizeTeamKey(teamA);

    let teamAWins = 0;
    let teamBWins = 0;
    let draws = 0;
    let teamAGoals = 0;
    let teamBGoals = 0;
    let displayA = teamA;
    let displayB = teamB;

    for (const m of matches) {
      if (m.homeGoals === undefined || m.awayGoals === undefined) continue;
      const aIsHome = m.homeKey === keyA || teamMatches(m.homeTeam, teamA);
      const aGoals = aIsHome ? m.homeGoals : m.awayGoals;
      const bGoals = aIsHome ? m.awayGoals : m.homeGoals;
      displayA = aIsHome ? m.homeTeam : m.awayTeam;
      displayB = aIsHome ? m.awayTeam : m.homeTeam;
      teamAGoals += aGoals;
      teamBGoals += bGoals;
      if (aGoals > bGoals) teamAWins++;
      else if (aGoals < bGoals) teamBWins++;
      else draws++;
    }

    return {
      teamA: displayA,
      teamB: displayB,
      totalMatches: matches.length,
      teamAWins,
      teamBWins,
      draws,
      teamAGoals,
      teamBGoals,
      matches,
    };
  }

  // ---- Team queries ------------------------------------------------------

  /**
   * Aggregate a team's record. `side` narrows to home-only or away-only
   * fixtures; season/competition filters are applied first.
   */
  teamRecord(
    team: string,
    opts: { season?: number; competition?: Competition; side?: "home" | "away" | "either" } = {}
  ): TeamRecord {
    const side = opts.side ?? "either";
    const matches = this.findMatches({
      team,
      side,
      season: opts.season,
      competition: opts.competition,
    });

    const key = normalizeTeamKey(team);
    let display = team;
    const rec: TeamRecord = {
      team: display,
      matches: 0,
      wins: 0,
      draws: 0,
      losses: 0,
      goalsFor: 0,
      goalsAgainst: 0,
      winRate: 0,
      points: 0,
    };

    for (const m of matches) {
      if (m.homeGoals === undefined || m.awayGoals === undefined) continue;
      const isHome = m.homeKey === key || teamMatches(m.homeTeam, team);
      display = isHome ? m.homeTeam : m.awayTeam;
      const gf = isHome ? m.homeGoals : m.awayGoals;
      const ga = isHome ? m.awayGoals : m.homeGoals;
      rec.matches++;
      rec.goalsFor += gf;
      rec.goalsAgainst += ga;
      if (gf > ga) rec.wins++;
      else if (gf < ga) rec.losses++;
      else rec.draws++;
    }

    rec.team = display;
    rec.points = rec.wins * POINTS_WIN + rec.draws * POINTS_DRAW;
    rec.winRate = rec.matches > 0 ? rec.wins / rec.matches : 0;
    return rec;
  }

  /**
   * Calculate full standings for a competition+season from match results.
   * Ranked by points, then goal difference, then goals for.
   */
  standings(competition: Competition, season: number): StandingRow[] {
    const matches = this.findMatches({ competition, season });
    const table = new Map<string, TeamRecord>();

    const ensure = (display: string): TeamRecord => {
      const key = normalizeTeamKey(display);
      let row = table.get(key);
      if (!row) {
        row = {
          team: display,
          matches: 0,
          wins: 0,
          draws: 0,
          losses: 0,
          goalsFor: 0,
          goalsAgainst: 0,
          winRate: 0,
          points: 0,
        };
        table.set(key, row);
      }
      return row;
    };

    for (const m of matches) {
      if (m.homeGoals === undefined || m.awayGoals === undefined) continue;
      const home = ensure(m.homeTeam);
      const away = ensure(m.awayTeam);
      home.matches++;
      away.matches++;
      home.goalsFor += m.homeGoals;
      home.goalsAgainst += m.awayGoals;
      away.goalsFor += m.awayGoals;
      away.goalsAgainst += m.homeGoals;
      if (m.homeGoals > m.awayGoals) {
        home.wins++;
        away.losses++;
      } else if (m.homeGoals < m.awayGoals) {
        away.wins++;
        home.losses++;
      } else {
        home.draws++;
        away.draws++;
      }
    }

    const rows = [...table.values()];
    for (const r of rows) {
      r.points = r.wins * POINTS_WIN + r.draws * POINTS_DRAW;
      r.winRate = r.matches > 0 ? r.wins / r.matches : 0;
    }
    rows.sort((a, b) => {
      if (b.points !== a.points) return b.points - a.points;
      const gdA = a.goalsFor - a.goalsAgainst;
      const gdB = b.goalsFor - b.goalsAgainst;
      if (gdB !== gdA) return gdB - gdA;
      if (b.goalsFor !== a.goalsFor) return b.goalsFor - a.goalsFor;
      return a.team.localeCompare(b.team);
    });

    return rows.map((r, i) => ({ ...r, rank: i + 1 }));
  }

  // ---- Player queries ----------------------------------------------------

  /** Search players by any combination of name/nationality/club/position. */
  findPlayers(filter: PlayerFilter): Player[] {
    const nameQ = filter.name?.toLowerCase().normalize("NFC");
    const natQ = filter.nationality?.toLowerCase();
    const posQ = filter.position?.toLowerCase();
    const clubKey = filter.club ? normalizeTeamKey(filter.club) : undefined;

    const result = this.players.filter((p) => {
      if (nameQ && !p.name.toLowerCase().includes(nameQ)) return false;
      if (natQ && p.nationality.toLowerCase() !== natQ) return false;
      if (posQ && p.position.toLowerCase() !== posQ) return false;
      if (filter.minOverall !== undefined && (p.overall ?? 0) < filter.minOverall) {
        return false;
      }
      if (clubKey && !(p.clubKey === clubKey || teamMatches(p.club, filter.club!))) {
        return false;
      }
      return true;
    });

    result.sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
    return typeof filter.limit === "number" ? result.slice(0, filter.limit) : result;
  }

  /**
   * Summarize the players each club has, restricted to an optional
   * nationality (e.g. Brazilian players grouped by Brazilian club). Sorted by
   * squad size descending.
   */
  clubSquads(opts: { nationality?: string; limit?: number } = {}): ClubSquadSummary[] {
    const natQ = opts.nationality?.toLowerCase();
    const byClub = new Map<string, { club: string; total: number; sum: number }>();

    for (const p of this.players) {
      if (natQ && p.nationality.toLowerCase() !== natQ) continue;
      if (!p.club) continue;
      let entry = byClub.get(p.clubKey);
      if (!entry) {
        entry = { club: p.club, total: 0, sum: 0 };
        byClub.set(p.clubKey, entry);
      }
      entry.total++;
      entry.sum += p.overall ?? 0;
    }

    const rows: ClubSquadSummary[] = [...byClub.values()].map((e) => ({
      club: e.club,
      playerCount: e.total,
      averageOverall: e.total > 0 ? e.sum / e.total : 0,
    }));
    rows.sort((a, b) => b.playerCount - a.playerCount || b.averageOverall - a.averageOverall);
    return typeof opts.limit === "number" ? rows.slice(0, opts.limit) : rows;
  }

  // ---- Statistical analysis ---------------------------------------------

  /**
   * Aggregate statistics over a set of matches (optionally filtered by
   * competition/season). Returns averages and home/away outcome rates.
   */
  aggregateStats(filter: MatchFilter = {}): AggregateStats {
    const matches = this.findMatches(filter);
    let totalGoals = 0;
    let scored = 0;
    let homeWins = 0;
    let awayWins = 0;
    let draws = 0;

    for (const m of matches) {
      if (m.homeGoals === undefined || m.awayGoals === undefined) continue;
      scored++;
      totalGoals += m.homeGoals + m.awayGoals;
      if (m.homeGoals > m.awayGoals) homeWins++;
      else if (m.homeGoals < m.awayGoals) awayWins++;
      else draws++;
    }

    return {
      matches: scored,
      totalGoals,
      averageGoals: scored > 0 ? totalGoals / scored : 0,
      homeWins,
      awayWins,
      draws,
      homeWinRate: scored > 0 ? homeWins / scored : 0,
      awayWinRate: scored > 0 ? awayWins / scored : 0,
      drawRate: scored > 0 ? draws / scored : 0,
    };
  }

  /** Biggest victories (largest goal margin) among the filtered matches. */
  biggestWins(filter: MatchFilter = {}, limit = 10): Match[] {
    const matches = this.findMatches(filter).filter(
      (m) => m.homeGoals !== undefined && m.awayGoals !== undefined
    );
    matches.sort((a, b) => {
      const ma = Math.abs((a.homeGoals ?? 0) - (a.awayGoals ?? 0));
      const mb = Math.abs((b.homeGoals ?? 0) - (b.awayGoals ?? 0));
      if (mb !== ma) return mb - ma;
      const ta = (a.homeGoals ?? 0) + (a.awayGoals ?? 0);
      const tb = (b.homeGoals ?? 0) + (b.awayGoals ?? 0);
      return tb - ta;
    });
    return matches.slice(0, limit);
  }

  /**
   * Rank teams in a competition+season by total goals scored. Useful for
   * "which team scored the most goals" questions.
   */
  topScoringTeams(
    competition: Competition,
    season: number,
    limit = 10
  ): TeamGoalTally[] {
    return this.standings(competition, season)
      .map((r) => ({ team: r.team, goalsFor: r.goalsFor, matches: r.matches }))
      .sort((a, b) => b.goalsFor - a.goalsFor)
      .slice(0, limit);
  }

  /** Distinct seasons available for a competition, ascending. */
  seasonsFor(competition: Competition): number[] {
    const seen = new Set<number>();
    for (const m of this.matches) {
      if (m.competition === competition && m.season !== undefined) seen.add(m.season);
    }
    return [...seen].sort((a, b) => a - b);
  }
}

function byDateDesc(a: Match, b: Match): number {
  const da = a.date ?? "";
  const db = b.date ?? "";
  if (da === db) return 0;
  // Undated entries sort last.
  if (!da) return 1;
  if (!db) return -1;
  return db < da ? -1 : 1;
}
