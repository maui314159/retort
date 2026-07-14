/**
 * Brazilian Soccer MCP Server - Query Engine
 *
 * Provides the core query functions that operate on loaded data:
 * match search, team statistics, player lookup, competition standings,
 * and statistical analysis. All functions accept simple filter parameters
 * and return structured results ready for MCP tool responses.
 */

import type {
  Match,
  Player,
  TeamRecord,
  HeadToHead,
  StandingEntry,
} from "./types.js";

/** Team name matching: case-insensitive, ignores accents on common chars */
export function teamMatches(team: string, query: string): boolean {
  const normalize = (s: string) =>
    s
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  return normalize(team).includes(normalize(query));
}

// ── Match queries ──────────────────────────────────────────────────

export function searchMatches(
  matches: Match[],
  opts: {
    team?: string;
    opponent?: string;
    competition?: string;
    season?: number;
    dateFrom?: string;
    dateTo?: string;
    limit?: number;
  }
): Match[] {
  let result = matches;

  if (opts.team) {
    const t = opts.team;
    result = result.filter(
      (m) => teamMatches(m.homeTeam, t) || teamMatches(m.awayTeam, t)
    );
  }

  if (opts.opponent) {
    const opp = opts.opponent;
    result = result.filter(
      (m) => teamMatches(m.homeTeam, opp) || teamMatches(m.awayTeam, opp)
    );
    // When both team & opponent given, ensure one is home and the other away
    if (opts.team) {
      const t = opts.team;
      result = result.filter(
        (m) =>
          (teamMatches(m.homeTeam, t) && teamMatches(m.awayTeam, opp)) ||
          (teamMatches(m.awayTeam, t) && teamMatches(m.homeTeam, opp))
      );
    }
  }

  if (opts.competition) {
    const comp = opts.competition.toLowerCase();
    result = result.filter((m) =>
      m.competition.toLowerCase().includes(comp)
    );
  }

  if (opts.season) {
    result = result.filter((m) => m.season === opts.season);
  }

  if (opts.dateFrom) {
    result = result.filter((m) => m.date >= opts.dateFrom!);
  }

  if (opts.dateTo) {
    result = result.filter((m) => m.date <= opts.dateTo!);
  }

  // Sort by date descending
  result.sort((a, b) => b.date.localeCompare(a.date));

  return opts.limit ? result.slice(0, opts.limit) : result;
}

// ── Team statistics ────────────────────────────────────────────────

export function getTeamRecord(
  matches: Match[],
  team: string,
  opts?: {
    season?: number;
    competition?: string;
    homeOnly?: boolean;
    awayOnly?: boolean;
  }
): TeamRecord {
  let filtered = matches.filter(
    (m) => teamMatches(m.homeTeam, team) || teamMatches(m.awayTeam, team)
  );

  if (opts?.season) filtered = filtered.filter((m) => m.season === opts.season);
  if (opts?.competition) {
    const comp = opts.competition.toLowerCase();
    filtered = filtered.filter((m) =>
      m.competition.toLowerCase().includes(comp)
    );
  }

  let wins = 0,
    draws = 0,
    losses = 0,
    gf = 0,
    ga = 0;

  for (const m of filtered) {
    const isHome = teamMatches(m.homeTeam, team);
    const isAway = teamMatches(m.awayTeam, team);

    if (opts?.homeOnly && !isHome) continue;
    if (opts?.awayOnly && !isAway) continue;

    if (isHome) {
      gf += m.homeGoals;
      ga += m.awayGoals;
      if (m.homeGoals > m.awayGoals) wins++;
      else if (m.homeGoals === m.awayGoals) draws++;
      else losses++;
    } else if (isAway) {
      gf += m.awayGoals;
      ga += m.homeGoals;
      if (m.awayGoals > m.homeGoals) wins++;
      else if (m.awayGoals === m.homeGoals) draws++;
      else losses++;
    }
  }

  const played = wins + draws + losses;
  return {
    team,
    wins,
    draws,
    losses,
    goalsFor: gf,
    goalsAgainst: ga,
    matches: played,
    points: wins * 3 + draws,
  };
}

