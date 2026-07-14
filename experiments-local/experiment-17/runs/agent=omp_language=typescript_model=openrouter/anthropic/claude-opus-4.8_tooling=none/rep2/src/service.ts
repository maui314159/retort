/**
 * Context
 * -------
 * The query layer over the loaded `Dataset`. A single `SoccerGraph` instance
 * holds the in-memory matches + players and answers the five capability
 * categories from the spec:
 *
 *   1. Match queries      — findMatches (team/competition/season/date range)
 *   2. Team queries       — teamRecord, headToHead
 *   3. Player queries     — findPlayers (name/nationality/club/position)
 *   4. Competition queries — standings (points table computed from results)
 *   5. Statistical analysis — competitionStats, biggestWins
 *
 * Methods return plain data structures; all human-readable formatting lives in
 * `format.ts`, so the same query results can be reused by tests or other front
 * ends without re-parsing strings.
 */

import { loadDataset, type Dataset } from "./loader.js";
import type { Competition, Match, Outcome, Player, TeamRecord } from "./models.js";
import { foldText, looseMatches, parseTeam, teamMatches } from "./normalize.js";

/** Canonical competition slugs accepted by tools / NL, mapped to labels. */
export const COMPETITIONS: Record<string, Competition> = {
  "serie a": "Brasileirão Série A",
  brasileirao: "Brasileirão Série A",
  "brasileirão": "Brasileirão Série A",
  "serie b": "Brasileirão Série B",
  "serie c": "Brasileirão Série C",
  "copa do brasil": "Copa do Brasil",
  "brazilian cup": "Copa do Brasil",
  libertadores: "Copa Libertadores",
  "copa libertadores": "Copa Libertadores",
};

/** Resolve a free-text competition name to a canonical label, if recognized. */
export function resolveCompetition(value: string | undefined): Competition | undefined {
  if (!value) return undefined;
  return COMPETITIONS[foldText(value)];
}

export interface MatchFilter {
  /** Match on either side (home or away). */
  team?: string;
  /** Require this specific home team. */
  homeTeam?: string;
  /** Require this specific away team. */
  awayTeam?: string;
  /** Require BOTH teams (in any order) — used for head-to-head listings. */
  opponent?: string;
  competition?: Competition;
  season?: number;
  /** Inclusive ISO date bounds, "YYYY-MM-DD". */
  from?: string;
  to?: string;
  /** Cap on returned matches (newest first). 0/undefined = no cap. */
  limit?: number;
}

/** Outcome of a match from `team`'s perspective. */
function outcomeFor(match: Match, isHome: boolean): Outcome {
  const gf = isHome ? match.homeGoals : match.awayGoals;
  const ga = isHome ? match.awayGoals : match.homeGoals;
  if (gf > ga) return "win";
  if (gf < ga) return "loss";
  return "draw";
}

export class SoccerGraph {
  readonly matches: readonly Match[];
  readonly players: readonly Player[];

  constructor(dataset: Dataset) {
    // Sort matches newest-first once; most queries want recent results first
    // and standings/stats are order-independent.
    this.matches = [...dataset.matches].sort((a, b) => (b.date?.epoch ?? 0) - (a.date?.epoch ?? 0));
    this.players = dataset.players;
  }

  /** Build a graph from the bundled CSVs (or a custom data directory). */
  static load(dir?: string): SoccerGraph {
    return new SoccerGraph(loadDataset(dir));
  }

  /** Find matches by any combination of team/competition/season/date filters. */
  findMatches(filter: MatchFilter): Match[] {
    const fromEpoch = filter.from ? Date.parse(`${filter.from}T00:00:00Z`) : undefined;
    const toEpoch = filter.to ? Date.parse(`${filter.to}T00:00:00Z`) : undefined;

    const results = this.matches.filter((m) => {
      if (filter.competition && m.competition !== filter.competition) return false;
      if (filter.season !== undefined && m.season !== filter.season) return false;

      if (filter.team && !(teamMatches(filter.team, m.homeTeamRaw) || teamMatches(filter.team, m.awayTeamRaw)))
        return false;
      if (filter.homeTeam && !teamMatches(filter.homeTeam, m.homeTeamRaw)) return false;
      if (filter.awayTeam && !teamMatches(filter.awayTeam, m.awayTeamRaw)) return false;
      if (filter.opponent && !(teamMatches(filter.opponent, m.homeTeamRaw) || teamMatches(filter.opponent, m.awayTeamRaw)))
        return false;

      if (fromEpoch !== undefined && (m.date?.epoch ?? -Infinity) < fromEpoch) return false;
      if (toEpoch !== undefined && (m.date?.epoch ?? Infinity) > toEpoch) return false;
      return true;
    });

    return filter.limit && filter.limit > 0 ? results.slice(0, filter.limit) : results;
  }

  /**
   * Win/draw/loss + goals record for a team, optionally scoped by competition,
   * season, and venue ("home" / "away" / "all").
   */
  teamRecord(
    team: string,
    opts: { competition?: Competition; season?: number; venue?: "home" | "away" | "all" } = {},
  ): TeamRecord {
    const venue = opts.venue ?? "all";
    const record: TeamRecord = { matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0 };

    for (const m of this.matches) {
      if (opts.competition && m.competition !== opts.competition) continue;
      if (opts.season !== undefined && m.season !== opts.season) continue;

      const isHome = teamMatches(team, m.homeTeamRaw);
      const isAway = teamMatches(team, m.awayTeamRaw);
      if (!isHome && !isAway) continue;
      if (venue === "home" && !isHome) continue;
      if (venue === "away" && !isAway) continue;

      // A team playing itself is impossible; prefer the home perspective.
      const asHome = isHome;
      record.matches++;
      record.goalsFor += asHome ? m.homeGoals : m.awayGoals;
      record.goalsAgainst += asHome ? m.awayGoals : m.homeGoals;
      const o = outcomeFor(m, asHome);
      if (o === "win") record.wins++;
      else if (o === "draw") record.draws++;
      else record.losses++;
    }
    return record;
  }

