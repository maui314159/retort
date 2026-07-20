/**
 * Statistical-analysis service: dataset-wide aggregates such as goals
 * per match, home advantage, biggest wins, and best home/away records.
 */
import type { Dataset, Match } from "../types.js";
import { competitionMatches } from "./matches.js";

export interface AggregateStats {
  matches: number;
  totalGoals: number;
  avgGoalsPerMatch: number;
  homeWins: number;
  draws: number;
  awayWins: number;
  homeWinRate: number;
  drawRate: number;
  awayWinRate: number;
  avgHomeGoals: number;
  avgAwayGoals: number;
}

/** Goals/result aggregates, optionally restricted by competition/season. */
export function aggregateStats(
  ds: Dataset,
  opts: { competition?: string; season?: number } = {},
): AggregateStats {
  let matches = 0,
    totalGoals = 0,
    homeGoals = 0,
    awayGoals = 0,
    homeWins = 0,
    draws = 0,
    awayWins = 0;
  for (const m of ds.matches) {
    if (opts.competition && !competitionMatches(m.competition, opts.competition)) continue;
    if (opts.season !== undefined && m.season !== opts.season) continue;
    matches++;
    totalGoals += m.homeGoals + m.awayGoals;
    homeGoals += m.homeGoals;
    awayGoals += m.awayGoals;
    if (m.homeGoals > m.awayGoals) homeWins++;
    else if (m.homeGoals < m.awayGoals) awayWins++;
    else draws++;
  }
  const safe = (n: number, d: number) => (d ? n / d : 0);
  return {
    matches,
    totalGoals,
    avgGoalsPerMatch: safe(totalGoals, matches),
    homeWins,
    draws,
    awayWins,
    homeWinRate: safe(homeWins, matches),
    drawRate: safe(draws, matches),
    awayWinRate: safe(awayWins, matches),
    avgHomeGoals: safe(homeGoals, matches),
    avgAwayGoals: safe(awayGoals, matches),
  };
}

/** Largest-margin victories, tie-broken by total goals. */
export function biggestWins(
  ds: Dataset,
  opts: { competition?: string; season?: number; limit?: number } = {},
): Match[] {
  const pool = ds.matches.filter((m) => {
    if (opts.competition && !competitionMatches(m.competition, opts.competition)) return false;
    if (opts.season !== undefined && m.season !== opts.season) return false;
    return m.homeGoals !== m.awayGoals;
  });
  pool.sort(
    (a, b) =>
      Math.abs(b.homeGoals - b.awayGoals) - Math.abs(a.homeGoals - a.awayGoals) ||
      b.homeGoals + b.awayGoals - (a.homeGoals + a.awayGoals),
  );
  return pool.slice(0, opts.limit ?? 10);
}

export interface VenueRecord {
  team: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  winRate: number;
}

/** Best home or away records by win rate (min matches to be meaningful). */
export function bestVenueRecords(
  ds: Dataset,
  venue: "home" | "away",
  opts: { competition?: string; season?: number; minMatches?: number; limit?: number } = {},
): VenueRecord[] {
  const acc = new Map<string, VenueRecord>();
  for (const m of ds.matches) {
    if (opts.competition && !competitionMatches(m.competition, opts.competition)) continue;
    if (opts.season !== undefined && m.season !== opts.season) continue;
    const key = venue === "home" ? m.homeKey : m.awayKey;
    const team = venue === "home" ? m.homeTeam : m.awayTeam;
    const gf = venue === "home" ? m.homeGoals : m.awayGoals;
    const ga = venue === "home" ? m.awayGoals : m.homeGoals;
    const rec =
      acc.get(key) ??
      ({ team, played: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0, winRate: 0 } as VenueRecord);
    rec.played++;
    rec.goalsFor += gf;
    rec.goalsAgainst += ga;
    if (gf > ga) rec.wins++;
    else if (gf < ga) rec.losses++;
    else rec.draws++;
    acc.set(key, rec);
  }
  const min = opts.minMatches ?? 10;
  return [...acc.values()]
    .filter((r) => r.played >= min)
    .map((r) => ({ ...r, winRate: r.played ? r.wins / r.played : 0 }))
    .sort((a, b) => b.winRate - a.winRate || b.wins - a.wins)
    .slice(0, opts.limit ?? 10);
}
