import type {
  Competition,
  HeadToHeadRecord,
  NormalizedMatch,
  PlayerRecord,
  StandingResult,
  StandingRow,
  TeamStats,
} from "./types.js";
import { teamMatches } from "./normalize.js";

export interface MatchFilter {
  team?: string;
  opponent?: string;
  homeTeam?: string;
  awayTeam?: string;
  competition?: Competition | "All";
  season?: number | "All";
  fromDate?: string;
  toDate?: string;
  round?: string;
  stage?: string;
  limit?: number;
}

const asDate = (s: string | undefined): Date | null => {
  if (!s) return null;
  const d = new Date(s);
  return isNaN(d.getTime()) ? null : d;
};

export const filterMatches = (
  matches: NormalizedMatch[],
  f: MatchFilter
): NormalizedMatch[] => {
  const from = asDate(f.fromDate);
  const to = asDate(f.toDate);
  let out = matches.filter((m) => {
    if (f.competition && f.competition !== "All" && m.competition !== f.competition) return false;
    if (f.season && f.season !== "All" && m.season !== f.season) return false;
    if (from && m.dateObj && m.dateObj < from) return false;
    if (to && m.dateObj && m.dateObj > to) return false;
    if (f.round && m.round && String(m.round).toLowerCase() !== String(f.round).toLowerCase()) return false;
    if (f.stage && m.stage && !m.stage.toLowerCase().includes(f.stage.toLowerCase())) return false;
    if (f.homeTeam && !teamMatches(m.homeTeam, f.homeTeam)) return false;
    if (f.awayTeam && !teamMatches(m.awayTeam, f.awayTeam)) return false;
    if (f.team) {
      const teamIsHome = teamMatches(m.homeTeam, f.team);
      const teamIsAway = teamMatches(m.awayTeam, f.team);
      if (!teamIsHome && !teamIsAway) return false;
      if (f.opponent) {
        const oppIsHome = teamMatches(m.homeTeam, f.opponent);
        const oppIsAway = teamMatches(m.awayTeam, f.opponent);
        const teamOpp = (teamIsHome && oppIsAway) || (teamIsAway && oppIsHome);
        if (!teamOpp) return false;
      }
    } else if (f.opponent) {
      if (!teamMatches(m.homeTeam, f.opponent) && !teamMatches(m.awayTeam, f.opponent)) return false;
    }
    return true;
  });
  out = out.sort((a, b) => {
    const da = a.dateObj ? a.dateObj.getTime() : 0;
    const db = b.dateObj ? b.dateObj.getTime() : 0;
    return da - db;
  });
  if (f.limit && f.limit > 0) out = out.slice(0, f.limit);
  return out;
};

export const computeTeamStats = (
  matches: NormalizedMatch[],
  team: string,
  opts: {
    competition?: Competition | "All";
    season?: number | "All";
    venue?: "home" | "away" | "all";
  } = {}
): TeamStats => {
  const { competition = "All", season = "All", venue = "all" } = opts;
  let played = 0,
    wins = 0,
    draws = 0,
    losses = 0,
    gf = 0,
    ga = 0;
  for (const m of matches) {
    if (competition !== "All" && m.competition !== competition) continue;
    if (season !== "All" && m.season !== season) continue;
    const isHome = teamMatches(m.homeTeam, team);
    const isAway = teamMatches(m.awayTeam, team);
    if (!isHome && !isAway) continue;
    if (venue === "home" && !isHome) continue;
    if (venue === "away" && !isAway) continue;
    if (m.homeGoals == null || m.awayGoals == null) continue;
    played++;
    const myGoals = isHome ? m.homeGoals : m.awayGoals;
    const oppGoals = isHome ? m.awayGoals : m.homeGoals;
    gf += myGoals;
    ga += oppGoals;
    if (myGoals > oppGoals) wins++;
    else if (myGoals < oppGoals) losses++;
    else draws++;
  }
  return {
    team,
    competition,
    season,
    venue,
    matches: played,
    wins,
    draws,
    losses,
    goalsFor: gf,
    goalsAgainst: ga,
    winRate: played === 0 ? 0 : Number(((wins / played) * 100).toFixed(1)),
  };
};

