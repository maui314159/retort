/**
 * brazilian-soccer-mcp — Query engine.
 *
 * Context: All non-IO soccer logic lives here. Each exported function takes
 * the loaded `Store` and a typed options object, and returns plain JSON values
 * that the MCP tools serialize. The engine never touches the filesystem or the
 * network; it is pure functions over the in-memory store, which makes the BDD
 * tests trivial to drive without any mocking.
 *
 * Name matching is done via `teamKey()` (case- and accent-folded) so a caller
 * asking for "Sao Paulo" finds matches stored as "São Paulo-SP".
 */

import type { Store } from "./loader.js";
import type {
  Match,
  Player,
  TeamRecord,
  HeadToHead,
  StandingsRow,
  BiggestWin,
  MatchOutcome,
} from "./types.js";
import { teamKey } from "./normalize.js";

/* ----------------------------------------------------------------------- */
/* Shared helpers                                                           */
/* ----------------------------------------------------------------------- */

function resolveTeamKey(store: Store, name: string): string | null {
  const k = teamKey(name);
  if (!k) return null;
  if (store.teamDisplay.has(k)) return k;
  // Fallback: substring match against known team keys.
  for (const known of store.teamDisplay.keys()) {
    if (known.includes(k) || k.includes(known)) return known;
  }
  return k;
}

function bestDisplayName(store: Store, key: string): string {
  return store.teamDisplay.get(key) ?? key;
}

function teamOutcomeFor(m: Match, teamKeyStr: string): MatchOutcome | null {
  if (m.homeGoals === null || m.awayGoals === null) return null;
  const isHome = m.homeTeamKey === teamKeyStr;
  const isAway = m.awayTeamKey === teamKeyStr;
  if (!isHome && !isAway) return null;
  const gf = isHome ? m.homeGoals : m.awayGoals;
  const ga = isHome ? m.awayGoals : m.homeGoals;
  if (gf > ga) return "win";
  if (gf < ga) return "loss";
  return "draw";
}

function dedupeMatches(matches: Match[]): Match[] {
  // The BR-Football dataset overlaps the Brasileirão/Cup files; dedupe on
  // (homeKey, awayKey, scores, season) to avoid double-counting in standings
  // and statistics. We deliberately do NOT use the date in the key because
  // the two sources disagree by ±1 day on ~20% of matches (timezone offset
  // between kick-off recording). Same teams + same score + same season is
  // virtually always the same match; the rare false-merge (two matches
  // between the same teams with the same score in one season) is far less
  // harmful than the pervasive double-counting the date-strict key produces.
  const seen = new Set<string>();
  const out: Match[] = [];
  for (const m of matches) {
    const key = [
      m.homeTeamKey,
      m.awayTeamKey,
      m.homeGoals ?? "",
      m.awayGoals ?? "",
      m.season ?? "",
    ].join("|");
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(m);
  }
  return out;
}

/* ----------------------------------------------------------------------- */
/* Match queries                                                            */
/* ----------------------------------------------------------------------- */

export interface MatchQueryOptions {
  team?: string;
  opponent?: string;
  competition?: string;
  season?: number;
  from?: string; // ISO date
  to?: string; // ISO date
  limit?: number;
}

export interface MatchSummary {
  id: string;
  date: string | null;
  homeTeam: string;
  awayTeam: string;
  homeGoals: number | null;
  awayGoals: number | null;
  competition: string;
  season: number | null;
  round: string | null;
  stage: string | null;
  venue: string | null;
}

export function matchSummary(m: Match): MatchSummary {
  return {
    id: m.id,
    date: m.date ? m.date.toISOString().slice(0, 10) : null,
    homeTeam: m.homeTeam,
    awayTeam: m.awayTeam,
    homeGoals: m.homeGoals,
    awayGoals: m.awayGoals,
    competition: m.competition,
    season: m.season,
    round: m.round,
    stage: m.stage,
    venue: m.venue,
  };
}

