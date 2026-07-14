/**
 * brazilian-soccer-mcp / src/store.ts
 *
 * In-memory query engine over the loaded data.
 *
 * Context block:
 * The store holds all matches and players in flat arrays and exposes the
 * query methods that back the MCP tools. Team matching is core-based: a query
 * for "Flamengo" matches every occurrence whose normalized core is "flamengo"
 * (covering "Flamengo-RJ", "Flamengo", ...), and a query that carries a state
 * (e.g. "Atlético-MG") additionally filters to that state so same-nickname
 * clubs stay distinct. Competition filtering uses canonical labels produced by
 * the loader, with case/diacritic-insensitive substring matching so callers can
 * pass "brasileirao" or "Brasileirão". Aggregate methods (standings, team
 * stats, head-to-head, biggest wins, average goals) compute from the raw match
 * list — no precomputed tables — keeping the store trivially consistent.
 */
import type { LoadedData } from "./loader.js";
import type {
  Match,
  Player,
  PlayerSort,
  StandingRow,
  TeamStat,
  Venue,
} from "./types.js";
import { canonicalCompetition, extractParts, positionGroupOf } from "./normalize.js";

/** Filter options for match search. */
export interface MatchFilter {
  team?: string;
  opponent?: string;
  competition?: string;
  season?: number;
  from?: string; // ISO YYYY-MM-DD
  to?: string; // ISO YYYY-MM-DD
  venue?: Venue;
}

/** Sort options for matches. */
export type MatchSort = "date_asc" | "date_desc";

const POSITION_GROUP_CODES: Record<string, Set<string>> = {
  goalkeeper: new Set(["GK"]),
  defender: new Set(["CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"]),
  midfielder: new Set(["CDM", "CM", "CAM", "LM", "RM", "LDM", "RDM", "LCM", "RCM", "LAM", "RAM"]),
  forward: new Set(["ST", "LS", "RS", "LW", "RW", "LF", "CF", "RF"]),
};

/** True if `competition` matches `query` (canonical, case/diacritic-insensitive). */
function competitionMatches(competition: string, query: string): boolean {
  return canonicalCompetition(competition) === canonicalCompetition(query);
}
export class SoccerStore {
  readonly matches: readonly Match[];
  readonly players: readonly Player[];
  readonly competitions: readonly string[];
  readonly competitionCounts: Record<string, number>;
  readonly competitionSeasons: Record<string, { min: number; max: number }>;
  /** Cores of clubs that appear in Brazilian domestic competitions. */
  readonly brazilianClubKeys: Set<string>;

  constructor(data: LoadedData) {
    this.matches = data.matches;
    this.players = data.players;
    this.competitions = data.competitions;
    this.competitionCounts = data.competitionCounts;
    this.competitionSeasons = data.competitionSeasons;

    // A club counts as "Brazilian" if its core matches any team that played in
    // a Brazilian domestic competition (Brasileirão variants or Copa do Brasil).
    // Cores (not disambiguated keys) so FIFA club cores can match.
    const keys = new Set<string>();
    for (const m of this.matches) {
      if (
        m.competition === "Brasileirão" ||
        m.competition === "Brasileirão Série B" ||
        m.competition === "Brasileirão Série C" ||
        m.competition === "Copa do Brasil"
      ) {
        keys.add(m.homeTeamCore);
        keys.add(m.awayTeamCore);
      }
    }
    this.brazilianClubKeys = keys;
  }
  // ---- Team query helper ------------------------------------------------

  /** Parse a team query into core + optional state for matching. */
  private static teamQuery(name: string): { core: string; state: string | null } {
    const p = extractParts(name);
    return { core: p.core, state: p.state };
  }

  /** True if a match side (core, state) matches a query (core; state if given). */
  private static sideMatches(
    sideCore: string,
    sideState: string | null,
    q: { core: string; state: string | null },
  ): boolean {
    if (sideCore !== q.core) return false;
    if (q.state && sideState !== q.state) return false;
    return true;
  }

  // ---- Match queries ----------------------------------------------------

