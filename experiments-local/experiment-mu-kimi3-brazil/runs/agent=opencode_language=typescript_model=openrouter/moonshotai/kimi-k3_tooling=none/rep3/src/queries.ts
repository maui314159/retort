/**
 * Query engine: answers the five question categories from the spec
 * (matches, teams, players, competitions, statistics) on top of the
 * knowledge-graph indexes.
 */

import type {
  CompetitionLabel,
  Match,
  Player,
  StandingRow,
  TeamRecord,
} from "./types.js";
import type { BuiltGraph } from "./graph.js";
import {
  isBrazilianTeamKey,
  loose,
  resolveCompetition,
  resolveTeamQuery,
  teamDisplayName,
} from "./normalize.js";

export class SoccerQueries {
  constructor(private readonly built: BuiltGraph) {}

  private get matches(): Match[] {
    // All matches, already sorted by date asc.
    return this.allMatches;
  }

  private allMatches: Match[] = [];

  /** Bind the flat match list (kept separate from graph for iteration). */
  bindMatches(matches: Match[]): this {
    this.allMatches = matches;
    return this;
  }

  /* ---------------------------------------------------------------- */
  /* 1. Match queries                                                   */
  /* ---------------------------------------------------------------- */

  findMatches(filter: {
    team?: string;
    opponent?: string;
    competition?: string;
    season?: number;
    from?: string;
    to?: string;
    venue?: "home" | "away" | "any";
    round?: string;
    stage?: string;
    limit?: number;
  }): Match[] {
    const teamKey = filter.team ? resolveTeamQuery(filter.team) : null;
    const oppKey = filter.opponent ? resolveTeamQuery(filter.opponent) : null;
    const comp = filter.competition
      ? resolveCompetition(filter.competition)
      : null;
    const venue = filter.venue ?? "any";
    const limit = Math.min(Math.max(filter.limit ?? 50, 1), 500);

    let pool: Match[];
    if (teamKey && this.built.indexes.matchesByTeam.has(teamKey)) {
      pool = this.built.indexes.matchesByTeam.get(teamKey)!;
    } else if (comp && this.built.indexes.matchesByCompetition.has(comp)) {
      pool = this.built.indexes.matchesByCompetition.get(comp)!;
    } else {
      pool = this.matches;
    }

    const out: Match[] = [];
    for (const m of pool) {
      if (teamKey) {
        const isHome = m.homeTeam.key === teamKey;
        const isAway = m.awayTeam.key === teamKey;
        if (venue === "home" && !isHome) continue;
        if (venue === "away" && !isAway) continue;
        if (!isHome && !isAway) continue;
      }
      if (oppKey && m.homeTeam.key !== oppKey && m.awayTeam.key !== oppKey) continue;
      if (comp && m.competition !== comp) continue;
      if (filter.season != null && m.season !== filter.season) continue;
      if (filter.from && m.date < filter.from) continue;
      if (filter.to && m.date > filter.to) continue;
      if (filter.round && m.round !== filter.round) continue;
      if (filter.stage && loose(m.stage ?? "") !== loose(filter.stage)) continue;
      out.push(m);
      if (out.length >= limit) break;
    }
    return out;
  }

  /* ---------------------------------------------------------------- */
  /* Head-to-head                                                       */
  /* ---------------------------------------------------------------- */

  headToHead(teamA: string, teamB: string, competition?: string) {
    const keyA = resolveTeamQuery(teamA);
    const keyB = resolveTeamQuery(teamB);
    const comp = competition ? resolveCompetition(competition) : null;
    const pool = this.built.indexes.matchesByTeam.get(keyA) ?? [];
    const matches = pool.filter(
      (m) =>
        (m.homeTeam.key === keyB || m.awayTeam.key === keyB) &&
        (!comp || m.competition === comp),
    );
    let winsA = 0, winsB = 0, draws = 0, goalsA = 0, goalsB = 0;
    for (const m of matches) {
      if (m.homeGoals == null || m.awayGoals == null) continue;
      const aHome = m.homeTeam.key === keyA;
      const gA = aHome ? m.homeGoals : m.awayGoals;
      const gB = aHome ? m.awayGoals : m.homeGoals;
      goalsA += gA;
      goalsB += gB;
      if (gA > gB) winsA++;
      else if (gA < gB) winsB++;
      else draws++;
    }
    return {
      teamA: teamDisplayName(keyA),
      teamB: teamDisplayName(keyB),
      matches,
      summary: {
        total: matches.length,
        winsA,
        draws,
        winsB,
        goalsA,
        goalsB,
      },
    };
  }

