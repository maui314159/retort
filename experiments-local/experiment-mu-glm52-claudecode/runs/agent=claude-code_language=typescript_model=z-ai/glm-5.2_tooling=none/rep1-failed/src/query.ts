/**
 * Brazilian Soccer MCP Server — query engine
 * ===========================================
 * Context block:
 *   The pure query layer that backs every MCP tool. It consumes the normalized
 *   `MatchRecord[]`/`PlayerRecord[]` produced by `src/loader.ts` and exposes
 *   operations for the five capability categories in the spec:
 *
 *     1. Match queries      — searchMatches, headToHead
 *     2. Team queries       — teamStatistics, teamVenues
 *     3. Player queries     — searchPlayers, topPlayers
 *     4. Competition queries — standings, competitionSummary
 *     5. Statistical analysis — averageGoals, biggestWins, homeAwaySplit
 *
 *   Every function is deterministic and framework-agnostic so the BDD tests in
 *   `tests/bdd.test.ts` can call them directly without going through stdio.
 */

import {
  COMPETITIONS,
  competitionMatches,
  parseTeamRef,
  teamMatches,
  tokenize,
} from './normalize.js';
import type {
  MatchRecord,
  PlayerRecord,
  TeamRef,
  TeamTally,
} from './types.js';

/**
 * Return a non-overlapping subset of matches by picking one canonical source
 * per (competition, season). The five match datasets overlap heavily:
 *   - Brasileirao_Matches (2012-2022) ∩ novo_campeonato_brasileiro (2003-2019)
 *   - BR-Football "Serie A" (2014-2023) ∩ Brasileirao_Matches (2012-2022)
 *   - BR-Football "Copa do Brasil" (2014-2023) ∩ Brazilian_Cup_Matches (2012-2021)
 *
 * Selection rule (one source per season, no double counting):
 *   Brasileirão:  2003-2011 → historical; 2012-2022 → Brasileirao_Matches;
 *                 2023+ → BR-Football Serie A.
 *   Copa do Brasil: 2012-2021 → Brazilian_Cup_Matches; 2022-2023 → BR-Football.
 *   Libertadores / Série B / Série C: single source, kept as-is.
 * When a record has no season (Libertadores "NA"), the source-default rule keeps
 * the dedicated file.
 */
export function canonicalMatches(matches: MatchRecord[]): MatchRecord[] {
  return matches.filter((m) => {
    if (m.competition === COMPETITIONS.BRASILEIRAO) {
      const s = m.season;
      if (m.source === 'novo_campeonato_brasileiro') return s !== null && s < 2012;
      if (m.source === 'Brasileirao_Matches') return true;
      if (m.source === 'BR-Football-Dataset') return s !== null && s > 2022;
      return false;
    }
    if (m.competition === COMPETITIONS.COPA_DO_BRASIL) {
      const s = m.season;
      if (m.source === 'Brazilian_Cup_Matches') return true;
      if (m.source === 'BR-Football-Dataset') return s !== null && s > 2021;
      return false;
    }
    // Libertadores, Série B, Série C: no source overlap.
    return true;
  });
}

/** Optional filters for `searchMatches`. */
export interface MatchFilter {
  team?: string;
  opponent?: string;
  competition?: string;
  season?: number;
  /** ISO date YYYY-MM-DD lower bound (inclusive). */
  fromDate?: string;
  /** ISO date YYYY-MM-DD upper bound (inclusive). */
  toDate?: string;
  limit?: number;
}

/** Determine whether a match involves a team ref (home or away). */
function matchTeamIn(m: MatchRecord, ref: TeamRef): boolean {
  return teamMatches(m.homeKey, m.homeState, ref) || teamMatches(m.awayKey, m.awayState, ref);
}

/** Determine whether the match's opponent (the side not equal to `team`) is `opp`. */
function opponentIs(m: MatchRecord, team: TeamRef, opp: TeamRef): boolean {
  const homeIsTeam = teamMatches(m.homeKey, m.homeState, team);
  const awayIsTeam = teamMatches(m.awayKey, m.awayState, team);
  if (homeIsTeam && !awayIsTeam) return teamMatches(m.awayKey, m.awayState, opp);
  if (awayIsTeam && !homeIsTeam) return teamMatches(m.homeKey, m.homeState, opp);
  return false;
}

