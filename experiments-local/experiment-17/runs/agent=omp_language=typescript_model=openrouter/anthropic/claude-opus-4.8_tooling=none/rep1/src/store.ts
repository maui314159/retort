/**
 * Context
 * =======
 * In-memory query engine for the Brazilian Soccer MCP server.
 *
 * `DataStore` wraps the normalized `Match[]` / `Player[]` produced by loader.ts
 * and exposes the query primitives the MCP tools call: match search, team
 * statistics, head-to-head, standings (computed from results), player search,
 * club rosters, and league-wide aggregates.
 *
 * Performance: the full corpus is ~24k matches + ~18k players. All queries are
 * single linear scans with early predicate exits, comfortably inside the spec's
 * <2s simple / <5s aggregate budgets. Team matching uses the canonical keys
 * precomputed at load time (no per-query normalization of stored rows).
 */

import { loadAll, DEFAULT_DATA_DIR } from './loader.js';
import {
  canonicalCompetition,
  canonicalTeam,
  type Competition,
} from './normalize.js';
import type { Match, Player, StandingRow, TeamRecord } from './types.js';

/** Criteria for {@link DataStore.findMatches}. */
export interface MatchQuery {
  /** Match where this team is home, away, or either (canonicalized internally). */
  team?: string;
  /** Restrict to matches where `team` and `opponent` faced each other. */
  opponent?: string;
  /** Restrict `team` to home matches only. */
  homeOnly?: boolean;
  /** Restrict `team` to away matches only. */
  awayOnly?: boolean;
  competition?: string;
  season?: number;
  /** Inclusive ISO date lower bound (YYYY-MM-DD). */
  dateFrom?: string;
  /** Inclusive ISO date upper bound (YYYY-MM-DD). */
  dateTo?: string;
  /** Max rows returned (after sorting newest-first). Default 50. */
  limit?: number;
}

/** Criteria for {@link DataStore.findPlayers}. */
export interface PlayerQuery {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  /** Minimum FIFA overall rating. */
  minOverall?: number;
  limit?: number;
}

export class DataStore {
  readonly matches: Match[];
  readonly players: Player[];

  constructor(matches: Match[], players: Player[]) {
    this.matches = matches;
    this.players = players;
  }

  /** Build a store by loading the bundled CSVs from `dataDir`. */
  static fromDataDir(dataDir: string = DEFAULT_DATA_DIR): DataStore {
    const { matches, players } = loadAll(dataDir);
    return new DataStore(matches, players);
  }
  /**
   * Find matches by team / opponent / competition / season / date range.
   * Results are sorted newest-first by date (undated rows last) and capped at
   * `limit` (default 50).
   */
  findMatches(query: MatchQuery): Match[] {
    const teamKey = query.team ? canonicalTeam(query.team) : undefined;
    const oppKey = query.opponent ? canonicalTeam(query.opponent) : undefined;
    const comp = query.competition ? canonicalCompetition(query.competition) : undefined;
    const limit = query.limit ?? 50;

    const out: Match[] = [];
    for (const m of this.matches) {
      if (comp && m.competition !== comp) continue;
      if (query.season !== undefined && m.season !== query.season) continue;
      if (query.dateFrom && (!m.date || m.date < query.dateFrom)) continue;
      if (query.dateTo && (!m.date || m.date > query.dateTo)) continue;

      if (teamKey) {
        const isHome = m.canonicalHome === teamKey;
        const isAway = m.canonicalAway === teamKey;
        if (!isHome && !isAway) continue;
        if (query.homeOnly && !isHome) continue;
        if (query.awayOnly && !isAway) continue;
      }
      if (oppKey && m.canonicalHome !== oppKey && m.canonicalAway !== oppKey) continue;
      out.push(m);
    }

    out.sort((a, b) => {
      if (a.date && b.date) return a.date < b.date ? 1 : a.date > b.date ? -1 : 0;
      if (a.date) return -1;
      if (b.date) return 1;
      return (b.season ?? 0) - (a.season ?? 0);
    });

    return out.slice(0, limit);
  }