  /* ---------------------------------------------------------------- */
  /* 2. Team queries                                                    */
  /* ---------------------------------------------------------------- */

  teamRecord(
    team: string,
    opts: { season?: number; competition?: string; venue?: "home" | "away" | "any" } = {},
  ): TeamRecord & { teamKey: string } {
    return this.recordForKey(resolveTeamQuery(team), opts);
  }

  private recordForKey(
    key: string,
    opts: { season?: number; competition?: string; venue?: "home" | "away" | "any" } = {},
  ): TeamRecord & { teamKey: string } {
    const comp = opts.competition ? resolveCompetition(opts.competition) : null;
    const venue = opts.venue ?? "any";
    const pool = this.built.indexes.matchesByTeam.get(key) ?? [];
    let wins = 0, draws = 0, losses = 0, gf = 0, ga = 0, played = 0;
    for (const m of pool) {
      const isHome = m.homeTeam.key === key;
      if (venue === "home" && !isHome) continue;
      if (venue === "away" && isHome) continue;
      if (comp && m.competition !== comp) continue;
      if (opts.season != null && m.season !== opts.season) continue;
      if (m.homeGoals == null || m.awayGoals == null) continue;
      played++;
      const scored = isHome ? m.homeGoals : m.awayGoals;
      const conceded = isHome ? m.awayGoals : m.homeGoals;
      gf += scored;
      ga += conceded;
      if (scored > conceded) wins++;
      else if (scored < conceded) losses++;
      else draws++;
    }
    return {
      team: teamDisplayName(key),
      teamKey: key,
      matches: played,
      wins,
      draws,
      losses,
      goalsFor: gf,
      goalsAgainst: ga,
      goalDifference: gf - ga,
      winRate: played ? wins / played : 0,
    };
  }

  /** Competitions (with seasons + match counts) a team has played in. */
  teamCompetitions(team: string) {
    const key = resolveTeamQuery(team);
    const pool = this.built.indexes.matchesByTeam.get(key) ?? [];
    const byComp = new Map<CompetitionLabel, { seasons: Set<number>; matches: number }>();
    for (const m of pool) {
      const entry = byComp.get(m.competition) ?? { seasons: new Set<number>(), matches: 0 };
      entry.matches++;
      if (m.season != null) entry.seasons.add(m.season);
      byComp.set(m.competition, entry);
    }
    return {
      team: teamDisplayName(key),
      teamKey: key,
      competitions: [...byComp.entries()].map(([competition, e]) => ({
        competition,
        matches: e.matches,
        seasons: [...e.seasons].sort((a, b) => a - b),
      })),
    };
  }

  /* ---------------------------------------------------------------- */
  /* 3. Player queries                                                  */
  /* ---------------------------------------------------------------- */