/** Find matches matching the given criteria. */
export function queryMatches(
  store: Store,
  opts: MatchQueryOptions,
): MatchSummary[] {
  let candidates: Match[] = [];

  const teamK = opts.team ? resolveTeamKey(store, opts.team) : undefined;
  const oppK = opts.opponent ? resolveTeamKey(store, opts.opponent) : undefined;

  if (teamK && oppK) {
    const set = store.matchesByPair.get(`${teamK}|${oppK}`);
    if (set) candidates = [...set].map((i) => store.matches[i]);
  } else if (teamK) {
    const set = store.matchesByTeam.get(teamK);
    if (set) candidates = [...set].map((i) => store.matches[i]);
  } else if (oppK) {
    const set = store.matchesByTeam.get(oppK);
    if (set) candidates = [...set].map((i) => store.matches[i]);
  } else {
    candidates = store.matches;
  }

  const fromMs = opts.from ? Date.parse(opts.from) : NaN;
  const toMs = opts.to ? Date.parse(opts.to) : NaN;

  let filtered = candidates.filter((m) => {
    if (opts.competition) {
      const want = opts.competition.toLowerCase();
      if (
        !m.competition.toLowerCase().includes(want) &&
        !m.tournamentRaw.toLowerCase().includes(want)
      ) {
        return false;
      }
    }
    if (opts.season !== undefined && m.season !== opts.season) return false;
    if (!isNaN(fromMs) && (m.date === null || m.date.getTime() < fromMs))
      return false;
    if (!isNaN(toMs) && (m.date === null || m.date.getTime() > toMs))
      return false;
    return true;
  });

  filtered = dedupeMatches(filtered);
  filtered.sort((a, b) => (b.date?.getTime() ?? 0) - (a.date?.getTime() ?? 0));
  const limit = opts.limit ?? 50;
  return filtered.slice(0, limit).map(matchSummary);
}
/** Last match between two teams (most recent by date). */
export function lastMatchBetween(
  store: Store,
  teamA: string,
  teamB: string,
): MatchSummary | null {
  const results = queryMatches(store, { team: teamA, opponent: teamB, limit: 1 });
  return results.length > 0 ? results[0] : null;
}

/* ----------------------------------------------------------------------- */
/* Team queries                                                            */
/* ----------------------------------------------------------------------- */

export interface TeamStatsOptions {
  season?: number;
  competition?: string;
  /** "home", "away", or "all" (default). */
  venue?: "home" | "away" | "all";
}

/** Calculate the record for a team over a (filtered) match set. */
export function teamRecord(
  store: Store,
  team: string,
  opts: TeamStatsOptions = {},
): TeamRecord {
  const k = resolveTeamKey(store, team);
  if (!k) {
    return emptyRecord(team);
  }
  const display = bestDisplayName(store, k);
  const set = store.matchesByTeam.get(k);
  if (!set) return emptyRecord(display);

  const rows = dedupeMatches([...set].map((i) => store.matches[i]));

  let matches = 0,
    wins = 0,
    draws = 0,
    losses = 0,
    gf = 0,
    ga = 0;
  for (const m of rows) {
    if (opts.season !== undefined && m.season !== opts.season) continue;
    if (opts.competition) {
      const want = opts.competition.toLowerCase();
      if (
        !m.competition.toLowerCase().includes(want) &&
        !m.tournamentRaw.toLowerCase().includes(want)
      )
        continue;
    }
    const isHome = m.homeTeamKey === k;
    const isAway = m.awayTeamKey === k;
    if (!isHome && !isAway) continue;
    if (opts.venue === "home" && !isHome) continue;
    if (opts.venue === "away" && !isAway) continue;
    if (m.homeGoals === null || m.awayGoals === null) continue;
    matches++;
    const outcome = teamOutcomeFor(m, k);
    if (outcome === "win") wins++;
    else if (outcome === "draw") draws++;
    else if (outcome === "loss") losses++;
    gf += isHome ? m.homeGoals : m.awayGoals;
    ga += isHome ? m.awayGoals : m.homeGoals;
  }
  const points = wins * 3 + draws;
  return {
    team: display,
    matches,
    wins,
    draws,
    losses,
    goalsFor: gf,
    goalsAgainst: ga,
    goalDifference: gf - ga,
    points,
    winRate: matches > 0 ? +(wins / matches * 100).toFixed(1) : 0,
  };
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
    goalDifference: 0,
    points: 0,
    winRate: 0,
  };
}

/* ----------------------------------------------------------------------- */
/* Head-to-head                                                            */
/* ----------------------------------------------------------------------- */