  /**
   * Aggregate a team's win/draw/loss + goals record over an optionally filtered
   * set (competition / season / home-or-away venue). `venue` 'home' counts only
   * matches where the team played at home, 'away' only away, 'all' both.
   */
  teamRecord(
    team: string,
    opts: { competition?: string; season?: number; venue?: 'home' | 'away' | 'all' } = {},
  ): TeamRecord {
    const key = canonicalTeam(team);
    const comp = opts.competition ? canonicalCompetition(opts.competition) : undefined;
    const venue = opts.venue ?? 'all';
    const rec: TeamRecord = { matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0 };

    for (const m of this.matches) {
      if (comp && m.competition !== comp) continue;
      if (opts.season !== undefined && m.season !== opts.season) continue;
      const isHome = m.canonicalHome === key;
      const isAway = m.canonicalAway === key;
      if (!isHome && !isAway) continue;
      if (venue === 'home' && !isHome) continue;
      if (venue === 'away' && !isAway) continue;

      const gf = isHome ? m.homeGoals : m.awayGoals;
      const ga = isHome ? m.awayGoals : m.homeGoals;
      rec.matches++;
      rec.goalsFor += gf;
      rec.goalsAgainst += ga;
      if (gf > ga) rec.wins++;
      else if (gf < ga) rec.losses++;
      else rec.draws++;
    }
    return rec;
  }

  /**
   * Head-to-head summary between two teams: each team's wins, draws, the goals
   * each scored, and the chronologically sorted list of meetings (newest-first).
   */
  headToHead(
    teamA: string,
    teamB: string,
    opts: { competition?: string; limit?: number } = {},
  ): {
    teamA: string;
    teamB: string;
    aWins: number;
    bWins: number;
    draws: number;
    aGoals: number;
    bGoals: number;
    matches: Match[];
  } {
    const keyA = canonicalTeam(teamA);
    const keyB = canonicalTeam(teamB);
    const comp = opts.competition ? canonicalCompetition(opts.competition) : undefined;

    let aWins = 0;
    let bWins = 0;
    let draws = 0;
    let aGoals = 0;
    let bGoals = 0;
    const meetings: Match[] = [];

    for (const m of this.matches) {
      if (comp && m.competition !== comp) continue;
      const aHome = m.canonicalHome === keyA && m.canonicalAway === keyB;
      const aAway = m.canonicalAway === keyA && m.canonicalHome === keyB;
      if (!aHome && !aAway) continue;

      meetings.push(m);
      const aScore = aHome ? m.homeGoals : m.awayGoals;
      const bScore = aHome ? m.awayGoals : m.homeGoals;
      aGoals += aScore;
      bGoals += bScore;
      if (aScore > bScore) aWins++;
      else if (aScore < bScore) bWins++;
      else draws++;
    }

    meetings.sort((x, y) => {
      if (x.date && y.date) return x.date < y.date ? 1 : x.date > y.date ? -1 : 0;
      if (x.date) return -1;
      if (y.date) return 1;
      return (y.season ?? 0) - (x.season ?? 0);
    });

    const displayA = meetings.find((m) => m.canonicalHome === keyA)?.homeTeam
      ?? meetings.find((m) => m.canonicalAway === keyA)?.awayTeam
      ?? teamA;
    const displayB = meetings.find((m) => m.canonicalHome === keyB)?.homeTeam
      ?? meetings.find((m) => m.canonicalAway === keyB)?.awayTeam
      ?? teamB;

    return {
      teamA: displayA,
      teamB: displayB,
      aWins,
      bWins,
      draws,
      aGoals,
      bGoals,
      matches: opts.limit ? meetings.slice(0, opts.limit) : meetings,
    };
  }

  /**
   * Compute a league table for a competition+season from match results.
   * 3 points per win, 1 per draw. Sorted by points, then goal difference, then
   * goals for. Returns [] when no matches match the filter.
   */
  standings(competition: string, season: number): StandingRow[] {
    const comp = canonicalCompetition(competition);
    if (!comp) return [];

    const table = new Map<string, StandingRow>();
    const ensure = (key: string, display: string): StandingRow => {
      let row = table.get(key);
      if (!row) {
        row = {
          team: display,
          points: 0,
          played: 0,
          wins: 0,
          draws: 0,
          losses: 0,
          goalsFor: 0,
          goalsAgainst: 0,
          goalDifference: 0,
        };
        table.set(key, row);
      }
      return row;
    };

    for (const m of this.matches) {
      if (m.competition !== comp || m.season !== season) continue;
      const home = ensure(m.canonicalHome, m.homeTeam);
      const away = ensure(m.canonicalAway, m.awayTeam);
      home.played++;
      away.played++;
      home.goalsFor += m.homeGoals;
      home.goalsAgainst += m.awayGoals;
      away.goalsFor += m.awayGoals;
      away.goalsAgainst += m.homeGoals;
      if (m.homeGoals > m.awayGoals) {
        home.wins++;
        home.points += 3;
        away.losses++;
      } else if (m.homeGoals < m.awayGoals) {
        away.wins++;
        away.points += 3;
        home.losses++;
      } else {
        home.draws++;
        away.draws++;
        home.points++;
        away.points++;
      }
    }

    const rows = [...table.values()];
    for (const r of rows) r.goalDifference = r.goalsFor - r.goalsAgainst;
    rows.sort(
      (a, b) =>
        b.points - a.points ||
        b.goalDifference - a.goalDifference ||
        b.goalsFor - a.goalsFor ||
        a.team.localeCompare(b.team),
    );
    return rows;
  }

