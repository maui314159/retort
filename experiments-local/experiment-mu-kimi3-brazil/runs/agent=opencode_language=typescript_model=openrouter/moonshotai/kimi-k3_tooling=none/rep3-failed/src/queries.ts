/**
 * Query engine over the in-memory DatasetStore.
 * All functions are pure and operate on the deduped match view.
 */
import {
  Competition,
  DatasetStore,
  HeadToHead,
  Match,
  Player,
  StandingRow,
  TeamIdentity,
  TeamRecord,
} from './types.js';
import { normalizeCompetition, parseTeamName, simplify, teamKey } from './normalize.js';

// ---------------------------------------------------------------------------
// Team resolution
// ---------------------------------------------------------------------------

export interface TeamResolution {
  team?: TeamIdentity;
  /** Other identities that also matched (ambiguous base names). */
  alternatives: TeamIdentity[];
  /** All candidates considered, ranked. */
  candidates: TeamIdentity[];
}

/**
 * Resolve a free-text team query to a canonical identity.
 * Handles accents, case, state suffixes and full legal names. When several
 * identities share a base name (e.g. "Botafogo" RJ/PB/SP), the one with the
 * most matches wins and the rest are returned as alternatives.
 */
export function resolveTeam(store: DatasetStore, query: string): TeamResolution {
  const { base, state } = parseTeamName(query);
  const teams = [...store.teams.values()];

  const exact = store.teams.get(teamKey(base, state));
  if (exact) return { team: exact, alternatives: [], candidates: [exact] };

  let candidates = teams.filter(
    (t) => t.base === base && (!state || t.state === state),
  );

  if (candidates.length === 0 && !state) {
    // Fallback: substring match on the base name.
    candidates = teams.filter(
      (t) => t.base.includes(base) || base.includes(t.base),
    );
  }
  if (candidates.length === 0 && state) {
    candidates = teams.filter((t) => t.base === base);
  }

  candidates = candidates.sort((a, b) => b.matchCount - a.matchCount);
  const [team, ...alternatives] = candidates;
  return { team, alternatives, candidates };
}

/** List every identity whose base name matches the query. */
export function findTeams(store: DatasetStore, query: string): TeamIdentity[] {
  const { base } = parseTeamName(query);
  return [...store.teams.values()]
    .filter((t) => t.base === base || t.base.includes(base) || base.includes(t.base))
    .sort((a, b) => b.matchCount - a.matchCount);
}

// ---------------------------------------------------------------------------
// Match search
// ---------------------------------------------------------------------------

export interface MatchFilter {
  team?: TeamIdentity;
  opponent?: TeamIdentity;
  competition?: string;
  season?: number;
  dateFrom?: string;
  dateTo?: string;
  playedOnly?: boolean;
}

export function searchMatches(store: DatasetStore, filter: MatchFilter): Match[] {
  return store.dedupedMatches.filter((m) => {
    if (filter.playedOnly !== false && !m.played) return false;
    if (filter.competition && m.competition !== filter.competition) return false;
    if (filter.season !== undefined && m.season !== filter.season) return false;
    if (filter.dateFrom && (!m.date || m.date < filter.dateFrom)) return false;
    if (filter.dateTo && (!m.date || m.date > filter.dateTo)) return false;
    if (filter.team && filter.opponent) {
      const a = filter.team.key;
      const b = filter.opponent.key;
      const pair = [m.homeTeam.key, m.awayTeam.key];
      if (!(pair.includes(a) && pair.includes(b))) return false;
    } else if (filter.team) {
      const k = filter.team.key;
      if (m.homeTeam.key !== k && m.awayTeam.key !== k) return false;
    }
    return true;
  });
}

/** Newest-first ordering with undated matches last. */
export function byDateDesc(a: Match, b: Match): number {
  if (a.date && b.date) return a.date > b.date ? -1 : a.date < b.date ? 1 : 0;
  return a.date ? -1 : 1;
}

// ---------------------------------------------------------------------------
// Head to head
// ---------------------------------------------------------------------------

