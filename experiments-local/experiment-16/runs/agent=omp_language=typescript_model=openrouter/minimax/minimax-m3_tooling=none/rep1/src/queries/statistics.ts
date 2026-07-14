/**
 * Statistical aggregates that don't fit into the per-team or
 * per-player queries: average goals, biggest wins, etc.
 */

import type { Competition, DatasetSnapshot, Match } from '../data/types.js';
import { findMatches } from './matches.js';

export interface GoalsStats {
  matches: number;
  totalGoals: number;
  averageGoals: number;
  homeWins: number;
  draws: number;
  awayWins: number;
  homeWinRate: number;
  cleanSheets: number;
}

export function goalsStats(snap: DatasetSnapshot, competition?: Competition | Competition[]): GoalsStats {
  const matches = findMatches(snap, { competition: competition ?? 'all', includeUnknownScores: false });
  const out: GoalsStats = {
    matches: 0, totalGoals: 0, averageGoals: 0,
    homeWins: 0, draws: 0, awayWins: 0, homeWinRate: 0, cleanSheets: 0
  };
  for (const m of matches) {
    if (m.homeGoal === null || m.awayGoal === null) continue;
    out.matches++;
    out.totalGoals += m.homeGoal + m.awayGoal;
    if (m.homeGoal > m.awayGoal) out.homeWins++;
    else if (m.homeGoal < m.awayGoal) out.awayWins++;
    else out.draws++;
    if (m.homeGoal === 0 || m.awayGoal === 0) out.cleanSheets++;
  }
  out.averageGoals = out.matches === 0 ? 0 : Math.round((out.totalGoals / out.matches) * 100) / 100;
  out.homeWinRate = out.matches === 0 ? 0 : Math.round((out.homeWins / out.matches) * 1000) / 10;
  return out;
}

export interface BiggestWin {
  match: Match;
  margin: number;
}

/**
 * Largest margin of victory, optionally constrained to a competition
 * and a season range.
 */
export function biggestWins(snap: DatasetSnapshot, opts: { competition?: Competition | Competition[] | 'all'; limit?: number; season?: number | [number, number] } = {}): BiggestWin[] {
  const list = findMatches(snap, {
    competition: opts.competition ?? 'all',
    season: opts.season,
    includeUnknownScores: false
  });
  const scored: BiggestWin[] = [];
  for (const m of list) {
    if (m.homeGoal === null || m.awayGoal === null) continue;
    const margin = Math.abs(m.homeGoal - m.awayGoal);
    scored.push({ match: m, margin });
  }
  scored.sort((a, b) => b.margin - a.margin || (a.match.date < b.match.date ? 1 : -1));
  return scored.slice(0, opts.limit ?? 10);
}

export interface HomeAwayComparison {
  team: string;
  homeWinRate: number;
  awayWinRate: number;
  homeRecord: { matches: number; wins: number; draws: number; losses: number };
  awayRecord: { matches: number; wins: number; draws: number; losses: number };
}

export function bestHomeRecord(snap: DatasetSnapshot, limit = 5, minMatches = 10): HomeAwayComparison[] {
  const totals = new Map<string, { home: { matches: number; wins: number; draws: number; losses: number }; away: { matches: number; wins: number; draws: number; losses: number } }>();
  for (const m of snap.matches) {
    if (m.homeGoal === null || m.awayGoal === null) continue;
    const inc = (slot: { matches: number; wins: number; draws: number; losses: number }, isHome: boolean) => {
      slot.matches++;
      const my = isHome ? m.homeGoal! : m.awayGoal!;
      const op = isHome ? m.awayGoal! : m.homeGoal!;
      if (my > op) slot.wins++;
      else if (my < op) slot.losses++;
      else slot.draws++;
    };
    const entry = totals.get(m.homeTeam) ?? { home: { matches: 0, wins: 0, draws: 0, losses: 0 }, away: { matches: 0, wins: 0, draws: 0, losses: 0 } };
    inc(entry.home, true);
    totals.set(m.homeTeam, entry);
    const entry2 = totals.get(m.awayTeam) ?? { home: { matches: 0, wins: 0, draws: 0, losses: 0 }, away: { matches: 0, wins: 0, draws: 0, losses: 0 } };
    inc(entry2.away, false);
    totals.set(m.awayTeam, entry2);
  }
  const out: HomeAwayComparison[] = [];
  for (const [team, rec] of totals.entries()) {
    if (rec.home.matches < minMatches) continue;
    out.push({
      team,
      homeWinRate: Math.round((rec.home.wins / rec.home.matches) * 1000) / 10,
      awayWinRate: Math.round((rec.away.wins / rec.away.matches) * 1000) / 10,
      homeRecord: rec.home,
      awayRecord: rec.away
    });
  }
  out.sort((a, b) => b.homeWinRate - a.homeWinRate || a.team.localeCompare(b.team));
  return out.slice(0, limit);
}