  /** Search matches by the given filter, sorted and optionally limited. */
  searchMatches(
    filter: MatchFilter,
    opts: { sort?: MatchSort; limit?: number } = {},
  ): Match[] {
    const tq = filter.team ? SoccerStore.teamQuery(filter.team) : null;
    const oq = filter.opponent ? SoccerStore.teamQuery(filter.opponent) : null;
    let out = this.matches.filter((m) => {
      if (tq) {
        const isHome = SoccerStore.sideMatches(m.homeTeamCore, m.homeState, tq);
        const isAway = SoccerStore.sideMatches(m.awayTeamCore, m.awayState, tq);
        if (!isHome && !isAway) return false;
        if (filter.venue === "home" && !isHome) return false;
        if (filter.venue === "away" && !isAway) return false;
        if (oq) {
          // Opponent must be the OTHER side from the matched team.
          const oppAway = isHome && SoccerStore.sideMatches(m.awayTeamCore, m.awayState, oq);
          const oppHome = isAway && SoccerStore.sideMatches(m.homeTeamCore, m.homeState, oq);
          if (!oppAway && !oppHome) return false;
        }
      } else if (oq) {
        const h = SoccerStore.sideMatches(m.homeTeamCore, m.homeState, oq);
        const a = SoccerStore.sideMatches(m.awayTeamCore, m.awayState, oq);
        if (!h && !a) return false;
      }
      if (filter.competition && !competitionMatches(m.competition, filter.competition)) return false;
      if (filter.season != null && m.season !== filter.season) return false;
      if (filter.from && (m.date == null || m.date < filter.from)) return false;
      if (filter.to && (m.date == null || m.date > filter.to)) return false;
      return true;
    });

    const sort = opts.sort ?? "date_desc";
    out = out.slice().sort((a, b) => {
      const da = a.date ?? "";
      const db = b.date ?? "";
      return sort === "date_asc" ? da.localeCompare(db) : db.localeCompare(da);
    });

    return opts.limit != null ? out.slice(0, opts.limit) : out;
  }
  /** Head-to-head: all matches between two teams + per-team W/D/L. */
  headToHead(team1: string, team2: string): {
    matches: Match[];
    team1: string;
    team2: string;
    team1Wins: number;
    team2Wins: number;
    draws: number;
  } {
    const q1 = SoccerStore.teamQuery(team1);
    const q2 = SoccerStore.teamQuery(team2);
    const matches = this.matches
      .filter((m) => {
        const t1Home = SoccerStore.sideMatches(m.homeTeamCore, m.homeState, q1);
        const t1Away = SoccerStore.sideMatches(m.awayTeamCore, m.awayState, q1);
        const t2Home = SoccerStore.sideMatches(m.homeTeamCore, m.homeState, q2);
        const t2Away = SoccerStore.sideMatches(m.awayTeamCore, m.awayState, q2);
        const t1In = t1Home || t1Away;
        const t2In = t2Home || t2Away;
        if (!t1In || !t2In) return false;
        // Same team on both sides (e.g. ambiguous bare query) — skip.
        if (q1.core === q2.core && (!q1.state || !q2.state)) return false;
        return true;
      })
      .sort((a, b) => (b.date ?? "").localeCompare(a.date ?? ""));

    let team1Wins = 0;
    let team2Wins = 0;
    let draws = 0;
    for (const m of matches) {
      const hg = m.homeGoal;
      const ag = m.awayGoal;
      if (hg == null || ag == null) continue;
      const t1IsHome = SoccerStore.sideMatches(m.homeTeamCore, m.homeState, q1);
      const t1Goals = t1IsHome ? hg : ag;
      const t2Goals = t1IsHome ? ag : hg;
      if (t1Goals > t2Goals) team1Wins++;
      else if (t1Goals < t2Goals) team2Wins++;
      else draws++;
    }
    return { matches, team1, team2, team1Wins, team2Wins, draws };
  }

  // ---- Team queries -----------------------------------------------------

  /** Aggregate stats for a team, optionally filtered by competition/season/venue. */
  teamStats(
    team: string,
    opts: { competition?: string; season?: number; venue?: Venue } = {},
  ): TeamStat {
    const q = SoccerStore.teamQuery(team);
    let wins = 0;
    let draws = 0;
    let losses = 0;
    let goalsFor = 0;
    let goalsAgainst = 0;
    let matches = 0;

    for (const m of this.matches) {
      const isHome = SoccerStore.sideMatches(m.homeTeamCore, m.homeState, q);
      const isAway = SoccerStore.sideMatches(m.awayTeamCore, m.awayState, q);
      if (!isHome && !isAway) continue;
      if (opts.venue === "home" && !isHome) continue;
      if (opts.venue === "away" && !isAway) continue;
      if (opts.competition && !competitionMatches(m.competition, opts.competition)) continue;
      if (opts.season != null && m.season !== opts.season) continue;
      const hg = m.homeGoal;
      const ag = m.awayGoal;
      if (hg == null || ag == null) continue;
      const gf = isHome ? hg : ag;
      const ga = isHome ? ag : hg;
      matches++;
      goalsFor += gf;
      goalsAgainst += ga;
      if (gf > ga) wins++;
      else if (gf < ga) losses++;
      else draws++;
    }

    const winRate = matches > 0 ? wins / matches : 0;
    return { team, matches, wins, draws, losses, goalsFor, goalsAgainst, winRate };
  }

