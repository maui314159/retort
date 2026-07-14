import type { Match, Player, TeamRecord, HeadToHead } from "./types.js";
import { getAllMatches, getAllPlayers } from "./loader.js";

// ─── helpers ────────────────────────────────────────────────────────────────

/** Case-insensitive substring match on team names (handles partial names) */
function teamMatches(teamName: string, query: string): boolean {
  return teamName.toLowerCase().includes(query.toLowerCase());
}

function buildRecord(team: string, matches: Match[]): TeamRecord {
  let wins = 0, draws = 0, losses = 0, goalsFor = 0, goalsAgainst = 0;
  for (const m of matches) {
    const isHome = teamMatches(m.homeTeam, team);
    const gf = isHome ? m.homeGoals : m.awayGoals;
    const ga = isHome ? m.awayGoals : m.homeGoals;
    goalsFor += gf;
    goalsAgainst += ga;
    if (gf > ga) wins++;
    else if (gf === ga) draws++;
    else losses++;
  }
  return {
    team,
    matches: matches.length,
    wins,
    draws,
    losses,
    goalsFor,
    goalsAgainst,
    points: wins * 3 + draws,
  };
}

// ─── Match queries ───────────────────────────────────────────────────────────

export interface FindMatchesParams {
  team?: string;
  team1?: string;
  team2?: string;
  competition?: string;
  season?: number;
  dateFrom?: string;
  dateTo?: string;
  limit?: number;
}

export function findMatches(params: FindMatchesParams): Match[] {
  const { team, team1, team2, competition, season, dateFrom, dateTo } = params;
  const limit = params.limit ?? 100;

  let matches = getAllMatches();

  if (team) {
    matches = matches.filter(
      (m) => teamMatches(m.homeTeam, team) || teamMatches(m.awayTeam, team)
    );
  }
  if (team1 && team2) {
    matches = matches.filter(
      (m) =>
        (teamMatches(m.homeTeam, team1) && teamMatches(m.awayTeam, team2)) ||
        (teamMatches(m.homeTeam, team2) && teamMatches(m.awayTeam, team1))
    );
  } else if (team1) {
    matches = matches.filter(
      (m) => teamMatches(m.homeTeam, team1) || teamMatches(m.awayTeam, team1)
    );
  }
  if (competition) {
    const comp = competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(comp));
  }
  if (season) {
    matches = matches.filter((m) => m.season === season);
  }
  if (dateFrom) {
    matches = matches.filter((m) => m.date >= dateFrom);
  }
  if (dateTo) {
    matches = matches.filter((m) => m.date <= dateTo);
  }

  // Sort by date descending
  matches.sort((a, b) => (b.date > a.date ? 1 : b.date < a.date ? -1 : 0));

  return matches.slice(0, limit);
}

// ─── Head-to-head ────────────────────────────────────────────────────────────

export function getHeadToHead(team1: string, team2: string): HeadToHead {
  const matches = getAllMatches().filter(
    (m) =>
      (teamMatches(m.homeTeam, team1) && teamMatches(m.awayTeam, team2)) ||
      (teamMatches(m.homeTeam, team2) && teamMatches(m.awayTeam, team1))
  );
  matches.sort((a, b) => (b.date > a.date ? 1 : b.date < a.date ? -1 : 0));

  let t1Wins = 0, t2Wins = 0, draws = 0, t1Goals = 0, t2Goals = 0;
  for (const m of matches) {
    const t1IsHome = teamMatches(m.homeTeam, team1);
    const t1g = t1IsHome ? m.homeGoals : m.awayGoals;
    const t2g = t1IsHome ? m.awayGoals : m.homeGoals;
    t1Goals += t1g;
    t2Goals += t2g;
    if (t1g > t2g) t1Wins++;
    else if (t1g < t2g) t2Wins++;
    else draws++;
  }

  return {
    team1,
    team2,
    matches,
    team1Wins: t1Wins,
    team2Wins: t2Wins,
    draws,
    team1Goals: t1Goals,
    team2Goals: t2Goals,
  };
}

// ─── Team stats ──────────────────────────────────────────────────────────────

export interface TeamStatsParams {
  team: string;
  competition?: string;
  season?: number;
  homeOnly?: boolean;
  awayOnly?: boolean;
}

export function getTeamStats(params: TeamStatsParams): TeamRecord {
  const { team, competition, season, homeOnly, awayOnly } = params;
  let matches = getAllMatches().filter(
    (m) => teamMatches(m.homeTeam, team) || teamMatches(m.awayTeam, team)
  );

  if (competition) {
    const comp = competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(comp));
  }
  if (season) {
    matches = matches.filter((m) => m.season === season);
  }
  if (homeOnly) {
    matches = matches.filter((m) => teamMatches(m.homeTeam, team));
  }
  if (awayOnly) {
    matches = matches.filter((m) => teamMatches(m.awayTeam, team));
  }

  return buildRecord(team, matches);
}

// ─── Standings ───────────────────────────────────────────────────────────────