export function headToHead(
  store: DatasetStore,
  teamA: TeamIdentity,
  teamB: TeamIdentity,
  filter: { competition?: string; season?: number } = {},
): HeadToHead {
  const matches = searchMatches(store, {
    team: teamA,
    opponent: teamB,
    competition: filter.competition,
    season: filter.season,
  }).sort(byDateDesc);

  let winsA = 0;
  let winsB = 0;
  let draws = 0;
  let goalsA = 0;
  let goalsB = 0;
  for (const m of matches) {
    const aIsHome = m.homeTeam.key === teamA.key;
    const gf = aIsHome ? m.homeGoals! : m.awayGoals!;
    const ga = aIsHome ? m.awayGoals! : m.homeGoals!;
    goalsA += gf;
    goalsB += ga;
    if (gf > ga) winsA++;
    else if (gf < ga) winsB++;
    else draws++;
  }
  return { teamA, teamB, matches, winsA, winsB, draws, goalsA, goalsB };
}

// ---------------------------------------------------------------------------
// Team statistics
// ---------------------------------------------------------------------------

export interface TeamStatsFilter {
  season?: number;
  competition?: string;
  venue?: 'home' | 'away' | 'all';
}

export function teamStats(
  store: DatasetStore,
  team: TeamIdentity,
  filter: TeamStatsFilter = {},
): { record: TeamRecord; home: TeamRecord; away: TeamRecord; matches: Match[] } {
  const venue = filter.venue ?? 'all';
  const matches = searchMatches(store, {
    team,
    season: filter.season,
    competition: filter.competition,
  }).filter((m) => {
    if (venue === 'home') return m.homeTeam.key === team.key;
    if (venue === 'away') return m.awayTeam.key === team.key;
    return true;
  });

  const blank = (): TeamRecord => ({
    matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0,
  });
  const record = blank();
  const home = blank();
  const away = blank();

  for (const m of matches) {
    const isHome = m.homeTeam.key === team.key;
    const gf = isHome ? m.homeGoals! : m.awayGoals!;
    const ga = isHome ? m.awayGoals! : m.homeGoals!;
    const bucket = isHome ? home : away;
    for (const b of [record, bucket]) {
      b.matches++;
      b.goalsFor += gf;
      b.goalsAgainst += ga;
      if (gf > ga) b.wins++;
      else if (gf < ga) b.losses++;
      else b.draws++;
    }
  }
  return { record, home, away, matches };
}

// ---------------------------------------------------------------------------
// Standings
// ---------------------------------------------------------------------------

/** Round-robin competitions for which standings can be computed. */
export const STANDINGS_COMPETITIONS = new Set<string>([
  'Brasileirão Série A',
  'Brasileirão Série B',
  'Brasileirão Série C',
]);

export function computeStandings(
  store: DatasetStore,
  competition: Competition,
  season: number,
): StandingRow[] {
  const matches = searchMatches(store, { competition, season });
  const table = new Map<string, StandingRow & { team: TeamIdentity }>();

  const rowFor = (t: TeamIdentity) => {
    let row = table.get(t.key);
    if (!row) {
      row = {
        team: t, position: 0, points: 0, goalDifference: 0,
        matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0,
      };
      table.set(t.key, row);
    }
    return row;
  };

  for (const m of matches) {
    const h = rowFor(m.homeTeam);
    const a = rowFor(m.awayTeam);
    h.matches++; a.matches++;
    h.goalsFor += m.homeGoals!; h.goalsAgainst += m.awayGoals!;
    a.goalsFor += m.awayGoals!; a.goalsAgainst += m.homeGoals!;
    if (m.homeGoals! > m.awayGoals!) {
      h.wins++; h.points += 3; a.losses++;
    } else if (m.homeGoals! < m.awayGoals!) {
      a.wins++; a.points += 3; h.losses++;
    } else {
      h.draws++; a.draws++; h.points++; a.points++;
    }
  }

  const rows = [...table.values()];
  for (const r of rows) r.goalDifference = r.goalsFor - r.goalsAgainst;
  rows.sort(
    (x, y) =>
      y.points - x.points ||
      y.wins - x.wins ||
      y.goalDifference - x.goalDifference ||
      y.goalsFor - x.goalsFor ||
      x.team.displayName.localeCompare(y.team.displayName),
  );
  rows.forEach((r, i) => (r.position = i + 1));
  return rows;
}

// ---------------------------------------------------------------------------
// Aggregated statistics
// ---------------------------------------------------------------------------

export interface MatchStatistics {
  matches: number;
  totalGoals: number;
  avgGoalsPerMatch: number;
  homeWins: number;
  draws: number;
  awayWins: number;
  homeWinRate: number;
  drawRate: number;
  awayWinRate: number;
}