  // ---- Player queries ---------------------------------------------------

  /** Search players by name/nationality/club/position, sorted and limited. */
  searchPlayers(filter: {
    name?: string;
    nationality?: string;
    club?: string;
    position?: string;
    positionGroup?: string;
    minOverall?: number;
    brazilianClubsOnly?: boolean;
    sort?: PlayerSort;
    limit?: number;
  }): Player[] {
    const nameKey = filter.name ? filter.name.toLowerCase() : null;
    const natKey = filter.nationality ? filter.nationality.toLowerCase() : null;
    const clubKeyFilter = filter.club ? extractParts(filter.club).core : null;
    const posFilter = filter.position ? filter.position.toUpperCase().trim() : null;
    const groupFilter = filter.positionGroup ? filter.positionGroup.toLowerCase() : null;

    let out = this.players.filter((p) => {
      if (nameKey && !p.name.toLowerCase().includes(nameKey)) return false;
      if (natKey && !p.nationality.toLowerCase().includes(natKey)) return false;
      if (clubKeyFilter && p.clubKey !== clubKeyFilter) return false;
      if (posFilter && p.position !== posFilter) return false;
      if (groupFilter) {
        const codes = POSITION_GROUP_CODES[groupFilter];
        const inGroup = codes ? codes.has(p.position) : false;
        if (!inGroup) return false;
      }
      if (filter.minOverall != null && (p.overall ?? 0) < filter.minOverall) return false;
      if (filter.brazilianClubsOnly && !this.brazilianClubKeys.has(p.clubKey)) return false;
      return true;
    });

    const sort = filter.sort ?? "overall";
    out = out.slice().sort((a, b) => {
      switch (sort) {
        case "overall":
          return (b.overall ?? -1) - (a.overall ?? -1) || a.name.localeCompare(b.name);
        case "potential":
          return (b.potential ?? -1) - (a.potential ?? -1) || a.name.localeCompare(b.name);
        case "age":
          return (a.age ?? 999) - (b.age ?? 999) || a.name.localeCompare(b.name);
        case "name":
          return a.name.localeCompare(b.name);
      }
    });

    return filter.limit != null ? out.slice(0, filter.limit) : out;
  }

  // ---- Competition queries ----------------------------------------------