  searchPlayers(filter: {
    name?: string;
    nationality?: string;
    club?: string;
    position?: string;
    minOverall?: number;
    brazilianClubsOnly?: boolean;
    limit?: number;
    sortByOverall?: boolean;
  }): Player[] {
    const limit = Math.min(Math.max(filter.limit ?? 20, 1), 200);
    let pool: Player[] = this.allPlayers;

    if (filter.nationality) {
      const nat = loose(filter.nationality);
      pool = pool.filter((p) => loose(p.nationality) === nat);
    }
    if (filter.club) {
      const clubKey = resolveTeamQuery(filter.club);
      const clubLoose = loose(filter.club);
      pool = pool.filter((p) => {
        if (!p.club) return false;
        if (p.clubKey && p.clubKey === clubKey) return true;
        return loose(p.club).includes(clubLoose);
      });
    }
    if (filter.brazilianClubsOnly) {
      pool = pool.filter((p) => p.clubKey != null && isBrazilianTeamKey(p.clubKey));
    }
    if (filter.position) {
      const pos = filter.position.toUpperCase();
      const groups: Record<string, string[]> = {
        FORWARD: ["ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"],
        MIDFIELDER: ["CAM", "CM", "CDM", "LM", "RM", "LAM", "RAM", "LCM", "RCM", "LDM", "RDM"],
        DEFENDER: ["CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"],
        GOALKEEPER: ["GK"],
      };
      const wanted = groups[pos] ?? [pos];
      pool = pool.filter((p) => p.position != null && wanted.includes(p.position));
    }
    if (filter.minOverall != null) {
      pool = pool.filter((p) => (p.overall ?? 0) >= filter.minOverall!);
    }
    if (filter.name) {
      const q = loose(filter.name);
      pool = pool.filter((p) => loose(p.name).includes(q));
    }
    if (filter.sortByOverall !== false) {
      pool = [...pool].sort(
        (a, b) => (b.overall ?? 0) - (a.overall ?? 0) || a.name.localeCompare(b.name),
      );
    }
    return pool.slice(0, limit);
  }

  /** Count + average rating of a nationality's players per club. */
  playersByClubSummary(nationality: string, brazilianClubsOnly = true) {
    const nat = loose(nationality);
    const pool = this.allPlayers.filter(
      (p) =>
        loose(p.nationality) === nat &&
        (!brazilianClubsOnly || (p.clubKey != null && isBrazilianTeamKey(p.clubKey))),
    );
    const byClub = new Map<string, { count: number; totalOverall: number; club: string }>();
    for (const p of pool) {
      const key = p.clubKey ?? loose(p.club ?? "unknown");
      const entry = byClub.get(key) ?? {
        count: 0,
        totalOverall: 0,
        club: p.clubKey ? teamDisplayName(p.clubKey) : (p.club ?? "Unknown"),
      };
      entry.count++;
      entry.totalOverall += p.overall ?? 0;
      byClub.set(key, entry);
    }
    return [...byClub.values()]
      .map((e) => ({
        club: e.club,
        players: e.count,
        averageOverall: e.count ? Math.round((e.totalOverall / e.count) * 10) / 10 : 0,
      }))
      .sort((a, b) => b.players - a.players || b.averageOverall - a.averageOverall);
  }

  /* ---------------------------------------------------------------- */
  /* 4. Competition queries                                             */
  /* ---------------------------------------------------------------- */

  standings(season: number, competition = "Brasileirão Série A"): StandingRow[] {
    const comp = resolveCompetition(competition) ?? "Brasileirão Série A";
    const pool = (this.built.indexes.matchesByCompetition.get(comp) ?? []).filter(
      (m) => m.season === season && m.homeGoals != null && m.awayGoals != null,
    );
    const table = new Map<string, StandingRow>();
    const ensure = (key: string): StandingRow => {
      let row = table.get(key);
      if (!row) {
        row = {
          rank: 0,
          team: teamDisplayName(key),
          matches: 0,
          wins: 0,
          draws: 0,
          losses: 0,
          goalsFor: 0,
          goalsAgainst: 0,
          goalDifference: 0,
          winRate: 0,
          points: 0,
        };
        table.set(key, row);
      }
      return row;
    };
    for (const m of pool) {
      const home = ensure(m.homeTeam.key);
      const away = ensure(m.awayTeam.key);
      const hg = m.homeGoals!;
      const ag = m.awayGoals!;
      home.matches++;
      away.matches++;
      home.goalsFor += hg;
      home.goalsAgainst += ag;
      away.goalsFor += ag;
      away.goalsAgainst += hg;
      if (hg > ag) {
        home.wins++;
        away.losses++;
        home.points += 3;
      } else if (hg < ag) {
        away.wins++;
        home.losses++;
        away.points += 3;
      } else {
        home.draws++;
        away.draws++;
        home.points += 1;
        away.points += 1;
      }
    }
    const rows = [...table.values()];
    for (const r of rows) {
      r.goalDifference = r.goalsFor - r.goalsAgainst;
      r.winRate = r.matches ? r.wins / r.matches : 0;
    }
    rows.sort(
      (a, b) =>
        b.points - a.points ||
        b.wins - a.wins ||
        b.goalDifference - a.goalDifference ||
        b.goalsFor - a.goalsFor ||
        a.team.localeCompare(b.team),
    );
    rows.forEach((r, i) => (r.rank = i + 1));
    if (rows.length > 0) rows[0].note = "Champion";
    if (comp === "Brasileirão Série A" && rows.length >= 20) {
      for (const r of rows.slice(-4)) r.note = r.note ? `${r.note}; Relegated` : "Relegated";
    }
    return rows;
  }