export function matchStatistics(store: DatasetStore, filter: MatchFilter): MatchStatistics {
  const matches = searchMatches(store, filter);
  let goals = 0;
  let homeWins = 0;
  let draws = 0;
  let awayWins = 0;
  for (const m of matches) {
    goals += m.homeGoals! + m.awayGoals!;
    if (m.homeGoals! > m.awayGoals!) homeWins++;
    else if (m.homeGoals! < m.awayGoals!) awayWins++;
    else draws++;
  }
  const n = matches.length;
  return {
    matches: n,
    totalGoals: goals,
    avgGoalsPerMatch: n ? goals / n : 0,
    homeWins,
    draws,
    awayWins,
    homeWinRate: n ? homeWins / n : 0,
    drawRate: n ? draws / n : 0,
    awayWinRate: n ? awayWins / n : 0,
  };
}

export interface BigWin {
  match: Match;
  winner: TeamIdentity;
  loser: TeamIdentity;
  margin: number;
  score: string;
}

export function biggestWins(
  store: DatasetStore,
  filter: MatchFilter,
  limit = 10,
): BigWin[] {
  return searchMatches(store, filter)
    .filter((m) => m.homeGoals !== m.awayGoals)
    .map((m) => {
      const homeWon = m.homeGoals! > m.awayGoals!;
      return {
        match: m,
        winner: homeWon ? m.homeTeam : m.awayTeam,
        loser: homeWon ? m.awayTeam : m.homeTeam,
        margin: Math.abs(m.homeGoals! - m.awayGoals!),
        score: `${m.homeGoals}-${m.awayGoals}`,
      };
    })
    .sort((a, b) => b.margin - a.margin || b.match.homeGoals! + b.match.awayGoals! - (a.match.homeGoals! + a.match.awayGoals!))
    .slice(0, limit);
}

export interface TeamGoals {
  team: TeamIdentity;
  goals: number;
  matches: number;
  avgPerMatch: number;
}

export function topScoringTeams(
  store: DatasetStore,
  filter: MatchFilter,
  limit = 10,
): TeamGoals[] {
  const matches = searchMatches(store, filter);
  const agg = new Map<string, TeamGoals>();
  const bump = (t: TeamIdentity, goals: number) => {
    let row = agg.get(t.key);
    if (!row) {
      row = { team: t, goals: 0, matches: 0, avgPerMatch: 0 };
      agg.set(t.key, row);
    }
    row.goals += goals;
  };
  const played = new Map<string, number>();
  for (const m of matches) {
    bump(m.homeTeam, m.homeGoals!);
    bump(m.awayTeam, m.awayGoals!);
    played.set(m.homeTeam.key, (played.get(m.homeTeam.key) ?? 0) + 1);
    played.set(m.awayTeam.key, (played.get(m.awayTeam.key) ?? 0) + 1);
  }
  const rows = [...agg.values()];
  for (const r of rows) {
    r.matches = played.get(r.team.key) ?? 0;
    r.avgPerMatch = r.matches ? r.goals / r.matches : 0;
  }
  return rows
    .sort((a, b) => b.goals - a.goals || b.avgPerMatch - a.avgPerMatch)
    .slice(0, limit);
}

// ---------------------------------------------------------------------------
// Competitions
// ---------------------------------------------------------------------------

export interface CompetitionInfo {
  competition: Competition;
  seasons: number[];
  matches: number;
}

export function listCompetitions(store: DatasetStore): CompetitionInfo[] {
  const out: CompetitionInfo[] = [];
  for (const [competition, seasons] of store.competitions) {
    const matches = store.dedupedMatches.filter((m) => m.competition === competition).length;
    out.push({
      competition,
      seasons: [...seasons].sort((a, b) => a - b),
      matches,
    });
  }
  return out.sort((a, b) => a.competition.localeCompare(b.competition));
}

export interface TeamCompetitions {
  team: TeamIdentity;
  competitions: { competition: Competition; seasons: number[]; matches: number }[];
}

export function teamCompetitions(store: DatasetStore, team: TeamIdentity): TeamCompetitions {
  const matches = searchMatches(store, { team });
  const byComp = new Map<Competition, { seasons: Set<number>; matches: number }>();
  for (const m of matches) {
    let e = byComp.get(m.competition);
    if (!e) {
      e = { seasons: new Set(), matches: 0 };
      byComp.set(m.competition, e);
    }
    e.matches++;
    if (m.season !== undefined) e.seasons.add(m.season);
  }
  return {
    team,
    competitions: [...byComp.entries()]
      .map(([competition, e]) => ({
        competition,
        seasons: [...e.seasons].sort((a, b) => a - b),
        matches: e.matches,
      }))
      .sort((a, b) => b.matches - a.matches),
  };
}