export function headToHead(
  store: Store,
  teamA: string,
  teamB: string,
): HeadToHead {
  const ka = resolveTeamKey(store, teamA);
  const kb = resolveTeamKey(store, teamB);
  const aDisplay = ka ? bestDisplayName(store, ka) : teamA;
  const bDisplay = kb ? bestDisplayName(store, kb) : teamB;
  const base: HeadToHead = {
    teamA: aDisplay,
    teamB: bDisplay,
    matches: 0,
    teamAWins: 0,
    teamBWins: 0,
    draws: 0,
    teamAGoals: 0,
    teamBGoals: 0,
  };
  if (!ka || !kb) return base;
  const set = store.matchesByPair.get(`${ka}|${kb}`);
  if (!set) return base;
  const rows = dedupeMatches([...set].map((i) => store.matches[i]));
  for (const m of rows) {
    if (m.homeGoals === null || m.awayGoals === null) continue;
    base.matches++;
    const aIsHome = m.homeTeamKey === ka;
    const aGoals = aIsHome ? m.homeGoals : m.awayGoals;
    const bGoals = aIsHome ? m.awayGoals : m.homeGoals;
    base.teamAGoals += aGoals;
    base.teamBGoals += bGoals;
    if (aGoals > bGoals) base.teamAWins++;
    else if (aGoals < bGoals) base.teamBWins++;
    else base.draws++;
  }
  return base;
}

/* ----------------------------------------------------------------------- */
/* Competition / standings                                                 */
/* ----------------------------------------------------------------------- */

export interface StandingsOptions {
  competition?: string;
  season: number;
  /** Limit to the top N; default all. */
  top?: number;
}

/** Calculate standings for a competition+season from match results. */
export function standings(
  store: Store,
  opts: StandingsOptions,
): StandingsRow[] {
  const competition = opts.competition ?? "Brasileirão Serie A";
  const want = competition.toLowerCase();
  const rows = store.matches.filter(
    (m) =>
      m.season === opts.season &&
      (m.competition.toLowerCase().includes(want) ||
        m.tournamentRaw.toLowerCase().includes(want)),
  );
  const deduped = dedupeMatches(rows);
  const rec = new Map<string, TeamRecord>();
  const keyOf = (m: Match, home: boolean) =>
    home ? m.homeTeamKey : m.awayTeamKey;

  for (const m of deduped) {
    if (m.homeGoals === null || m.awayGoals === null) continue;
    for (const home of [true, false]) {
      const k = keyOf(m, home);
      if (!k) continue;
      let r = rec.get(k);
      if (!r) {
        r = emptyRecord(bestDisplayName(store, k));
        rec.set(k, r);
      }
      r.matches++;
      const gf = home ? m.homeGoals : m.awayGoals;
      const ga = home ? m.awayGoals : m.homeGoals;
      r.goalsFor += gf;
      r.goalsAgainst += ga;
      if (gf > ga) r.wins++;
      else if (gf < ga) r.losses++;
      else r.draws++;
    }
  }
  for (const r of rec.values()) {
    r.points = r.wins * 3 + r.draws;
    r.goalDifference = r.goalsFor - r.goalsAgainst;
    r.winRate = r.matches > 0 ? +(r.wins / r.matches * 100).toFixed(1) : 0;
  }
  const sorted = [...rec.values()].sort(
    (a, b) =>
      b.points - a.points ||
      b.wins - a.wins ||
      b.goalDifference - a.goalDifference ||
      b.goalsFor - a.goalsFor ||
      a.team.localeCompare(b.team),
  );
  const out: StandingsRow[] = sorted.map((r, i) => ({
    position: i + 1,
    team: r.team,
    played: r.matches,
    wins: r.wins,
    draws: r.draws,
    losses: r.losses,
    goalsFor: r.goalsFor,
    goalsAgainst: r.goalsAgainst,
    goalDifference: r.goalDifference,
    points: r.points,
    isChampion: false,
  }));
  if (out.length > 0) out[0].isChampion = true;
  return opts.top ? out.slice(0, opts.top) : out;
}

/** Return the champion (top of standings) for a competition+season. */
export function champion(
  store: Store,
  opts: StandingsOptions,
): StandingsRow | null {
  const table = standings(store, opts);
  return table.length > 0 ? table[0] : null;
}

/** Teams in the bottom N positions of a competition+season (relegation). */
export function relegated(
  store: Store,
  opts: StandingsOptions & { count?: number },
): StandingsRow[] {
  const table = standings(store, opts);
  const count = opts.count ?? 4;
  return table.slice(-count).reverse();
}