/** Search matches by the criteria in `filter`. */
export function searchMatches(matches: MatchRecord[], filter: MatchFilter): MatchRecord[] {
  const teamRef = filter.team ? parseTeamRef(filter.team) : null;
  const oppRef = filter.opponent ? parseTeamRef(filter.opponent) : null;
  const fromMs = filter.fromDate ? Date.parse(filter.fromDate) : NaN;
  const toMs = filter.toDate ? Date.parse(filter.toDate) : NaN;

  let out = matches.filter((m) => {
    if (teamRef && !matchTeamIn(m, teamRef)) return false;
    if (teamRef && oppRef && !opponentIs(m, teamRef, oppRef)) return false;
    if (filter.competition && !competitionMatches(m.competition, filter.competition)) return false;
    if (filter.season !== undefined && m.season !== filter.season) return false;
    if (m.date) {
      if (!Number.isNaN(fromMs) && m.date.getTime() < fromMs) return false;
      if (!Number.isNaN(toMs) && m.date.getTime() > toMs + 86_400_000) return false;
    } else if (filter.fromDate || filter.toDate) {
      return false;
    }
    return true;
  });

  // Most recent first.
  out = out.sort((a, b) => {
    const at = a.date?.getTime() ?? 0;
    const bt = b.date?.getTime() ?? 0;
    return bt - at;
  });

  if (filter.limit && filter.limit > 0) out = out.slice(0, filter.limit);
  return out;
}

/** Head-to-head tally between two teams across all datasets. */
export function headToHead(matches: MatchRecord[], teamA: string, teamB: string): {
  a: TeamRef;
  b: TeamRef;
  aWins: number;
  bWins: number;
  draws: number;
  matches: MatchRecord[];
} {
  const a = parseTeamRef(teamA);
  const b = parseTeamRef(teamB);
  const found = matches.filter(
    (m) => opponentIs(m, a, b) || opponentIs(m, b, a) ||
      (matchTeamIn(m, a) && matchTeamIn(m, b)),
  );
  let aWins = 0;
  let bWins = 0;
  let draws = 0;
  for (const m of found) {
    if (m.homeGoal === null || m.awayGoal === null) continue;
    const homeIsA = teamMatches(m.homeKey, m.homeState, a);
    const awayIsA = teamMatches(m.awayKey, m.awayState, a);
    const aGoals = homeIsA ? m.homeGoal : awayIsA ? m.awayGoal : null;
    const bGoals = homeIsA ? m.awayGoal : awayIsA ? m.homeGoal : null;
    if (aGoals === null || bGoals === null) continue;
    if (aGoals > bGoals) aWins++;
    else if (bGoals > aGoals) bWins++;
    else draws++;
  }
  found.sort((x, y) => (y.date?.getTime() ?? 0) - (x.date?.getTime() ?? 0));
  return { a, b, aWins, bWins, draws, matches: found };
}

/** Compute a tally for one team over a filtered match set. */
function tallyTeam(matches: MatchRecord[], ref: TeamRef): TeamTally {
  const t: TeamTally = {
    team: ref.raw,
    teamKey: ref.nameKey,
    played: 0,
    wins: 0,
    draws: 0,
    losses: 0,
    goalsFor: 0,
    goalsAgainst: 0,
    points: 0,
  };
  for (const m of matches) {
    const home = teamMatches(m.homeKey, m.homeState, ref);
    const away = teamMatches(m.awayKey, m.awayState, ref);
    if (!home && !away) continue;
    if (m.homeGoal === null || m.awayGoal === null) continue;
    const gf = home ? m.homeGoal : m.awayGoal;
    const ga = home ? m.awayGoal : m.homeGoal;
    t.played++;
    t.goalsFor += gf;
    t.goalsAgainst += ga;
    if (gf > ga) {
      t.wins++;
      t.points += 3;
    } else if (gf === ga) {
      t.draws++;
      t.points += 1;
    } else {
      t.losses++;
    }
  }
  return t;
}

export interface TeamStatsOptions {
  team: string;
  season?: number;
  competition?: string;
  venue?: 'home' | 'away' | 'all';
}