export const headToHead = (
  matches: NormalizedMatch[],
  teamA: string,
  teamB: string,
  opts: { competition?: Competition | "All"; season?: number | "All" } = {}
): HeadToHeadRecord => {
  const filtered = filterMatches(matches, {
    team: teamA,
    opponent: teamB,
    competition: opts.competition,
    season: opts.season,
  });
  let aWins = 0,
    bWins = 0,
    draws = 0,
    aGoals = 0,
    bGoals = 0;
  for (const m of filtered) {
    if (m.homeGoals == null || m.awayGoals == null) continue;
    const aIsHome = teamMatches(m.homeTeam, teamA);
    const aGoalsMatch = aIsHome ? m.homeGoals : m.awayGoals;
    const bGoalsMatch = aIsHome ? m.awayGoals : m.homeGoals;
    aGoals += aGoalsMatch;
    bGoals += bGoalsMatch;
    if (aGoalsMatch > bGoalsMatch) aWins++;
    else if (aGoalsMatch < bGoalsMatch) bWins++;
    else draws++;
  }
  return {
    teamA,
    teamB,
    matches: filtered.length,
    teamAWins: aWins,
    teamBWins: bWins,
    draws,
    teamAGoals: aGoals,
    teamBGoals: bGoals,
    matchesList: filtered,
  };
};

export const calculateStandings = (
  matches: NormalizedMatch[],
  competition: Competition,
  season: number
): StandingResult => {
  const byTeam = new Map<string, StandingRow>();
  const relevant = matches.filter(
    (m) =>
      m.competition === competition &&
      m.season === season &&
      m.homeGoals != null &&
      m.awayGoals != null
  );
  const ensure = (team: string): StandingRow => {
    let row = byTeam.get(team);
    if (!row) {
      row = {
        team,
        played: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        goalsFor: 0,
        goalsAgainst: 0,
        goalDifference: 0,
        points: 0,
      };
      byTeam.set(team, row);
    }
    return row;
  };
  for (const m of relevant) {
    const home = ensure(m.homeTeam);
    const away = ensure(m.awayTeam);
    home.played++;
    away.played++;
    home.goalsFor += m.homeGoals!;
    home.goalsAgainst += m.awayGoals!;
    away.goalsFor += m.awayGoals!;
    away.goalsAgainst += m.homeGoals!;
    if (m.homeGoals! > m.awayGoals!) {
      home.wins++;
      away.losses++;
      home.points += 3;
    } else if (m.homeGoals! < m.awayGoals!) {
      away.wins++;
      home.losses++;
      away.points += 3;
    } else {
      home.draws++;
      away.draws++;
      home.points += 1;
      away.points += 1;
    }
  }
  const rows = Array.from(byTeam.values()).map((r) => ({
    ...r,
    goalDifference: r.goalsFor - r.goalsAgainst,
  }));
  rows.sort(
    (a, b) =>
      b.points - a.points ||
      b.wins - a.wins ||
      b.goalDifference - a.goalDifference ||
      b.goalsFor - a.goalsFor ||
      a.team.localeCompare(b.team)
  );
  return { competition, season, rows };
};

export const biggestWins = (
  matches: NormalizedMatch[],
  opts: { competition?: Competition | "All"; season?: number | "All"; limit?: number } = {}
): NormalizedMatch[] => {
  const { competition = "All", season = "All", limit = 10 } = opts;
  const scored = matches
    .filter(
      (m) =>
        m.homeGoals != null &&
        m.awayGoals != null &&
        (competition === "All" || m.competition === competition) &&
        (season === "All" || m.season === season)
    )
    .map((m) => ({ m, diff: Math.abs(m.homeGoals! - m.awayGoals!) }))
    .sort((a, b) => b.diff - a.diff || b.m.homeGoals! - a.m.homeGoals!);
  return scored.slice(0, limit).map((x) => x.m);
};

