/**
 * Context
 * -------
 * Pure query/aggregation layer over a DataStore. These functions implement the
 * five capability areas from the spec (match, team, player, competition,
 * statistics) and are deliberately free of any MCP/transport concerns so they
 * are directly unit-testable by the BDD suite. The MCP tool layer (server.ts)
 * is a thin adapter that calls these and formats the result.
 *
 * Team matching: a query term is normalized with `normalizeTeam`, then a stored
 * team matches when its canonical key equals the query key, or either key is a
 * whitespace-bounded substring of the other ("sao paulo" ⊂ "sao paulo fc").
 */

import { normalizeTeam, normalizeText, UF_CODES } from "./normalize.js";
import type { DataStore } from "./store.js";
import type {
  Competition,
  Match,
  Outcome,
  Player,
  TeamRecord,
} from "./types.js";

/**
 * True when a stored team key matches a query key.
 *
 * Exact match, or one key equals the other plus a trailing STATE (UF) token.
 * This lets a plain query ("palmeiras", "sao paulo") match a state-suffixed
 * stored key ("palmeiras sp", "sao paulo sp") while keeping genuinely different
 * clubs apart: "santos" must NOT match "santos laguna" ("laguna" is not a UF),
 * and "atletico mg" must NOT match "atletico go".
 */
export function teamKeyMatches(storedKey: string, queryKey: string): boolean {
  if (queryKey === "" || storedKey === "") return false;
  if (storedKey === queryKey) return true;

  const a = storedKey.split(" ");
  const b = queryKey.split(" ");
  const [shorter, longer] = a.length <= b.length ? [a, b] : [b, a];

  // Every token of the shorter key must prefix-match the longer key...
  for (let i = 0; i < shorter.length; i++) {
    if (shorter[i] !== longer[i]) return false;
  }
  // ...and the extra trailing tokens of the longer key must all be UF codes.
  for (let i = shorter.length; i < longer.length; i++) {
    if (!UF_CODES[longer[i].toUpperCase()]) return false;
  }
  return true;
}

export type Side = "home" | "away" | "either";

export interface MatchFilter {
  team?: string;
  /** Restrict `team` to home or away appearances. Default: either. */
  side?: Side;
  /** Second team for head-to-head / fixture queries. */
  opponent?: string;
  competition?: Competition;
  season?: number;
  /** Inclusive ISO date lower bound (YYYY-MM-DD). */
  from?: string;
  /** Inclusive ISO date upper bound (YYYY-MM-DD). */
  to?: string;
}

/** Filter matches by any combination of team/opponent/competition/season/date. */
export function findMatches(store: DataStore, filter: MatchFilter): Match[] {
  const teamKey = filter.team ? normalizeTeam(filter.team) : null;
  const oppKey = filter.opponent ? normalizeTeam(filter.opponent) : null;
  const side = filter.side ?? "either";

  const result = store.matches.filter((m) => {
    if (filter.competition && m.competition !== filter.competition) return false;
    if (filter.season != null && m.season !== filter.season) return false;
    if (filter.from && (m.date == null || m.date < filter.from)) return false;
    if (filter.to && (m.date == null || m.date > filter.to)) return false;

    if (teamKey) {
      const onHome = teamKeyMatches(m.homeKey, teamKey);
      const onAway = teamKeyMatches(m.awayKey, teamKey);
      if (side === "home" && !onHome) return false;
      if (side === "away" && !onAway) return false;
      if (side === "either" && !onHome && !onAway) return false;
    }

    if (oppKey) {
      const oppHome = teamKeyMatches(m.homeKey, oppKey);
      const oppAway = teamKeyMatches(m.awayKey, oppKey);
      if (!oppHome && !oppAway) return false;
      // When both team and opponent are set, require them on opposite sides.
      if (teamKey) {
        const teamHome = teamKeyMatches(m.homeKey, teamKey);
        const valid = (teamHome && oppAway) || (!teamHome && oppHome);
        if (!valid) return false;
      }
    }

    return true;
  });

  // Most recent first; matches without a date sort last.
  result.sort((a, b) => (b.date ?? "").localeCompare(a.date ?? ""));
  return result;
}