/** Compute win/draw/loss and goal tallies for a team. */
export function teamStatistics(matches: MatchRecord[], opts: TeamStatsOptions): TeamTally {
  const ref = parseTeamRef(opts.team);
  let subset = matches.filter((m) => matchTeamIn(m, ref));
  if (opts.season !== undefined) subset = subset.filter((m) => m.season === opts.season);
  if (opts.competition) subset = subset.filter((m) => competitionMatches(m.competition, opts.competition));
  if (opts.venue === 'home') {
    subset = subset.filter((m) => teamMatches(m.homeKey, m.homeState, ref));
  } else if (opts.venue === 'away') {
    subset = subset.filter((m) => teamMatches(m.awayKey, m.awayState, ref));
  }
  return tallyTeam(subset, ref);
}

/** Average goals per match, optionally filtered by competition/season. */
export function averageGoals(
  matches: MatchRecord[],
  opts: { competition?: string; season?: number },
): { matches: number; totalGoals: number; avgPerMatch: number; homeWinRate: number } {
  let subset = matches.filter((m) => m.homeGoal !== null && m.awayGoal !== null);
  if (opts.competition) subset = subset.filter((m) => competitionMatches(m.competition, opts.competition));
  if (opts.season !== undefined) subset = subset.filter((m) => m.season === opts.season);
  if (subset.length === 0) {
    return { matches: 0, totalGoals: 0, avgPerMatch: 0, homeWinRate: 0 };
  }
  const totalGoals = subset.reduce((s, m) => s + (m.homeGoal ?? 0) + (m.awayGoal ?? 0), 0);
  const homeWins = subset.filter((m) => (m.homeGoal ?? 0) > (m.awayGoal ?? 0)).length;
  return {
    matches: subset.length,
    totalGoals,
    avgPerMatch: Number((totalGoals / subset.length).toFixed(2)),
    homeWinRate: Number(((homeWins / subset.length) * 100).toFixed(1)),
  };
}

/** Biggest victories ranked by goal difference. */
export function biggestWins(
  matches: MatchRecord[],
  opts: { competition?: string; season?: number; limit?: number },
): MatchRecord[] {
  let subset = matches.filter((m) => m.homeGoal !== null && m.awayGoal !== null);
  if (opts.competition) subset = subset.filter((m) => competitionMatches(m.competition, opts.competition));
  if (opts.season !== undefined) subset = subset.filter((m) => m.season === opts.season);
  const sorted = subset.sort((a, b) => {
    const da = Math.abs((a.homeGoal ?? 0) - (a.awayGoal ?? 0));
    const db = Math.abs((b.homeGoal ?? 0) - (b.awayGoal ?? 0));
    return db - da;
  });
  return sorted.slice(0, Math.max(1, opts.limit ?? 10));
}

/** Standings for a competition + season, computed from match results (3-1-0). */
export function standings(
  matches: MatchRecord[],
  opts: { competition: string; season: number; limit?: number },
): TeamTally[] {
  const comp = opts.competition;
  const season = opts.season;
  const subset = matches.filter(
    (m) => m.season === season && competitionMatches(m.competition, comp),
  );
  // Collect every team that played.
  const refMap = new Map<string, TeamRef>();
  for (const m of subset) {
    for (const [name, key, state] of [
      [m.home, m.homeKey, m.homeState],
      [m.away, m.awayKey, m.awayState],
    ] as const) {
      if (key && !refMap.has(key)) {
        refMap.set(key, { nameKey: key, state: state, raw: name });
      }
    }
  }
  const tallies: TeamTally[] = [];
  for (const ref of refMap.values()) {
    const t = tallyTeam(subset, ref);
    if (t.played > 0) tallies.push(t);
  }
  tallies.sort((a, b) =>
    b.points - a.points ||
    (b.goalsFor - b.goalsAgainst) - (a.goalsFor - a.goalsAgainst) ||
    b.goalsFor - a.goalsFor ||
    a.teamKey.localeCompare(b.teamKey),
  );
  return tallies.slice(0, Math.max(1, opts.limit ?? 100));
}