  /** Find players by name / nationality / club / position / min rating. */
  findPlayers(query: PlayerQuery): Player[] {
    const name = query.name ? query.name.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase() : undefined;
    const nat = query.nationality ? query.nationality.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase() : undefined;
    const clubKey = query.club ? canonicalTeam(query.club) : undefined;
    const pos = query.position ? query.position.toUpperCase() : undefined;
    const limit = query.limit ?? 50;

    const out: Player[] = [];
    for (const p of this.players) {
      if (name) {
        const pn = p.name.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
        if (!pn.includes(name)) continue;
      }
      if (nat) {
        const pnat = p.nationality.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
        if (pnat !== nat) continue;
      }
      if (clubKey && p.canonicalClub !== clubKey) continue;
      if (pos && (p.position ?? '').toUpperCase() !== pos) continue;
      if (query.minOverall !== undefined && p.overall < query.minOverall) continue;
      out.push(p);
    }

    out.sort((a, b) => b.overall - a.overall || a.name.localeCompare(b.name));
    return out.slice(0, limit);
  }

  /**
   * League-wide aggregate stats for a competition+season (or all data when both
   * omitted): match count, total goals, average goals per match, home/away/draw
   * win rates.
   */
  leagueStats(opts: { competition?: string; season?: number } = {}): {
    matches: number;
    totalGoals: number;
    avgGoalsPerMatch: number;
    homeWinRate: number;
    awayWinRate: number;
    drawRate: number;
  } {
    const comp = opts.competition ? canonicalCompetition(opts.competition) : undefined;
    let matches = 0;
    let totalGoals = 0;
    let homeWins = 0;
    let awayWins = 0;
    let draws = 0;

    for (const m of this.matches) {
      if (comp && m.competition !== comp) continue;
      if (opts.season !== undefined && m.season !== opts.season) continue;
      matches++;
      totalGoals += m.homeGoals + m.awayGoals;
      if (m.homeGoals > m.awayGoals) homeWins++;
      else if (m.homeGoals < m.awayGoals) awayWins++;
      else draws++;
    }

    return {
      matches,
      totalGoals,
      avgGoalsPerMatch: matches ? totalGoals / matches : 0,
      homeWinRate: matches ? homeWins / matches : 0,
      awayWinRate: matches ? awayWins / matches : 0,
      drawRate: matches ? draws / matches : 0,
    };
  }

  /**
   * Biggest victories (largest goal margin) over an optionally filtered set.
   * Sorted by margin desc, then total goals desc. Capped at `limit` (default 10).
   */
  biggestWins(opts: { competition?: string; season?: number; limit?: number } = {}): Match[] {
    const comp = opts.competition ? canonicalCompetition(opts.competition) : undefined;
    const limit = opts.limit ?? 10;
    const filtered: Match[] = [];
    for (const m of this.matches) {
      if (comp && m.competition !== comp) continue;
      if (opts.season !== undefined && m.season !== opts.season) continue;
      filtered.push(m);
    }
    filtered.sort((a, b) => {
      const ma = Math.abs(a.homeGoals - a.awayGoals);
      const mb = Math.abs(b.homeGoals - b.awayGoals);
      return mb - ma || (b.homeGoals + b.awayGoals) - (a.homeGoals + a.awayGoals);
    });
    return filtered.slice(0, limit);
  }

  /** Distinct competition labels present in the loaded data. */
  competitions(): Competition[] {
    const seen = new Set<Competition>();
    for (const m of this.matches) seen.add(m.competition);
    return [...seen];
  }
}