  /** Head-to-head summary between two teams across all (or scoped) matches. */
  headToHead(
    teamA: string,
    teamB: string,
    opts: { competition?: Competition; season?: number } = {},
  ): { matches: Match[]; aWins: number; bWins: number; draws: number; aGoals: number; bGoals: number } {
    const matches = this.findMatches({
      team: teamA,
      opponent: teamB,
      competition: opts.competition,
      season: opts.season,
    });
    let aWins = 0;
    let bWins = 0;
    let draws = 0;
    let aGoals = 0;
    let bGoals = 0;
    for (const m of matches) {
      const aHome = teamMatches(teamA, m.homeTeamRaw);
      const aFor = aHome ? m.homeGoals : m.awayGoals;
      const bFor = aHome ? m.awayGoals : m.homeGoals;
      aGoals += aFor;
      bGoals += bFor;
      if (aFor > bFor) aWins++;
      else if (aFor < bFor) bWins++;
      else draws++;
    }
    return { matches, aWins, bWins, draws, aGoals, bGoals };
  }

  /** Search players by name/nationality/club/position; sorted by overall desc. */
  findPlayers(filter: {
    name?: string;
    nationality?: string;
    club?: string;
    position?: string;
    minOverall?: number;
    limit?: number;
  }): Player[] {
    const results = this.players.filter((p) => {
      if (filter.name && !looseMatches(filter.name, p.name)) return false;
      if (filter.nationality && foldText(p.nationality) !== foldText(filter.nationality)) return false;
      if (filter.club && !looseMatches(filter.club, p.club)) return false;
      if (filter.position && foldText(p.position) !== foldText(filter.position)) return false;
      if (filter.minOverall !== undefined && (p.overall ?? 0) < filter.minOverall) return false;
      return true;
    });
    results.sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
    return filter.limit && filter.limit > 0 ? results.slice(0, filter.limit) : results;
  }

  /**
   * League table for a competition+season computed from match results
   * (3 pts win / 1 draw), tie-broken by goal difference then goals for.
   * Teams are identified by suffix-aware full key so Atlético-MG and
   * Atlético-GO stay distinct.
   */
  standings(competition: Competition, season: number): StandingRow[] {
    const table = new Map<string, StandingRow>();

    const ensure = (raw: string): StandingRow => {
      const t = parseTeam(raw);
      let row = table.get(t.fullKey);
      if (!row) {
        row = {
          team: t.suffix ? `${t.displayBase}-${t.suffix.toUpperCase()}` : t.displayBase,
          played: 0,
          wins: 0,
          draws: 0,
          losses: 0,
          goalsFor: 0,
          goalsAgainst: 0,
          points: 0,
        };
        table.set(t.fullKey, row);
      }
      return row;
    };

    for (const m of this.matches) {
      if (m.competition !== competition || m.season !== season) continue;
      const home = ensure(m.homeTeamRaw);
      const away = ensure(m.awayTeamRaw);
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

    return [...table.values()].sort((a, b) => {
      if (b.points !== a.points) return b.points - a.points;
      const gdA = a.goalsFor - a.goalsAgainst;
      const gdB = b.goalsFor - b.goalsAgainst;
      if (gdB !== gdA) return gdB - gdA;
      if (b.goalsFor !== a.goalsFor) return b.goalsFor - a.goalsFor;
      return a.team.localeCompare(b.team);
    });
  }

  /** Aggregate competition statistics for a season (or all seasons). */
  competitionStats(competition: Competition, season?: number): CompetitionStats {
    let matches = 0;
    let totalGoals = 0;
    let homeWins = 0;
    let awayWins = 0;
    let draws = 0;
    for (const m of this.matches) {
      if (m.competition !== competition) continue;
      if (season !== undefined && m.season !== season) continue;
      matches++;
      totalGoals += m.homeGoals + m.awayGoals;
      if (m.homeGoals > m.awayGoals) homeWins++;
      else if (m.homeGoals < m.awayGoals) awayWins++;
      else draws++;
    }
    return {
      competition,
      season,
      matches,
      totalGoals,
      goalsPerMatch: matches ? totalGoals / matches : 0,
      homeWins,
      awayWins,
      draws,
      homeWinRate: matches ? homeWins / matches : 0,
    };
  }

  /** Largest goal-difference victories, optionally scoped by competition. */
  biggestWins(opts: { competition?: Competition; season?: number; limit?: number } = {}): Match[] {
    const scoped = this.matches.filter((m) => {
      if (opts.competition && m.competition !== opts.competition) return false;
      if (opts.season !== undefined && m.season !== opts.season) return false;
      return true;
    });
    scoped.sort((a, b) => {
      const diffA = Math.abs(a.homeGoals - a.awayGoals);
      const diffB = Math.abs(b.homeGoals - b.awayGoals);
      if (diffB !== diffA) return diffB - diffA;
      return b.homeGoals + b.awayGoals - (a.homeGoals + a.awayGoals);
    });
    return opts.limit && opts.limit > 0 ? scoped.slice(0, opts.limit) : scoped;
  }
}

export interface StandingRow {
  team: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  points: number;
}

export interface CompetitionStats {
  competition: Competition;
  season?: number;
  matches: number;
  totalGoals: number;
  goalsPerMatch: number;
  homeWins: number;
  awayWins: number;
  draws: number;
  homeWinRate: number;
}