export function getHeadToHead(
  matches: Match[],
  team1: string,
  team2: string
): HeadToHead {
  const headToHeadMatches = matches.filter(
    (m) =>
      (teamMatches(m.homeTeam, team1) && teamMatches(m.awayTeam, team2)) ||
      (teamMatches(m.awayTeam, team1) && teamMatches(m.homeTeam, team2))
  );

  let t1Wins = 0,
    t2Wins = 0,
    drawCount = 0;

  for (const m of headToHeadMatches) {
    const t1Home = teamMatches(m.homeTeam, team1);
    if (m.homeGoals === m.awayGoals) {
      drawCount++;
    } else if (t1Home) {
      if (m.homeGoals > m.awayGoals) t1Wins++;
      else t2Wins++;
    } else {
      if (m.awayGoals > m.homeGoals) t1Wins++;
      else t2Wins++;
    }
  }

  return {
    team1,
    team2,
    team1Wins: t1Wins,
    team2Wins: t2Wins,
    draws: drawCount,
    matches: headToHeadMatches,
  };
}

// ── Player queries ─────────────────────────────────────────────────

export function searchPlayers(
  players: Player[],
  opts: {
    name?: string;
    nationality?: string;
    club?: string;
    position?: string;
    minOverall?: number;
    limit?: number;
    sortBy?: string;
  }
): Player[] {
  let result = players;

  if (opts.name) {
    const q = opts.name.toLowerCase();
    result = result.filter((p) => p.name.toLowerCase().includes(q));
  }

  if (opts.nationality) {
    const q = opts.nationality.toLowerCase();
    result = result.filter((p) => p.nationality.toLowerCase().includes(q));
  }

  if (opts.club) {
    const q = opts.club.toLowerCase();
    result = result.filter((p) => p.club.toLowerCase().includes(q));
  }

  if (opts.position) {
    const q = opts.position.toLowerCase();
    result = result.filter((p) => p.position.toLowerCase().includes(q));
  }

  if (opts.minOverall) {
    result = result.filter((p) => p.overall >= opts.minOverall!);
  }

  // Sort
  const sortKey = (opts.sortBy || "overall") as keyof Player;
  result.sort((a, b) => {
    const av = a[sortKey];
    const bv = b[sortKey];
    if (typeof av === "number" && typeof bv === "number") return bv - av;
    return String(av).localeCompare(String(bv));
  });

  return opts.limit ? result.slice(0, opts.limit) : result;
}

// ── Competition standings ──────────────────────────────────────────

export function getStandings(
  matches: Match[],
  competition: string,
  season: number
): StandingEntry[] {
  const comp = competition.toLowerCase();
  const compMatches = matches.filter(
    (m) =>
      m.competition.toLowerCase().includes(comp) && m.season === season
  );

  // Accumulate per-team stats
  const teamStats = new Map<
    string,
    { wins: number; draws: number; losses: number; gf: number; ga: number }
  >();

  for (const m of compMatches) {
    for (const [team, isHome] of [
      [m.homeTeam, true],
      [m.awayTeam, false],
    ] as [string, boolean][]) {
      if (!teamStats.has(team)) {
        teamStats.set(team, { wins: 0, draws: 0, losses: 0, gf: 0, ga: 0 });
      }
      const s = teamStats.get(team)!;
      const scored = isHome ? m.homeGoals : m.awayGoals;
      const conceded = isHome ? m.awayGoals : m.homeGoals;
      s.gf += scored;
      s.ga += conceded;
      if (scored > conceded) s.wins++;
      else if (scored === conceded) s.draws++;
      else s.losses++;
    }
  }

  const entries: StandingEntry[] = [];
  for (const [team, s] of teamStats) {
    const played = s.wins + s.draws + s.losses;
    entries.push({
      position: 0,
      team,
      points: s.wins * 3 + s.draws,
      wins: s.wins,
      draws: s.draws,
      losses: s.losses,
      goalsFor: s.gf,
      goalsAgainst: s.ga,
      goalDifference: s.gf - s.ga,
      matches: played,
    });
  }

  // Sort by points, then GD, then GF
  entries.sort(
    (a, b) =>
      b.points - a.points ||
      b.goalDifference - a.goalDifference ||
      b.goalsFor - a.goalsFor
  );

  entries.forEach((e, i) => (e.position = i + 1));
  return entries;
}

