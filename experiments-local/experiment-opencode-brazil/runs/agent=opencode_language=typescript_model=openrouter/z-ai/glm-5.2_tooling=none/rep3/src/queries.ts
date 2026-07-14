/**
 * Brazilian Soccer MCP Server - Query Layer
 * -----------------------------------------
 * Context: Pure functions that operate on the in-memory `SoccerData` model
 * produced by `loader.ts`. These functions implement the five required query
 * capabilities from the spec:
 *   1. Match queries (by team, opponent, competition, season, date range)
 *   2. Team queries (per-season stats, home/away splits)
 *   3. Player queries (filter + sort by name, nationality, club, position, rating)
 *   4. Competition queries (computed standings for a season)
 *   5. Statistical analysis (avg goals, biggest wins, best records, head-to-head)
 *
 * Every function is deterministic and side-effect free, which keeps the MCP
 * tool layer thin and the unit tests simple.
 */

import type {
  HeadToHead,
  Match,
  MatchQuery,
  Player,
  PlayerQuery,
  Standing,
  TeamStats,
} from "./types.js";
import type { SoccerData } from "./loader.js";
import { normalizeTeamName } from "./normalize.js";

/** Filter matches by a structured query. Returns most-recent-first. */
export function findMatches(data: SoccerData, q: MatchQuery): Match[] {
  const team = q.team ? normalizeTeamName(q.team) : undefined;
  const opponent = q.opponent ? normalizeTeamName(q.opponent) : undefined;
  const competition = q.competition && q.competition !== "any" ? q.competition : undefined;
  const limit = q.limit && q.limit > 0 ? q.limit : undefined;

  let out = data.matches.filter((m) => {
    if (team) {
      const isHome = m.homeTeam === team;
      const isAway = m.awayTeam === team;
      if (!isHome && !isAway) return false;
      if (opponent) {
        const opp = opponent;
        const oppHome = m.homeTeam === opp;
        const oppAway = m.awayTeam === opp;
        // Need team and opponent both present.
        if (!((isHome && oppAway) || (isAway && oppHome))) return false;
      }
    } else if (opponent) {
      // Only opponent specified -> include matches where opponent plays.
      if (m.homeTeam !== opponent && m.awayTeam !== opponent) return false;
    }
    if (competition && m.competition !== competition) return false;
    if (q.season && m.season !== q.season) return false;
    if (q.startDate && m.date < q.startDate) return false;
    if (q.endDate && m.date > q.endDate) return false;
    return true;
  });

  out = sortMatchesByDateDesc(out);
  if (limit) out = out.slice(0, limit);
  return out;
}

function sortMatchesByDateDesc(matches: Match[]): Match[] {
  return [...matches].sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
}

/** Return all matches between two teams, most-recent-first. */
export function findHeadToHeadMatches(
  data: SoccerData,
  teamA: string,
  teamB: string,
): Match[] {
  const a = normalizeTeamName(teamA);
  const b = normalizeTeamName(teamB);
  const matches = data.matches.filter(
    (m) =>
      (m.homeTeam === a && m.awayTeam === b) ||
      (m.homeTeam === b && m.awayTeam === a),
  );
  return sortMatchesByDateDesc(matches);
}

/** Compute the head-to-head summary between two teams. */
export function headToHead(
  data: SoccerData,
  teamA: string,
  teamB: string,
): HeadToHead {
  const a = normalizeTeamName(teamA);
  const b = normalizeTeamName(teamB);
  const matches = findHeadToHeadMatches(data, teamA, teamB);
  let aWins = 0,
    bWins = 0,
    draws = 0,
    aGoals = 0,
    bGoals = 0;
  for (const m of matches) {
    const aIsHome = m.homeTeam === a;
    const aGoalsIn = aIsHome ? m.homeGoal : m.awayGoal;
    const bGoalsIn = aIsHome ? m.awayGoal : m.homeGoal;
    aGoals += aGoalsIn;
    bGoals += bGoalsIn;
    if (aGoalsIn > bGoalsIn) aWins++;
    else if (bGoalsIn > aGoalsIn) bWins++;
    else draws++;
  }
  return {
    teamA: a,
    teamB: b,
    matches: matches.length,
    teamAWins: aWins,
    teamBWins: bWins,
    draws,
    teamAGoals: aGoals,
    teamBGoals: bGoals,
    recent: matches,
  };
}