/** Outcome of a match from the perspective of the team on `side`. */
export function outcomeFor(m: Match, side: "home" | "away"): Outcome | null {
  if (m.homeGoal == null || m.awayGoal == null) return null;
  const diff = m.homeGoal - m.awayGoal;
  if (diff === 0) return "draw";
  const homeWon = diff > 0;
  if (side === "home") return homeWon ? "win" : "loss";
  return homeWon ? "loss" : "win";
}

function emptyRecord(): TeamRecord {
  return {
    matches: 0,
    wins: 0,
    draws: 0,
    losses: 0,
    goalsFor: 0,
    goalsAgainst: 0,
  };
}

export interface TeamStats {
  team: string;
  teamKey: string;
  overall: TeamRecord;
  home: TeamRecord;
  away: TeamRecord;
}

/** Aggregate a team's record over a filtered set of matches. */
export function teamStats(
  store: DataStore,
  team: string,
  filter: Omit<MatchFilter, "team" | "side" | "opponent"> = {},
): TeamStats {
  const teamKey = normalizeTeam(team);
  const matches = findMatches(store, { ...filter, team });

  const overall = emptyRecord();
  const home = emptyRecord();
  const away = emptyRecord();

  for (const m of matches) {
    if (m.homeGoal == null || m.awayGoal == null) continue;
    const onHome = teamKeyMatches(m.homeKey, teamKey);
    const side: "home" | "away" = onHome ? "home" : "away";
    const gf = side === "home" ? m.homeGoal : m.awayGoal;
    const ga = side === "home" ? m.awayGoal : m.homeGoal;
    const bucket = side === "home" ? home : away;
    const outcome = outcomeFor(m, side)!;

    for (const rec of [overall, bucket]) {
      rec.matches++;
      rec.goalsFor += gf;
      rec.goalsAgainst += ga;
      if (outcome === "win") rec.wins++;
      else if (outcome === "draw") rec.draws++;
      else rec.losses++;
    }
  }

  return { team, teamKey, overall, home, away };
}

export interface HeadToHead {
  teamA: string;
  teamB: string;
  matches: Match[];
  aWins: number;
  bWins: number;
  draws: number;
  aGoals: number;
  bGoals: number;
}

/** Compute the head-to-head record between two teams. */
export function headToHead(
  store: DataStore,
  teamA: string,
  teamB: string,
  filter: Omit<MatchFilter, "team" | "opponent" | "side"> = {},
): HeadToHead {
  const aKey = normalizeTeam(teamA);
  const matches = findMatches(store, { ...filter, team: teamA, opponent: teamB });

  let aWins = 0;
  let bWins = 0;
  let draws = 0;
  let aGoals = 0;
  let bGoals = 0;

  for (const m of matches) {
    if (m.homeGoal == null || m.awayGoal == null) continue;
    const aHome = teamKeyMatches(m.homeKey, aKey);
    const aScore = aHome ? m.homeGoal : m.awayGoal;
    const bScore = aHome ? m.awayGoal : m.homeGoal;
    aGoals += aScore;
    bGoals += bScore;
    if (aScore > bScore) aWins++;
    else if (aScore < bScore) bWins++;
    else draws++;
  }

  return { teamA, teamB, matches, aWins, bWins, draws, aGoals, bGoals };
}

export interface StandingRow {
  team: string;
  teamKey: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDiff: number;
  points: number;
}

/**
 * Compute a league table for a competition+season from match results.
 * 3 points for a win, 1 for a draw. Sorted by points, then GD, then GF.
 */