// ── Statistical analysis ───────────────────────────────────────────

export interface MatchStats {
  totalMatches: number;
  totalGoals: number;
  avgGoalsPerMatch: number;
  homeWins: number;
  awayWins: number;
  draws: number;
  homeWinRate: number;
  awayWinRate: number;
  drawRate: number;
  biggestHomeWins: Match[];
  biggestAwayWins: Match[];
}

export function getMatchStats(
  matches: Match[],
  opts?: { competition?: string; season?: number }
): MatchStats {
  let filtered = matches;
  if (opts?.competition) {
    const comp = opts.competition.toLowerCase();
    filtered = filtered.filter((m) =>
      m.competition.toLowerCase().includes(comp)
    );
  }
  if (opts?.season) {
    filtered = filtered.filter((m) => m.season === opts.season);
  }

  let totalGoals = 0;
  let homeWins = 0;
  let awayWins = 0;
  let drawCount = 0;

  for (const m of filtered) {
    totalGoals += m.homeGoals + m.awayGoals;
    if (m.homeGoals > m.awayGoals) homeWins++;
    else if (m.awayGoals > m.homeGoals) awayWins++;
    else drawCount++;
  }

  const total = filtered.length;
  const biggestHomeWins = [...filtered]
    .filter((m) => m.homeGoals > m.awayGoals)
    .sort((a, b) => b.homeGoals - b.awayGoals - (a.homeGoals - a.awayGoals))
    .slice(0, 10);

  const biggestAwayWins = [...filtered]
    .filter((m) => m.awayGoals > m.homeGoals)
    .sort((a, b) => b.awayGoals - b.homeGoals - (a.awayGoals - a.homeGoals))
    .slice(0, 10);

  return {
    totalMatches: total,
    totalGoals,
    avgGoalsPerMatch: total > 0 ? Math.round((totalGoals / total) * 100) / 100 : 0,
    homeWins,
    awayWins,
    draws: drawCount,
    homeWinRate: total > 0 ? Math.round((homeWins / total) * 1000) / 10 : 0,
    awayWinRate: total > 0 ? Math.round((awayWins / total) * 1000) / 10 : 0,
    drawRate: total > 0 ? Math.round((drawCount / total) * 1000) / 10 : 0,
    biggestHomeWins,
    biggestAwayWins,
  };
}

/** Find the team with the best record in a given dimension */
export function getBestTeamRecord(
  matches: Match[],
  opts: {
    competition?: string;
    season?: number;
    homeOnly?: boolean;
    awayOnly?: boolean;
    sortBy?: "points" | "wins" | "goalsFor" | "goalDifference";
  }
): TeamRecord[] {
  const comp = opts.competition?.toLowerCase();
  let filtered = matches;
  if (comp) {
    filtered = filtered.filter((m) =>
      m.competition.toLowerCase().includes(comp!)
    );
  }
  if (opts.season) {
    filtered = filtered.filter((m) => m.season === opts.season);
  }

  // Collect unique team names
  const teams = new Set<string>();
  for (const m of filtered) {
    teams.add(m.homeTeam);
    teams.add(m.awayTeam);
  }

  const records: TeamRecord[] = [];
  for (const team of teams) {
    records.push(
      getTeamRecord(filtered, team, {
        season: opts.season,
        competition: opts.competition,
        homeOnly: opts.homeOnly,
        awayOnly: opts.awayOnly,
      })
    );
  }

  const sortKey = opts.sortBy || "points";
  records.sort((a, b) => {
    switch (sortKey) {
      case "points":
        return b.points - a.points;
      case "wins":
        return b.wins - a.wins;
      case "goalsFor":
        return b.goalsFor - a.goalsFor;
      case "goalDifference":
        return b.goalsFor - b.goalsAgainst - (a.goalsFor - a.goalsAgainst);
      default:
        return b.points - a.points;
    }
  });

  return records;
}