/** Compute aggregate stats for a team, optionally restricted by season/competition. */
export function teamStats(
  data: SoccerData,
  team: string,
  opts?: { season?: number; competition?: string },
): TeamStats {
  const t = normalizeTeamName(team);
  const matches = data.matches.filter(
    (m) =>
      (m.homeTeam === t || m.awayTeam === t) &&
      (!opts?.season || m.season === opts.season) &&
      (!opts?.competition || m.competition === opts.competition),
  );
  return computeTeamStats(t, matches);
}

/** Compute stats from an explicit list of matches involving one team. */
function computeTeamStats(team: string, matches: Match[]): TeamStats {
  const home: TeamStats["home"] = {
    matches: 0,
    wins: 0,
    draws: 0,
    losses: 0,
    goalsFor: 0,
    goalsAgainst: 0,
  };
  const away: TeamStats["away"] = {
    matches: 0,
    wins: 0,
    draws: 0,
    losses: 0,
    goalsFor: 0,
    goalsAgainst: 0,
  };
  let wins = 0,
    draws = 0,
    losses = 0,
    goalsFor = 0,
    goalsAgainst = 0;

  for (const m of matches) {
    const isHome = m.homeTeam === team;
    const gf = isHome ? m.homeGoal : m.awayGoal;
    const ga = isHome ? m.awayGoal : m.homeGoal;
    goalsFor += gf;
    goalsAgainst += ga;
    let result: "win" | "draw" | "loss";
    if (gf > ga) result = "win";
    else if (ga > gf) result = "loss";
    else result = "draw";
    if (result === "win") wins++;
    else if (result === "draw") draws++;
    else losses++;

    const v = isHome ? home : away;
    v.matches++;
    v.goalsFor += gf;
    v.goalsAgainst += ga;
    if (result === "win") v.wins++;
    else if (result === "draw") v.draws++;
    else v.losses++;
  }
  const points = wins * 3 + draws;
  return {
    team,
    matches: matches.length,
    wins,
    draws,
    losses,
    goalsFor,
    goalsAgainst,
    goalDifference: goalsFor - goalsAgainst,
    points,
    home,
    away,
  };
}

/** Search the FIFA player database. */
export function findPlayers(data: SoccerData, q: PlayerQuery): Player[] {
  let out = data.players.filter((p) => {
    if (q.name) {
      const needle = q.name.toLowerCase();
      if (!p.name.toLowerCase().includes(needle)) return false;
    }
    if (q.nationality) {
      const needle = q.nationality.toLowerCase();
      if (!p.nationality.toLowerCase().includes(needle)) return false;
    }
    if (q.club) {
      const needle = normalizeTeamName(q.club);
      const club = normalizeTeamName(p.club);
      if (!club.includes(needle)) return false;
    }
    if (q.position) {
      const needle = q.position.toLowerCase();
      if (!p.position.toLowerCase().includes(needle)) return false;
    }
    if (q.minOverall !== undefined && p.overall < q.minOverall) return false;
    return true;
  });

  const sortBy = q.sortBy ?? "overall";
  const descending = q.descending ?? true;
  out = out.sort((a, b) => {
    let cmp = 0;
    if (sortBy === "name") cmp = a.name.localeCompare(b.name);
    else cmp = (a[sortBy] as number) - (b[sortBy] as number);
    return descending ? -cmp : cmp;
  });

  const limit = q.limit && q.limit > 0 ? q.limit : 50;
  return out.slice(0, limit);
}