/* ----------------------------------------------------------------------- */
/* Player queries                                                          */
/* ----------------------------------------------------------------------- */

export interface PlayerQueryOptions {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  limit?: number;
  sort?: "overall" | "potential" | "name";
}

export function queryPlayers(
  store: Store,
  opts: PlayerQueryOptions = {},
): Player[] {
  let indices: Iterable<number>;
  if (opts.club) {
    const k = teamKey(opts.club);
    const set = store.playersByClubKey.get(k);
    indices = set ?? [];
  } else if (opts.nationality) {
    const want = opts.nationality.toLowerCase();
    const set = store.playersByNationality.get(
      [...store.playersByNationality.keys()].find(
        (n) => n.toLowerCase() === want,
      ) ?? "",
    );
    indices = set ?? [];
  } else {
    indices = store.players.map((_, i) => i);
  }

  let out: Player[] = [];
  for (const i of indices) {
    const p = store.players[i];
    if (!p) continue;
    if (opts.name) {
      if (!p.name.toLowerCase().includes(opts.name.toLowerCase())) continue;
    }
    if (opts.nationality) {
      if (p.nationality.toLowerCase() !== opts.nationality.toLowerCase())
        continue;
    }
    if (opts.position) {
      if (p.position.toLowerCase() !== opts.position.toLowerCase()) continue;
    }
    if (opts.minOverall !== undefined) {
      if (p.overall === null || p.overall < opts.minOverall) continue;
    }
    out.push(p);
  }

  const sort = opts.sort ?? "overall";
  out.sort((a, b) => {
    if (sort === "name") return a.name.localeCompare(b.name);
    const av = a[sort === "potential" ? "potential" : "overall"] ?? 0;
    const bv = b[sort === "potential" ? "potential" : "overall"] ?? 0;
    return bv - av || a.name.localeCompare(b.name);
  });
  const limit = opts.limit ?? 20;
  return out.slice(0, limit);
}

/** Top-rated players at a club. */
export function topPlayersAtClub(
  store: Store,
  club: string,
  limit = 10,
): Player[] {
  return queryPlayers(store, { club, sort: "overall", limit });
}

/** Count of Brazilian players per Brazilian club, with average rating. */
export interface BrazilianClubsSummary {
  club: string;
  count: number;
  avgRating: number;
}

export function brazilianPlayersByClub(
  store: Store,
  limit = 20,
): BrazilianClubsSummary[] {
  const clubs = new Map<string, { count: number; sum: number }>();
  for (const p of store.players) {
    if (p.nationality.toLowerCase() !== "brazil") continue;
    if (!p.club) continue;
    const c = clubs.get(p.club) ?? { count: 0, sum: 0 };
    c.count++;
    c.sum += p.overall ?? 0;
    clubs.set(p.club, c);
  }
  return [...clubs.entries()]
    .map(([club, c]) => ({
      club,
      count: c.count,
      avgRating: +(c.sum / c.count).toFixed(1),
    }))
    .sort((a, b) => b.count - a.count || b.avgRating - a.avgRating)
    .slice(0, limit);
}

/* ----------------------------------------------------------------------- */
/* Statistics                                                              */
/* ----------------------------------------------------------------------- */

export interface GoalsAverage {
  matches: number;
  totalGoals: number;
  averagePerMatch: number;
  homeWinRate: number;
  awayWinRate: number;
  drawRate: number;
}

/** Goals-per-match and result-rate statistics for a competition (or all). */
export function goalsAverage(
  store: Store,
  opts: { competition?: string; season?: number } = {},
): GoalsAverage {
  let rows = store.matches;
  if (opts.competition) {
    const want = opts.competition.toLowerCase();
    rows = rows.filter(
      (m) =>
        m.competition.toLowerCase().includes(want) ||
        m.tournamentRaw.toLowerCase().includes(want),
    );
  }
  if (opts.season !== undefined) rows = rows.filter((m) => m.season === opts.season);
  rows = dedupeMatches(rows);
  let matches = 0,
    total = 0,
    homeWins = 0,
    awayWins = 0,
    draws = 0;
  for (const m of rows) {
    if (m.homeGoals === null || m.awayGoals === null) continue;
    matches++;
    total += m.homeGoals + m.awayGoals;
    if (m.homeGoals > m.awayGoals) homeWins++;
    else if (m.awayGoals > m.homeGoals) awayWins++;
    else draws++;
  }
  return {
    matches,
    totalGoals: total,
    averagePerMatch: matches > 0 ? +(total / matches).toFixed(2) : 0,
    homeWinRate: matches > 0 ? +(homeWins / matches * 100).toFixed(1) : 0,
    awayWinRate: matches > 0 ? +(awayWins / matches * 100).toFixed(1) : 0,
    drawRate: matches > 0 ? +(draws / matches * 100).toFixed(1) : 0,
  };
}

