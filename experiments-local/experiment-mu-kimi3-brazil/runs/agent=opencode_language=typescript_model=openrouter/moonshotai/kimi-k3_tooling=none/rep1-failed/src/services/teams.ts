/**
 * Team-query service: win/draw/loss records, goals, home/away splits,
 * per-competition performance.
 */
import type { Dataset, Match, Record } from "../types.js";
import { teamMatches } from "../normalize.js";
import { competitionMatches } from "./matches.js";

export interface TeamStats extends Record {
  team: string;
  home: Record;
  away: Record;
  /** Per-competition breakdown. */
  byCompetition: Map<string, Record>;
  /** Distinct display names seen for this club in the data. */
  seenAs: Set<string>;
}

function emptyRecord(): Record {
  return { matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0 };
}

function accrue(rec: Record, gf: number, ga: number): void {
  rec.matches++;
  rec.goalsFor += gf;
  rec.goalsAgainst += ga;
  if (gf > ga) rec.wins++;
  else if (gf < ga) rec.losses++;
  else rec.draws++;
}

/**
 * Aggregate a team's record. Optional filters: season, competition.
 * Splits home vs away and per-competition subtotals.
 */
export function teamStats(
  ds: Dataset,
  team: string,
  opts: { season?: number; competition?: string } = {},
): TeamStats {
  const stats: TeamStats = {
    team,
    matches: 0,
    wins: 0,
    draws: 0,
    losses: 0,
    goalsFor: 0,
    goalsAgainst: 0,
    home: emptyRecord(),
    away: emptyRecord(),
    byCompetition: new Map(),
    seenAs: new Set(),
  };
  for (const m of ds.matches) {
    if (opts.season !== undefined && m.season !== opts.season) continue;
    if (opts.competition && !competitionMatches(m.competition, opts.competition)) continue;
    const isHome = teamMatches(m.homeTeamRaw, team);
    const isAway = teamMatches(m.awayTeamRaw, team);
    if (!isHome && !isAway) continue;

    const gf = isHome ? m.homeGoals : m.awayGoals;
    const ga = isHome ? m.awayGoals : m.homeGoals;
    accrue(stats, gf, ga);
    accrue(isHome ? stats.home : stats.away, gf, ga);
    let comp = stats.byCompetition.get(m.competition);
    if (!comp) {
      comp = emptyRecord();
      stats.byCompetition.set(m.competition, comp);
    }
    accrue(comp, gf, ga);
    stats.seenAs.add(isHome ? m.homeTeam : m.awayTeam);
  }
  return stats;
}

/** Distinct competitions a team appears in, with match counts. */
export function teamCompetitions(ds: Dataset, team: string): Map<string, number> {
  const out = new Map<string, number>();
  for (const m of ds.matches) {
    if (teamMatches(m.homeTeamRaw, team) || teamMatches(m.awayTeamRaw, team)) {
      out.set(m.competition, (out.get(m.competition) ?? 0) + 1);
    }
  }
  return out;
}

export interface TeamSeasonGoals {
  team: string;
  goalsFor: number;
  matches: number;
}

/** Ranking: teams that scored the most goals in a competition/season. */
export function mostGoalsScored(
  ds: Dataset,
  opts: { competition?: string; season?: number; limit?: number } = {},
): TeamSeasonGoals[] {
  const acc = new Map<string, TeamSeasonGoals>();
  for (const m of ds.matches) {
    if (opts.competition && !competitionMatches(m.competition, opts.competition)) continue;
    if (opts.season !== undefined && m.season !== opts.season) continue;
    for (const [key, team, goals] of [
      [m.homeKey, m.homeTeam, m.homeGoals],
      [m.awayKey, m.awayTeam, m.awayGoals],
    ] as const) {
      const cur = acc.get(key) ?? { team, goalsFor: 0, matches: 0 };
      cur.goalsFor += goals;
      cur.matches++;
      acc.set(key, cur);
    }
  }
  return [...acc.values()]
    .sort((a, b) => b.goalsFor - a.goalsFor)
    .slice(0, opts.limit ?? 10);
}