export const averageGoals = (
  matches: NormalizedMatch[],
  opts: { competition?: Competition | "All"; season?: number | "All" } = {}
): {
  average: number;
  totalMatches: number;
  totalGoals: number;
  homeWinRate: number;
  drawRate: number;
  awayWinRate: number;
} => {
  const { competition = "All", season = "All" } = opts;
  let total = 0,
    goals = 0,
    homeWins = 0,
    draws = 0,
    awayWins = 0;
  for (const m of matches) {
    if (competition !== "All" && m.competition !== competition) continue;
    if (season !== "All" && m.season !== season) continue;
    if (m.homeGoals == null || m.awayGoals == null) continue;
    total++;
    goals += m.homeGoals + m.awayGoals;
    if (m.homeGoals > m.awayGoals) homeWins++;
    else if (m.homeGoals < m.awayGoals) awayWins++;
    else draws++;
  }
  return {
    average: total === 0 ? 0 : Number((goals / total).toFixed(2)),
    totalMatches: total,
    totalGoals: goals,
    homeWinRate: total === 0 ? 0 : Number(((homeWins / total) * 100).toFixed(1)),
    drawRate: total === 0 ? 0 : Number(((draws / total) * 100).toFixed(1)),
    awayWinRate: total === 0 ? 0 : Number(((awayWins / total) * 100).toFixed(1)),
  };
};

export const filterPlayers = (
  players: PlayerRecord[],
  opts: {
    name?: string;
    nationality?: string;
    club?: string;
    position?: string;
    minOverall?: number;
    limit?: number;
    sortBy?: "overall" | "potential" | "age" | "name";
    desc?: boolean;
  } = {}
): PlayerRecord[] => {
  let out = players.filter((p) => {
    if (opts.name) {
      const q = opts.name.toLowerCase();
      if (!p.name.toLowerCase().includes(q)) return false;
    }
    if (opts.nationality) {
      if (!p.nationality.toLowerCase().includes(opts.nationality.toLowerCase())) return false;
    }
    if (opts.club) {
      if (!teamMatches(p.club, opts.club)) return false;
    }
    if (opts.position) {
      if (!p.position.toLowerCase().includes(opts.position.toLowerCase())) return false;
    }
    if (opts.minOverall != null && (p.overall ?? 0) < opts.minOverall) return false;
    return true;
  });
  const sortBy = opts.sortBy ?? "overall";
  const desc = opts.desc ?? true;
  out = out.slice().sort((a, b) => {
    let av: number | string;
    let bv: number | string;
    if (sortBy === "name") {
      av = a.name.toLowerCase();
      bv = b.name.toLowerCase();
    } else {
      av = (a[sortBy as "overall" | "potential" | "age"] as number) ?? 0;
      bv = (b[sortBy as "overall" | "potential" | "age"] as number) ?? 0;
    }
    if (av < bv) return desc ? 1 : -1;
    if (av > bv) return desc ? -1 : 1;
    return 0;
  });
  if (opts.limit && opts.limit > 0) out = out.slice(0, opts.limit);
  return out;
};

export const listCompetitions = (matches: NormalizedMatch[]): { competition: Competition; label: string; seasons: number[]; matchCount: number }[] => {
  const map = new Map<Competition, { label: string; seasons: Set<number>; count: number }>();
  for (const m of matches) {
    let e = map.get(m.competition);
    if (!e) {
      e = { label: m.competitionLabel, seasons: new Set(), count: 0 };
      map.set(m.competition, e);
    }
    e.label = m.competitionLabel;
    e.seasons.add(m.season);
    e.count++;
  }
  return Array.from(map.entries()).map(([competition, v]) => ({
    competition,
    label: v.label,
    seasons: Array.from(v.seasons).sort((a, b) => a - b),
    matchCount: v.count,
  }));
};

export const listTeams = (matches: NormalizedMatch[]): string[] => {
  const set = new Set<string>();
  for (const m of matches) {
    if (m.homeTeam) set.add(m.homeTeam);
    if (m.awayTeam) set.add(m.awayTeam);
  }
  return Array.from(set).sort((a, b) => a.localeCompare(b));
};

export const lastMatchBetween = (
  matches: NormalizedMatch[],
  teamA: string,
  teamB: string
): NormalizedMatch | null => {
  const list = filterMatches(matches, { team: teamA, opponent: teamB });
  if (list.length === 0) return null;
  return list[list.length - 1];
};