  /** Copa do Brasil "finals": matches in the last (max) round of each season. */
  cupFinals(season?: number): Match[] {
    const pool = this.built.indexes.matchesByCompetition.get("Copa do Brasil") ?? [];
    const bySeason = new Map<number, Match[]>();
    for (const m of pool) {
      if (m.season == null) continue;
      if (season != null && m.season !== season) continue;
      const arr = bySeason.get(m.season) ?? [];
      arr.push(m);
      bySeason.set(m.season, arr);
    }
    const finals: Match[] = [];
    for (const [s, matches] of [...bySeason.entries()].sort((a, b) => a[0] - b[0])) {
      let maxRound = -1;
      for (const m of matches) {
        const r = parseInt(m.round ?? "", 10);
        if (Number.isFinite(r) && r > maxRound) maxRound = r;
      }
      finals.push(...matches.filter((m) => parseInt(m.round ?? "", 10) === maxRound));
    }
    return finals;
  }

  /** Seasons available per competition. */
  competitionSeasons(): Record<string, number[]> {
    const out: Record<string, Set<number>> = {};
    for (const [comp, matches] of this.built.indexes.matchesByCompetition) {
      out[comp] = out[comp] ?? new Set();
      for (const m of matches) if (m.season != null) out[comp].add(m.season);
    }
    return Object.fromEntries(
      Object.entries(out).map(([k, v]) => [k, [...v].sort((a, b) => a - b)]),
    );
  }

  /* ---------------------------------------------------------------- */
  /* 5. Statistical analysis                                            */
  /* ---------------------------------------------------------------- */

  competitionStats(opts: { competition?: string; season?: number } = {}) {
    const comp = opts.competition ? resolveCompetition(opts.competition) : null;
    let played = 0, goals = 0, homeWins = 0, awayWins = 0, draws = 0;
    for (const m of this.matches) {
      if (comp && m.competition !== comp) continue;
      if (opts.season != null && m.season !== opts.season) continue;
      if (m.homeGoals == null || m.awayGoals == null) continue;
      played++;
      goals += m.homeGoals + m.awayGoals;
      if (m.homeGoals > m.awayGoals) homeWins++;
      else if (m.homeGoals < m.awayGoals) awayWins++;
      else draws++;
    }
    return {
      competition: comp ?? "All competitions",
      season: opts.season ?? "all",
      matchesPlayed: played,
      totalGoals: goals,
      averageGoalsPerMatch: played ? Math.round((goals / played) * 100) / 100 : 0,
      homeWins,
      draws,
      awayWins,
      homeWinRate: played ? Math.round((homeWins / played) * 1000) / 10 : 0,
      drawRate: played ? Math.round((draws / played) * 1000) / 10 : 0,
      awayWinRate: played ? Math.round((awayWins / played) * 1000) / 10 : 0,
    };
  }