// ---------------------------------------------------------------------------
// Players
// ---------------------------------------------------------------------------

export const POSITION_GROUPS: Record<string, string[]> = {
  GK: ['GK'],
  DEF: ['CB', 'LCB', 'RCB', 'LB', 'RB', 'LWB', 'RWB'],
  MID: ['CM', 'LCM', 'RCM', 'CDM', 'LDM', 'RDM', 'CAM', 'LAM', 'RAM', 'LM', 'RM'],
  FWD: ['ST', 'CF', 'LW', 'RW', 'LF', 'RF', 'LS', 'RS'],
};

export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  positionGroup?: 'GK' | 'DEF' | 'MID' | 'FWD';
  minOverall?: number;
  limit?: number;
}

export function searchPlayers(store: DatasetStore, filter: PlayerFilter): Player[] {
  const nameQ = filter.name ? simplify(filter.name) : undefined;
  const natQ = filter.nationality ? simplify(filter.nationality) : undefined;
  const clubQ = filter.club ? parseTeamName(filter.club).base : undefined;
  const posQ = filter.position?.toUpperCase();
  const group = filter.positionGroup ? POSITION_GROUPS[filter.positionGroup] : undefined;

  let out = store.players.filter((p) => {
    if (nameQ && !simplify(p.name).includes(nameQ)) return false;
    if (natQ && simplify(p.nationality ?? '') !== natQ) return false;
    if (clubQ) {
      if (!p.club) return false;
      const clubParsed = parseTeamName(p.club);
      if (clubParsed.base !== clubQ && !simplify(p.club).includes(clubQ)) return false;
    }
    if (posQ && p.position !== posQ) return false;
    if (group && (!p.position || !group.includes(p.position))) return false;
    if (filter.minOverall !== undefined && (p.overall ?? 0) < filter.minOverall) return false;
    return true;
  });

  out = out.sort(
    (a, b) => (b.overall ?? 0) - (a.overall ?? 0) || a.name.localeCompare(b.name),
  );
  return out.slice(0, filter.limit ?? 20);
}

/** Exact-ish player lookup for profiles: best name match wins. */
export function findPlayer(store: DatasetStore, name: string): Player[] {
  const q = simplify(name);
  const scored = store.players
    .map((p) => {
      const n = simplify(p.name);
      let score = 0;
      if (n === q) score = 3;
      else if (n.startsWith(q)) score = 2;
      else if (n.includes(q)) score = 1;
      return { p, score };
    })
    .filter((s) => s.score > 0)
    .sort((a, b) => b.score - a.score || (b.p.overall ?? 0) - (a.p.overall ?? 0));
  return scored.slice(0, 5).map((s) => s.p);
}

/** Club-level summary: how many players and average rating. */
export function clubPlayerSummary(
  store: DatasetStore,
  clubQuery: string,
): { club: string; players: number; avgOverall: number }[] {
  const q = parseTeamName(clubQuery).base;
  const byClub = new Map<string, { count: number; total: number }>();
  for (const p of store.players) {
    if (!p.club) continue;
    const parsed = parseTeamName(p.club);
    if (parsed.base !== q && !simplify(p.club).includes(q)) continue;
    const e = byClub.get(p.club) ?? { count: 0, total: 0 };
    e.count++;
    e.total += p.overall ?? 0;
    byClub.set(p.club, e);
  }
  return [...byClub.entries()]
    .map(([club, e]) => ({
      club,
      players: e.count,
      avgOverall: e.count ? e.total / e.count : 0,
    }))
    .sort((a, b) => b.players - a.players);
}

/** Brazilian players grouped by club (spec example). */
export function brazilianPlayersByClub(
  store: DatasetStore,
  limit = 15,
): { club: string; players: number; avgOverall: number }[] {
  const byClub = new Map<string, { count: number; total: number }>();
  for (const p of store.players) {
    if (p.nationality !== 'Brazil' || !p.club) continue;
    const e = byClub.get(p.club) ?? { count: 0, total: 0 };
    e.count++;
    e.total += p.overall ?? 0;
    byClub.set(p.club, e);
  }
  return [...byClub.entries()]
    .map(([club, e]) => ({
      club,
      players: e.count,
      avgOverall: e.count ? e.total / e.count : 0,
    }))
    .sort((a, b) => b.players - a.players || b.avgOverall - a.avgOverall)
    .slice(0, limit);
}

export { normalizeCompetition };