/** Compute standings for a league/competition season. */
export function standings(
  data: SoccerData,
  competition: string,
  season: number,
  limit?: number,
): Standing[] {
  const matches = data.matches.filter(
    (m) => m.competition === competition && m.season === season,
  );
  const teams = new Set<string>();
  for (const m of matches) {
    teams.add(m.homeTeam);
    teams.add(m.awayTeam);
  }
  const rows: Standing[] = [];
  for (const t of teams) {
    const stats = computeTeamStats(
      t,
      matches.filter((m) => m.homeTeam === t || m.awayTeam === t),
    );
    rows.push({
      position: 0,
      team: t,
      played: stats.matches,
      wins: stats.wins,
      draws: stats.draws,
      losses: stats.losses,
      goalsFor: stats.goalsFor,
      goalsAgainst: stats.goalsAgainst,
      goalDifference: stats.goalDifference,
      points: stats.points,
    });
  }
  rows.sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    if (b.wins !== a.wins) return b.wins - a.wins;
    if (b.goalDifference !== a.goalDifference)
      return b.goalDifference - a.goalDifference;
    if (b.goalsFor !== a.goalsFor) return b.goalsFor - a.goalsFor;
    return a.team.localeCompare(b.team);
  });
  rows.forEach((r, i) => (r.position = i + 1));
  return limit ? rows.slice(0, limit) : rows;
}

/** Average goals per match across a (filtered) set of matches. */
export function averageGoals(matches: Match[]): {
  perMatch: number;
  totalMatches: number;
  totalGoals: number;
  homeWinRate: number;
  drawRate: number;
  awayWinRate: number;
} {
  const totalMatches = matches.length;
  if (totalMatches === 0) {
    return {
      perMatch: 0,
      totalMatches: 0,
      totalGoals: 0,
      homeWinRate: 0,
      drawRate: 0,
      awayWinRate: 0,
    };
  }
  let totalGoals = 0,
    homeWins = 0,
    draws = 0,
    awayWins = 0;
  for (const m of matches) {
    totalGoals += m.homeGoal + m.awayGoal;
    if (m.winner === "home") homeWins++;
    else if (m.winner === "away") awayWins++;
    else draws++;
  }
  return {
    perMatch: totalGoals / totalMatches,
    totalMatches,
    totalGoals,
    homeWinRate: homeWins / totalMatches,
    drawRate: draws / totalMatches,
    awayWinRate: awayWins / totalMatches,
  };
}

/** Return the biggest victories (by goal difference) in a set of matches. */
export function biggestWins(matches: Match[], limit = 10): Array<{
  match: Match;
  goalDifference: number;
}> {
  return matches
    .map((m) => ({ match: m, goalDifference: Math.abs(m.homeGoal - m.awayGoal) }))
    .filter((x) => x.goalDifference > 0)
    .sort((a, b) => b.goalDifference - a.goalDifference)
    .slice(0, limit);
}

/** Return the team with the best record over the given matches. */
export function bestTeamRecord(
  data: SoccerData,
  matches: Match[],
  venue?: "home" | "away",
): { team: string; stats: TeamStats } | null {
  const teams = new Set<string>();
  for (const m of matches) {
    if (!venue || venue === "home") teams.add(m.homeTeam);
    if (!venue || venue === "away") teams.add(m.awayTeam);
  }
  let best: { team: string; stats: TeamStats } | null = null;
  for (const t of teams) {
    const teamMatches = matches.filter(
      (m) =>
        (venue === "home" && m.homeTeam === t) ||
        (venue === "away" && m.awayTeam === t) ||
        (!venue && (m.homeTeam === t || m.awayTeam === t)),
    );
    if (teamMatches.length === 0) continue;
    const stats = computeTeamStats(t, teamMatches);
    if (!best || stats.points > best.stats.points) {
      best = { team: t, stats };
    }
  }
  return best;
}

/** Distinct competitions a team has played in. */
export function competitionsForTeam(data: SoccerData, team: string): string[] {
  const t = normalizeTeamName(team);
  const set = new Set<string>();
  for (const m of data.matches) {
    if (m.homeTeam === t || m.awayTeam === t) {
      set.add(m.competition);
    }
  }
  return Array.from(set);
}