  biggestWins(opts: { competition?: string; season?: number; limit?: number } = {}) {
    const comp = opts.competition ? resolveCompetition(opts.competition) : null;
    const limit = Math.min(Math.max(opts.limit ?? 10, 1), 100);
    const played = this.matches.filter(
      (m) =>
        m.homeGoals != null &&
        m.awayGoals != null &&
        (!comp || m.competition === comp) &&
        (opts.season == null || m.season === opts.season),
    );
    const withMargin = played.map((m) => ({
      match: m,
      margin: Math.abs(m.homeGoals! - m.awayGoals!),
      totalGoals: m.homeGoals! + m.awayGoals!,
    }));
    withMargin.sort((a, b) => b.margin - a.margin || b.totalGoals - a.totalGoals || a.match.date.localeCompare(b.match.date));
    return withMargin.slice(0, limit).map((w) => w.match);
  }

  /** Best home records (by win rate, min 10 home games). */
  bestHomeRecords(opts: { competition?: string; season?: number; limit?: number; minMatches?: number } = {}) {
    return this.bestVenueRecords("home", opts);
  }

  /** Best away records (by win rate, min 10 away games). */
  bestAwayRecords(opts: { competition?: string; season?: number; limit?: number; minMatches?: number } = {}) {
    return this.bestVenueRecords("away", opts);
  }

  private bestVenueRecords(
    venue: "home" | "away",
    opts: { competition?: string; season?: number; limit?: number; minMatches?: number },
  ): TeamRecord[] {
    const limit = Math.min(Math.max(opts.limit ?? 10, 1), 100);
    const minMatches = opts.minMatches ?? 10;
    const records: TeamRecord[] = [];
    for (const key of this.built.indexes.teams.keys()) {
      const rec = this.recordForKey(key, {
        season: opts.season,
        competition: opts.competition,
        venue,
      });
      if (rec.matches >= minMatches) records.push(rec);
    }
    records.sort(
      (a, b) =>
        b.winRate - a.winRate || b.wins - a.wins || b.goalDifference - a.goalDifference,
    );
    return records.slice(0, limit);
  }

  /** Top-scoring teams (goals for) in a season/competition. */
  topScoringTeams(opts: { season?: number; competition?: string; limit?: number } = {}) {
    const limit = Math.min(Math.max(opts.limit ?? 10, 1), 100);
    const records: TeamRecord[] = [];
    for (const key of this.built.indexes.teams.keys()) {
      const rec = this.recordForKey(key, {
        season: opts.season,
        competition: opts.competition,
      });
      if (rec.matches > 0) records.push(rec);
    }
    records.sort((a, b) => b.goalsFor - a.goalsFor || b.goalDifference - a.goalDifference);
    return records.slice(0, limit);
  }

  /* ---------------------------------------------------------------- */
  /* Dataset overview                                                   */
  /* ---------------------------------------------------------------- */

  private allPlayers: Player[] = [];

  bindPlayers(players: Player[]): this {
    this.allPlayers = players;
    return this;
  }

  overview(sourceRowCounts: Record<string, number>, duplicateCounts: Record<string, number>) {
    const seasons = new Set<number>();
    for (const m of this.matches) if (m.season != null) seasons.add(m.season);
    return {
      sources: sourceRowCounts,
      duplicatesMerged: duplicateCounts,
      uniqueMatches: this.matches.length,
      teams: this.built.indexes.teams.size,
      players: this.allPlayers.length,
      brazilianPlayers: this.allPlayers.filter((p) => p.nationality === "Brazil").length,
      competitions: this.competitionSeasons(),
      seasonRange: seasons.size
          ? [Math.min(...seasons), Math.max(...seasons)]
          : null,
    };
  }
}

/** Convenience: a fully wired query engine. */
export function createQueries(
  built: BuiltGraph,
  matches: Match[],
  players: Player[],
): SoccerQueries {
  return new SoccerQueries(built).bindMatches(matches).bindPlayers(players);
}
