/**
 * Competition service: league standings calculated from match results,
 * plus cup finals lookup.
 */
import type { Dataset } from "../types.js";
import { competitionMatches, findMatches } from "./matches.js";
import type { Match } from "../types.js";

export interface StandingRow {
  position: number;
  team: string;
  points: number;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
}

/**
 * Compute a league table (3-1-0 points) from match results.
 * Ties broken by wins, then goal difference, then goals for
 * (CBF tie-break order).
 */
export function standings(
  ds: Dataset,
  opts: { competition: string; season?: number },
): StandingRow[] {
  const table = new Map<string, StandingRow>();
  const ensure = (key: string, team: string): StandingRow => {
    let row = table.get(key);
    if (!row) {
      row = {
        position: 0,
        team,
        points: 0,
        played: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        goalsFor: 0,
        goalsAgainst: 0,
        goalDifference: 0,
      };
      table.set(key, row);
    }
    return row;
  };

  for (const m of ds.matches) {
    if (!competitionMatches(m.competition, opts.competition)) continue;
    if (opts.season !== undefined && m.season !== opts.season) continue;
    const home = ensure(m.homeKey, m.homeTeam);
    const away = ensure(m.awayKey, m.awayTeam);
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

  const rows = [...table.values()];
  for (const r of rows) r.goalDifference = r.goalsFor - r.goalsAgainst;
  rows.sort(
    (a, b) =>
      b.points - a.points ||
      b.wins - a.wins ||
      b.goalDifference - a.goalDifference ||
      b.goalsFor - a.goalsFor ||
      a.team.localeCompare(b.team),
  );
  rows.forEach((r, i) => (r.position = i + 1));
  return rows;
}

/**
 * Find cup finals: Copa do Brasil finals are the highest-numbered round
 * (round "8"); Libertadores finals carry stage "final".
 */
export function findFinals(
  ds: Dataset,
  opts: { competition: string; season?: number; limit?: number },
): Match[] {
  return findMatches(ds, {
    competition: opts.competition,
    season: opts.season,
    stage: "final",
    limit: opts.limit ?? 30,
  });
}

/** Seasons available for a competition. */
export function competitionSeasons(ds: Dataset, competition: string): number[] {
  const seasons = new Set<number>();
  for (const m of ds.matches) {
    if (m.season !== null && competitionMatches(m.competition, competition)) {
      seasons.add(m.season);
    }
  }
  return [...seasons].sort((a, b) => a - b);
}