export function getStandings(
  competition: string,
  season: number
): TeamRecord[] {
  let matches = getAllMatches().filter((m) => m.season === season);
  if (competition !== "all") {
    const comp = competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(comp));
  }

  // Collect all teams in this competition/season
  const teamSet = new Set<string>();
  for (const m of matches) {
    teamSet.add(m.homeTeam);
    teamSet.add(m.awayTeam);
  }

  const records: TeamRecord[] = [];
  for (const team of teamSet) {
    const teamMatches2 = matches.filter(
      (m) => m.homeTeam === team || m.awayTeam === team
    );
    records.push(buildRecord(team, teamMatches2));
  }

  // Sort by points desc, then goal difference
  records.sort((a, b) => {
    const ptsDiff = b.points - a.points;
    if (ptsDiff !== 0) return ptsDiff;
    const gdA = a.goalsFor - a.goalsAgainst;
    const gdB = b.goalsFor - b.goalsAgainst;
    return gdB - gdA;
  });

  return records;
}

// ─── Player queries ──────────────────────────────────────────────────────────

export interface FindPlayersParams {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  maxAge?: number;
  limit?: number;
}

export function findPlayers(params: FindPlayersParams): Player[] {
  const { name, nationality, club, position, minOverall, maxAge } = params;
  const limit = params.limit ?? 50;

  let players = getAllPlayers();

  if (name) {
    players = players.filter((p) =>
      p.name.toLowerCase().includes(name.toLowerCase())
    );
  }
  if (nationality) {
    players = players.filter((p) =>
      p.nationality.toLowerCase().includes(nationality.toLowerCase())
    );
  }
  if (club) {
    players = players.filter((p) =>
      p.club.toLowerCase().includes(club.toLowerCase())
    );
  }
  if (position) {
    players = players.filter((p) =>
      p.position.toLowerCase().includes(position.toLowerCase())
    );
  }
  if (minOverall !== undefined) {
    players = players.filter((p) => p.overall >= minOverall);
  }
  if (maxAge !== undefined) {
    players = players.filter((p) => p.age <= maxAge);
  }

  // Sort by overall descending
  players.sort((a, b) => b.overall - a.overall);

  return players.slice(0, limit);
}

// ─── Statistical analysis ────────────────────────────────────────────────────

export interface CompetitionStats {
  competition: string;
  totalMatches: number;
  totalGoals: number;
  avgGoalsPerMatch: number;
  homeWins: number;
  awayWins: number;
  draws: number;
  homeWinRate: number;
  biggestWin?: { match: Match; goalDiff: number };
}

export function getCompetitionStats(
  competition?: string,
  season?: number
): CompetitionStats {
  let matches = getAllMatches();

  if (competition) {
    const comp = competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(comp));
  }
  if (season) {
    matches = matches.filter((m) => m.season === season);
  }

  const totalGoals = matches.reduce(
    (s, m) => s + m.homeGoals + m.awayGoals,
    0
  );
  let homeWins = 0, awayWins = 0, draws2 = 0;
  let biggestDiff = 0;
  let biggestWinMatch: Match | undefined;

  for (const m of matches) {
    const diff = m.homeGoals - m.awayGoals;
    if (diff > 0) homeWins++;
    else if (diff < 0) awayWins++;
    else draws2++;

    const absDiff = Math.abs(diff);
    if (absDiff > biggestDiff) {
      biggestDiff = absDiff;
      biggestWinMatch = m;
    }
  }

  return {
    competition: competition ?? "all",
    totalMatches: matches.length,
    totalGoals,
    avgGoalsPerMatch: matches.length > 0 ? totalGoals / matches.length : 0,
    homeWins,
    awayWins,
    draws: draws2,
    homeWinRate: matches.length > 0 ? homeWins / matches.length : 0,
    biggestWin: biggestWinMatch
      ? { match: biggestWinMatch, goalDiff: biggestDiff }
      : undefined,
  };
}

export interface BestHomeAwayRecord {
  team: string;
  record: TeamRecord;
}

export function getBestHomeRecord(
  competition?: string,
  season?: number,
  topN = 10
): BestHomeAwayRecord[] {
  let matches = getAllMatches();
  if (competition) {
    const comp = competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(comp));
  }
  if (season) {
    matches = matches.filter((m) => m.season === season);
  }

  const homeTeams = new Set(matches.map((m) => m.homeTeam));
  const records: BestHomeAwayRecord[] = [];

  for (const team of homeTeams) {
    const homeMatches = matches.filter((m) => m.homeTeam === team);
    if (homeMatches.length < 5) continue; // need enough matches for meaningful stat
    const rec = buildRecord(team, homeMatches);
    records.push({ team, record: rec });
  }

  records.sort((a, b) => {
    const wrA = a.record.wins / a.record.matches;
    const wrB = b.record.wins / b.record.matches;
    return wrB - wrA;
  });

  return records.slice(0, topN);
}

export function getBiggestWins(limit = 10): Array<{ match: Match; goalDiff: number }> {
  const matches = getAllMatches();
  const wins = matches
    .map((m) => ({ match: m, goalDiff: Math.abs(m.homeGoals - m.awayGoals) }))
    .filter((x) => x.goalDiff > 0);
  wins.sort((a, b) => b.goalDiff - a.goalDiff);
  return wins.slice(0, limit);
}

export function getTeamCompetitions(team: string): string[] {
  const matches = getAllMatches().filter(
    (m) => teamMatches(m.homeTeam, team) || teamMatches(m.awayTeam, team)
  );

  const competitions = new Set<string>();
  for (const m of matches) {
    let label: string = m.competition;
    if (m.competition === "Extended" && m.round) label = m.round;
    competitions.add(label);
  }
  return [...competitions].sort();
}