/** Biggest victory margins in the dataset. */
export function biggestWins(
  store: Store,
  opts: { competition?: string; limit?: number } = {},
): BiggestWin[] {
  let rows = store.matches;
  if (opts.competition) {
    const want = opts.competition.toLowerCase();
    rows = rows.filter(
      (m) =>
        m.competition.toLowerCase().includes(want) ||
        m.tournamentRaw.toLowerCase().includes(want),
    );
  }
  rows = dedupeMatches(rows);
  const wins: BiggestWin[] = [];
  for (const m of rows) {
    if (m.homeGoals === null || m.awayGoals === null) continue;
    if (m.homeGoals > m.awayGoals) {
      wins.push({
        date: m.date ? m.date.toISOString().slice(0, 10) : "unknown",
        competition: m.competition,
        season: m.season,
        winner: m.homeTeam,
        loser: m.awayTeam,
        winnerGoals: m.homeGoals,
        loserGoals: m.awayGoals,
        margin: m.homeGoals - m.awayGoals,
      });
    } else if (m.awayGoals > m.homeGoals) {
      wins.push({
        date: m.date ? m.date.toISOString().slice(0, 10) : "unknown",
        competition: m.competition,
        season: m.season,
        winner: m.awayTeam,
        loser: m.homeTeam,
        winnerGoals: m.awayGoals,
        loserGoals: m.homeGoals,
        margin: m.awayGoals - m.homeGoals,
      });
    }
  }
  wins.sort((a, b) => b.margin - a.margin || b.winnerGoals - a.winnerGoals);
  return wins.slice(0, opts.limit ?? 10);
}

/** Best away record across all teams for a competition+season. */
export function bestAwayRecord(
  store: Store,
  opts: { competition?: string; season?: number; limit?: number } = {},
): TeamRecord[] {
  const competition = opts.competition ?? "Brasileirão Serie A";
  const want = competition.toLowerCase();
  const teams = new Set<string>();
  for (const m of store.matches) {
    if (opts.season !== undefined && m.season !== opts.season) continue;
    if (
      !m.competition.toLowerCase().includes(want) &&
      !m.tournamentRaw.toLowerCase().includes(want)
    )
      continue;
    teams.add(m.awayTeamKey);
  }
  const records = [...teams]
    .map((k) =>
      teamRecord(store, bestDisplayName(store, k), {
        competition,
        season: opts.season,
        venue: "away",
      }),
    )
    .filter((r) => r.matches > 0)
    .sort(
      (a, b) =>
        b.points - a.points ||
        b.winRate - a.winRate ||
        b.goalDifference - a.goalDifference,
    );
  return records.slice(0, opts.limit ?? 5);
}

/* ----------------------------------------------------------------------- */
/* Roster of all known teams (for prompts/validation)                     */
/* ----------------------------------------------------------------------- */

/** Return all known team display names (deduplicated, sorted). */
export function allTeams(store: Store): string[] {
  return [...new Set(store.teamDisplay.values())].sort((a, b) =>
    a.localeCompare(b),
  );
}

/** Return all competitions present in the data. */
export function allCompetitions(store: Store): string[] {
  return [...store.matchesByCompetition.keys()].sort();
}

/** Return all seasons present for a competition. */
export function seasonsFor(store: Store, competition?: string): number[] {
  const want = competition?.toLowerCase();
  const set = new Set<number>();
  for (const m of store.matches) {
    if (m.season === null) continue;
    if (want) {
      if (
        !m.competition.toLowerCase().includes(want) &&
        !m.tournamentRaw.toLowerCase().includes(want)
      )
        continue;
    }
    set.add(m.season);
  }
  return [...set].sort((a, b) => a - b);
}