export function standings(
  store: DataStore,
  competition: Competition,
  season: number,
): StandingRow[] {
  const rows = new Map<string, StandingRow>();

  const ensure = (key: string, display: string): StandingRow => {
    let row = rows.get(key);
    if (!row) {
      row = {
        team: display,
        teamKey: key,
        played: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        goalsFor: 0,
        goalsAgainst: 0,
        goalDiff: 0,
        points: 0,
      };
      rows.set(key, row);
    }
    return row;
  };

  // The store is already deduplicated across overlapping datasets, so we can
  // sum every fixture for this competition + season directly.
  const chosen = store.matches.filter(
    (m) =>
      m.competition === competition &&
      m.season === season &&
      m.homeGoal != null &&
      m.awayGoal != null,
  );

  for (const m of chosen) {
    const home = ensure(m.homeKey, m.homeTeam);
    const away = ensure(m.awayKey, m.awayTeam);
    home.played++;
    away.played++;
    home.goalsFor += m.homeGoal!;
    home.goalsAgainst += m.awayGoal!;
    away.goalsFor += m.awayGoal!;
    away.goalsAgainst += m.homeGoal!;
    if (m.homeGoal! > m.awayGoal!) {
      home.wins++;
      home.points += 3;
      away.losses++;
    } else if (m.homeGoal! < m.awayGoal!) {
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

  const table = [...rows.values()];
  for (const row of table) row.goalDiff = row.goalsFor - row.goalsAgainst;
  // CBF tiebreaker order: points, then wins, then goal difference, then goals
  // scored, then name for stability.
  table.sort(
    (a, b) =>
      b.points - a.points ||
      b.wins - a.wins ||
      b.goalDiff - a.goalDiff ||
      b.goalsFor - a.goalsFor ||
      a.team.localeCompare(b.team),
  );
  return table;
}

export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
}

/** Search players by name/nationality/club/position with accent-insensitive matching. */
export function findPlayers(store: DataStore, filter: PlayerFilter): Player[] {
  const nameKey = filter.name ? normalizeText(filter.name) : null;
  const natKey = filter.nationality ? normalizeText(filter.nationality) : null;
  const clubKey = filter.club ? normalizeTeam(filter.club) : null;
  const posKey = filter.position ? normalizeText(filter.position) : null;

  const result = store.players.filter((p) => {
    if (nameKey && !normalizeText(p.name).includes(nameKey)) return false;
    if (natKey && normalizeText(p.nationality) !== natKey) return false;
    if (clubKey && !teamKeyMatches(p.clubKey, clubKey)) return false;
    if (posKey && normalizeText(p.position) !== posKey) return false;
    if (filter.minOverall != null && (p.overall ?? 0) < filter.minOverall) {
      return false;
    }
    return true;
  });

  result.sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
  return result;
}

export interface GoalsSummary {
  matches: number;
  matchesWithScore: number;
  totalGoals: number;
  goalsPerMatch: number;
  homeWins: number;
  awayWins: number;
  draws: number;
  homeWinRate: number;
}

/** Aggregate goals-per-match and home/away/draw rates over a filtered set. */
export function goalsSummary(store: DataStore, filter: MatchFilter = {}): GoalsSummary {
  const matches = findMatches(store, filter);
  let withScore = 0;
  let totalGoals = 0;
  let homeWins = 0;
  let awayWins = 0;
  let draws = 0;

  for (const m of matches) {
    if (m.homeGoal == null || m.awayGoal == null) continue;
    withScore++;
    totalGoals += m.homeGoal + m.awayGoal;
    if (m.homeGoal > m.awayGoal) homeWins++;
    else if (m.homeGoal < m.awayGoal) awayWins++;
    else draws++;
  }

  return {
    matches: matches.length,
    matchesWithScore: withScore,
    totalGoals,
    goalsPerMatch: withScore === 0 ? 0 : totalGoals / withScore,
    homeWins,
    awayWins,
    draws,
    homeWinRate: withScore === 0 ? 0 : homeWins / withScore,
  };
}

/** Matches sorted by goal margin (biggest wins first), score required. */
export function biggestWins(
  store: DataStore,
  filter: MatchFilter = {},
  limit = 10,
): Match[] {
  const scored = findMatches(store, filter).filter(
    (m) => m.homeGoal != null && m.awayGoal != null,
  );
  scored.sort((a, b) => {
    const ma = Math.abs(a.homeGoal! - a.awayGoal!);
    const mb = Math.abs(b.homeGoal! - b.awayGoal!);
    return mb - ma || b.homeGoal! + b.awayGoal! - (a.homeGoal! + a.awayGoal!);
  });
  return scored.slice(0, limit);
}
