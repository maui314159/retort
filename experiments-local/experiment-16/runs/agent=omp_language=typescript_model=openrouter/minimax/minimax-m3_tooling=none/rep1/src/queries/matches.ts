/**
 * Match query helpers.
 *
 * Every helper accepts a {@link DatasetSnapshot} and a
 * {@link MatchQuery} filter; the filter is intentionally permissive so
 * one call site can satisfy many natural-language phrasings.
 */

import type { Competition, DatasetSnapshot, Match } from '../data/types.js';
import { teamMatches } from '../data/normalizer.js';

export interface MatchQuery {
  team?: string;
  team2?: string;
  competition?: Competition | Competition[] | 'all';
  season?: number | [number, number];
  dateRange?: [string, string]; // yyyy-mm-dd inclusive
  limit?: number;
  includeUnknownScores?: boolean;
  asTeam?: 'home' | 'away' | 'either';
  stage?: string;
}

function inSeason(m: Match, s: MatchQuery['season']): boolean {
  if (s === undefined) return true;
  if (typeof s === 'number') return m.season === s;
  return m.season >= s[0] && m.season <= s[1];
}

function inDateRange(m: Match, range: [string, string] | undefined): boolean {
  if (!range) return true;
  if (!m.date) return false;
  return m.date >= range[0] && m.date <= range[1];
}

function competitionAllowed(m: Match, comp: MatchQuery['competition']): boolean {
  if (comp === undefined || comp === 'all') return true;
  if (Array.isArray(comp)) return comp.includes(m.competition);
  return m.competition === comp;
}

function hasScore(m: Match): boolean {
  return m.homeGoal !== null && m.awayGoal !== null;
}

/**
 * Apply a {@link MatchQuery} and return the matching matches sorted by
 * date descending. The list is bounded by `limit` when provided.
 */
export function findMatches(snap: DatasetSnapshot, q: MatchQuery): Match[] {
  const asTeam = q.asTeam ?? 'either';
  const limit = q.limit ?? Number.POSITIVE_INFINITY;
  const includeUnknown = q.includeUnknownScores ?? true;

  const out: Match[] = [];
  for (const m of snap.matches) {
    if (!competitionAllowed(m, q.competition)) continue;
    if (!inSeason(m, q.season)) continue;
    if (!inDateRange(m, q.dateRange)) continue;
    if (q.stage && m.stage && strip(m.stage).toLowerCase() !== strip(q.stage).toLowerCase()) continue;

    if (q.team && q.team2) {
      const t1 = teamMatches(m.homeTeam, q.team) || teamMatches(m.awayTeam, q.team);
      const t2 = teamMatches(m.homeTeam, q.team2) || teamMatches(m.awayTeam, q.team2);
      if (!(t1 && t2)) continue;
    } else if (q.team) {
      const home = teamMatches(m.homeTeam, q.team);
      const away = teamMatches(m.awayTeam, q.team);
      if (asTeam === 'home' && !home) continue;
      if (asTeam === 'away' && !away) continue;
      if (asTeam === 'either' && !home && !away) continue;
    }

    if (!includeUnknown && !hasScore(m)) continue;
    out.push(m);
  }

  out.sort((a, b) => {
    if (a.date === b.date) return 0;
    return a.date < b.date ? 1 : -1;
  });
  return out.slice(0, limit);
}

function strip(s: string): string {
  return s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}

export function mostRecentMatch(snap: DatasetSnapshot, team1: string, team2: string): Match | undefined {
  const list = findMatches(snap, { team: team1, team2, limit: 1, includeUnknownScores: true });
  return list[0];
}