  /** Compute a points-based standings table for a competition+season. */
  standings(competition: string, season: number): StandingRow[] {
    const table = new Map<string, StandingRow>();
    const ensure = (team: string): StandingRow => {
      let row = table.get(team);
      if (!row) {
        row = {
          team,
          played: 0,
          wins: 0,
          draws: 0,
          losses: 0,
          goalsFor: 0,
          goalsAgainst: 0,
          goalDifference: 0,
          points: 0,
        };
        table.set(team, row);
      }
      return row;
    };

    for (const m of this.matches) {
      if (!competitionMatches(m.competition, competition)) continue;
      if (m.season !== season) continue;
      const hg = m.homeGoal;
      const ag = m.awayGoal;
      if (hg == null || ag == null) continue;
      const home = ensure(m.homeTeam);
      const away = ensure(m.awayTeam);
      home.played++;
      away.played++;
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
    for (const r of rows) r.goalDifference = r.goalsFor - r.goalsAgainst;
    return rows.sort(
      (a, b) =>
        b.points - a.points ||
        b.wins - a.wins ||
        b.goalDifference - a.goalDifference ||
        b.goalsFor - a.goalsFor ||
        a.team.localeCompare(b.team),
    );
  }

  // ---- Statistical analysis --------------------------------------------

  /** Biggest victories (by goal margin) across the dataset. */
  biggestWins(
    opts: { competition?: string; season?: number; limit?: number } = {},
  ): Match[] {
    let out = this.matches.filter((m) => {
      if (m.homeGoal == null || m.awayGoal == null) return false;
      if (opts.competition && !competitionMatches(m.competition, opts.competition)) return false;
      if (opts.season != null && m.season !== opts.season) return false;
      return true;
    });
    out = out.slice().sort((a, b) => {
      const mb = Math.abs((b.homeGoal ?? 0) - (b.awayGoal ?? 0));
      const ma = Math.abs((a.homeGoal ?? 0) - (a.awayGoal ?? 0));
      if (mb !== ma) return mb - ma;
      return (b.homeGoal ?? 0) + (b.awayGoal ?? 0) - ((a.homeGoal ?? 0) + (a.awayGoal ?? 0));
    });
    return opts.limit != null ? out.slice(0, opts.limit) : out;
  }

  /** Average goals + home/draw/away win rates for a competition/season. */
  averageGoals(opts: { competition?: string; season?: number } = {}): {
    matches: number;
    totalGoals: number;
    averageGoalsPerMatch: number;
    homeWins: number;
    draws: number;
    awayWins: number;
    homeWinRate: number;
    drawRate: number;
    awayWinRate: number;
  } {
    let count = 0;
    let totalGoals = 0;
    let homeWins = 0;
    let draws = 0;
    let awayWins = 0;
    for (const m of this.matches) {
      if (opts.competition && !competitionMatches(m.competition, opts.competition)) continue;
      if (opts.season != null && m.season !== opts.season) continue;
      const hg = m.homeGoal;
      const ag = m.awayGoal;
      if (hg == null || ag == null) continue;
      count++;
      totalGoals += hg + ag;
      if (hg > ag) homeWins++;
      else if (hg < ag) awayWins++;
      else draws++;
    }
    return {
      matches: count,
      totalGoals,
      averageGoalsPerMatch: count > 0 ? totalGoals / count : 0,
      homeWins,
      draws,
      awayWins,
      homeWinRate: count > 0 ? homeWins / count : 0,
      drawRate: count > 0 ? draws / count : 0,
      awayWinRate: count > 0 ? awayWins / count : 0,
    };
  }

  // ---- Discovery --------------------------------------------------------

  /** Distinct team display names for a competition/season. */
  listTeams(opts: { competition?: string; season?: number } = {}): string[] {
    const set = new Map<string, string>(); // key -> display
    for (const m of this.matches) {
      if (opts.competition && !competitionMatches(m.competition, opts.competition)) continue;
      if (opts.season != null && m.season !== opts.season) continue;
      set.set(m.homeTeamKey, m.homeTeam);
      set.set(m.awayTeamKey, m.awayTeam);
    }
    return [...set.values()].sort((a, b) => a.localeCompare(b));
  }

  /** Known traditional derby pairings (normalized keys). */
  private static readonly DERBY_PAIRS: ReadonlyArray<readonly [string, string]> = [
    ["flamengo", "fluminense"], // Fla-Flu
    ["flamengo", "vasco"], // Rivalidade
    ["flamengo", "botafogo"],
    ["vasco", "botafogo"],
    ["fluminense", "botafogo"],
    ["corinthians", "sao paulo"], // Majestoso
    ["corinthians", "palmeiras"], // Paulista
    ["palmeiras", "sao paulo"], // Choque-Rei
    ["gremio", "internacional"], // Grenal
    ["atletico", "cruzeiro"], // Clássico Mineiro
    ["bahia", "vitoria"], // Ba-Vi
    ["fortaleza", "ceara"], // Clássico-Rei
    ["sport", "nautico"], // Clássico dos Clássicos
    ["atletico", "parana"], // Atlético-PR x Paraná (approx)
  ];

  /** Find derby matches in a season (or all seasons), matching on team cores. */
  findDerbies(opts: { season?: number; competition?: string; limit?: number } = {}): Match[] {
    const pairs = SoccerStore.DERBY_PAIRS.map(
      ([a, b]) => [extractParts(a).core, extractParts(b).core] as const,
    );
    let out = this.matches.filter((m) => {
      const cores = new Set([m.homeTeamCore, m.awayTeamCore]);
      const isDerby = pairs.some(([a, b]) => cores.has(a) && cores.has(b) && a !== b);
      if (!isDerby) return false;
      if (opts.season != null && m.season !== opts.season) return false;
      if (opts.competition && !competitionMatches(m.competition, opts.competition)) return false;
      return true;
    });
    out = out.slice().sort((a, b) => (b.date ?? "").localeCompare(a.date ?? ""));
    return opts.limit != null ? out.slice(0, opts.limit) : out;
  }
}

/** Re-export so consumers don't need to import positionGroupOf separately. */
export { positionGroupOf };