/** Per-competition summary: available seasons + match counts. */
export function competitionSummary(matches: MatchRecord[]): {
  competition: string;
  seasons: { season: number | string; matches: number }[];
  totalMatches: number;
}[] {
  const map = new Map<string, Map<string, number>>();
  for (const m of matches) {
    if (!map.has(m.competition)) map.set(m.competition, new Map());
    const seasonKey = String(m.season ?? 'unknown');
    map.get(m.competition)!.set(seasonKey, (map.get(m.competition)!.get(seasonKey) ?? 0) + 1);
  }
  const out: ReturnType<typeof competitionSummary> = [];
  for (const [competition, seasons] of map) {
    const seasonList = [...seasons.entries()]
      .map(([season, matches]) => ({ season, matches }))
      .sort((a, b) => String(a.season).localeCompare(String(b.season)));
    out.push({
      competition,
      seasons: seasonList,
      totalMatches: seasonList.reduce((s, x) => s + x.matches, 0),
    });
  }
  out.sort((a, b) => a.competition.localeCompare(b.competition));
  return out;
}

export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  limit?: number;
}

/** Search FIFA players by name/nationality/club/position/rating. */
export function searchPlayers(players: PlayerRecord[], filter: PlayerFilter): PlayerRecord[] {
  const nameKey = filter.name ? tokenize(filter.name) : '';
  const natKey = filter.nationality ? tokenize(filter.nationality) : '';
  const clubKey = filter.club ? tokenize(filter.club) : '';
  const posKey = filter.position ? tokenize(filter.position) : '';
  let out = players.filter((p) => {
    if (nameKey) {
      const pk = tokenize(p.name);
      if (!pk.includes(nameKey) && !nameKey.includes(pk)) return false;
    }
    if (natKey) {
      const nk = tokenize(p.nationality);
      if (!nk.includes(natKey) && !natKey.includes(nk)) return false;
    }
    if (clubKey) {
      const ck = tokenize(p.club);
      if (!ck.includes(clubKey) && !clubKey.includes(ck)) return false;
    }
    if (posKey) {
      const pp = tokenize(p.position);
      if (pp !== posKey && !pp.includes(posKey) && !posKey.includes(pp)) return false;
    }
    if (filter.minOverall !== undefined && (p.overall ?? 0) < filter.minOverall) return false;
    return true;
  });
  if (filter.minOverall !== undefined) {
    out = out.sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
  }
  if (filter.limit && filter.limit > 0) out = out.slice(0, filter.limit);
  return out;
}

/** Top-N players by overall rating, with optional filters. */
export function topPlayers(
  players: PlayerRecord[],
  opts: { nationality?: string; club?: string; position?: string; limit?: number },
): PlayerRecord[] {
  return searchPlayers(players, {
    nationality: opts.nationality,
    club: opts.club,
    position: opts.position,
    limit: opts.limit ?? 10,
  }).filter((p) => p.overall !== null)
    .sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
}

/** Home vs away performance split for a competition/season. */
export function homeAwaySplit(
  matches: MatchRecord[],
  opts: { competition?: string; season?: number },
): { homeWins: number; awayWins: number; draws: number; total: number } {
  let subset = matches.filter((m) => m.homeGoal !== null && m.awayGoal !== null);
  if (opts.competition) subset = subset.filter((m) => competitionMatches(m.competition, opts.competition));
  if (opts.season !== undefined) subset = subset.filter((m) => m.season === opts.season);
  let homeWins = 0;
  let awayWins = 0;
  let draws = 0;
  for (const m of subset) {
    if ((m.homeGoal ?? 0) > (m.awayGoal ?? 0)) homeWins++;
    else if ((m.awayGoal ?? 0) > (m.homeGoal ?? 0)) awayWins++;
    else draws++;
  }
  return { homeWins, awayWins, draws, total: subset.length };
}

/** Convenience: resolve all distinct teams whose name matches a query. */
export function resolveTeams(matches: MatchRecord[], query: string): { display: string; key: string; state?: string }[] {
  const ref = parseTeamRef(query);
  const seen = new Map<string, { display: string; key: string; state?: string }>();
  for (const m of matches) {
    for (const [disp, key, state] of [
      [m.home, m.homeKey, m.homeState],
      [m.away, m.awayKey, m.awayState],
    ] as const) {
      if (key && teamMatches(key, state, ref)) {
        if (!seen.has(key + '|' + (state ?? ''))) {
          seen.set(key + '|' + (state ?? ''), { display: disp, key, state });
        }
      }
    }
  }
  return [...seen.values()];
}

export { COMPETITIONS };
