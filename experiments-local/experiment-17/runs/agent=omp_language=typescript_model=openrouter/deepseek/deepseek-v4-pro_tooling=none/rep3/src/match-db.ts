/**
 * Brazilian Soccer MCP Server - Match Database
 *
 * Unified interface for querying all match datasets.
 * Loads all CSV data, normalizes team names, and provides
 * rich query and aggregation capabilities.
 */

import {
  loadBrasileiraoMatches,
  loadBrazilianCupMatches,
  loadLibertadoresMatches,
  loadBRFootballMatches,
  loadNovoBrasileiraoMatches,
  type UnifiedMatch,
} from "./data-loader.js";
import { normalizeTeam, teamMatches } from "./team-normalizer.js";

// --- Cache ---

let _unified: UnifiedMatch[] | null = null;

export function getAllMatches(): UnifiedMatch[] {
  if (_unified) return _unified;

  const matches: UnifiedMatch[] = [];

  // Brasileirão
  for (const m of loadBrasileiraoMatches()) {
    matches.push({
      date: extractDate(m.datetime),
      home_team: normalizeTeam(m.home_team),
      away_team: normalizeTeam(m.away_team),
      home_goal: m.home_goal,
      away_goal: m.away_goal,
      season: m.season,
      competition: m.competition,
      round: m.round,
      home_team_state: m.home_team_state,
      away_team_state: m.away_team_state,
    });
  }

  // Copa do Brasil
  for (const m of loadBrazilianCupMatches()) {
    matches.push({
      date: extractDate(m.datetime),
      home_team: normalizeTeam(m.home_team),
      away_team: normalizeTeam(m.away_team),
      home_goal: m.home_goal,
      away_goal: m.away_goal,
      season: m.season,
      competition: m.competition,
      round: m.round,
    });
  }

  // Libertadores
  for (const m of loadLibertadoresMatches()) {
    matches.push({
      date: extractDate(m.datetime),
      home_team: normalizeTeam(m.home_team),
      away_team: normalizeTeam(m.away_team),
      home_goal: m.home_goal,
      away_goal: m.away_goal,
      season: m.season,
      competition: m.competition,
      stage: m.stage,
    });
  }

  // BR-Football dataset (extended stats)
  for (const m of loadBRFootballMatches()) {
    matches.push({
      date: m.date,
      home_team: normalizeTeam(m.home),
      away_team: normalizeTeam(m.away),
      home_goal: m.home_goal,
      away_goal: m.away_goal,
      season: extractYear(m.date),
      competition: normalizeCompetition(m.tournament),
    });
  }

  // Novo Brasileirão (historical 2003-2019)
  for (const m of loadNovoBrasileiraoMatches()) {
    if (m.gols_mandante === undefined || m.gols_visitante === undefined) continue;
    matches.push({
      date: parseBrazilianDate(m.data),
      home_team: normalizeTeam(m.equipe_mandante),
      away_team: normalizeTeam(m.equipe_visitante),
      home_goal: m.gols_mandante,
      away_goal: m.gols_visitante,
      season: m.ano,
      competition: m.competition,
      round: m.rodada,
      home_team_state: m.mandante_uf,
      away_team_state: m.visitante_uf,
    });
  }

  _unified = matches;
  return matches;
}

// --- Date Helpers ---

function extractDate(datetime: string): string {
  if (!datetime) return "";
  // "2012-05-19 18:30:00" -> "2012-05-19"
  const space = datetime.indexOf(" ");
  return space > 0 ? datetime.substring(0, space) : datetime;
}

function extractYear(dateStr: string): number {
  if (!dateStr) return 0;
  const y = parseInt(dateStr.substring(0, 4), 10);
  return isNaN(y) ? 0 : y;
}

function parseBrazilianDate(dateStr: string): string {
  if (!dateStr) return "";
  // "29/03/2003" -> "2003-03-29"
  const parts = dateStr.split("/");
  if (parts.length === 3) {
    return `${parts[2]}-${parts[1].padStart(2, "0")}-${parts[0].padStart(2, "0")}`;
  }
  return dateStr;
}

function normalizeCompetition(tournament: string): string {
  const t = tournament.toLowerCase();
  if (t.includes("copa do brasil")) return "Copa do Brasil";
  if (t.includes("brasileir") || t.includes("serie a")) return "Brasileirão";
  if (t.includes("libertadores")) return "Libertadores";
  return tournament;
}

// --- Query Functions ---

export interface TeamStats {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDiff: number;
  winRate: number;
  competitions: string[];
  seasons: number[];
}

export interface HeadToHead {
  team1: string;
  team2: string;
  team1Wins: number;
  team2Wins: number;
  draws: number;
  totalMatches: number;
  matches: UnifiedMatch[];
}

export interface StandingEntry {
  position: number;
  team: string;
  points: number;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDiff: number;
}

// --- Match Queries ---

/**
 * Search matches with multiple filter criteria.
 * All filters are optional and combined with AND.
 */
export function searchMatches(filters: {
  team?: string;
  homeTeam?: string;
  awayTeam?: string;
  season?: number;
  competition?: string;
  dateFrom?: string;
  dateTo?: string;
  round?: string;
  limit?: number;
}): UnifiedMatch[] {
  let results = getAllMatches();

  if (filters.team) {
    const q = filters.team;
    results = results.filter(
      (m) => teamMatches(m.home_team, q) || teamMatches(m.away_team, q),
    );
  }

  if (filters.homeTeam) {
    const q = filters.homeTeam;
    results = results.filter((m) => teamMatches(m.home_team, q));
  }

  if (filters.awayTeam) {
    const q = filters.awayTeam;
    results = results.filter((m) => teamMatches(m.away_team, q));
  }

  if (filters.season !== undefined) {
    results = results.filter((m) => m.season === filters.season);
  }

  if (filters.competition) {
    const c = filters.competition.toLowerCase();
    results = results.filter((m) => m.competition.toLowerCase().includes(c));
  }

  if (filters.dateFrom) {
    results = results.filter((m) => m.date >= filters.dateFrom!);
  }

  if (filters.dateTo) {
    results = results.filter((m) => m.date <= filters.dateTo!);
  }

  if (filters.round) {
    const r = filters.round.toLowerCase();
    results = results.filter((m) => {
      const mr = String(m.round || "").toLowerCase();
      const ms = String(m.stage || "").toLowerCase();
      return mr.includes(r) || ms.includes(r);
    });
  }

  // Sort by date descending
  results.sort((a, b) => b.date.localeCompare(a.date));

  if (filters.limit && filters.limit > 0) {
    results = results.slice(0, filters.limit);
  }

  return results;
}

/**
 * Get team statistics across all competitions, optionally filtered by season/competition.
 */
export function getTeamStats(team: string, season?: number, competition?: string): TeamStats {
  let matches = searchMatches({ team });
  if (season !== undefined) matches = matches.filter((m) => m.season === season);
  if (competition) {
    const c = competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(c));
  }

  return computeTeamStats(team, matches);
}

/**
 * Get head-to-head record between two teams.
 */
export function getHeadToHead(team1: string, team2: string): HeadToHead {
  const matches = getAllMatches().filter(
    (m) =>
      (teamMatches(m.home_team, team1) && teamMatches(m.away_team, team2)) ||
      (teamMatches(m.home_team, team2) && teamMatches(m.away_team, team1)),
  );

  let team1Wins = 0;
  let team2Wins = 0;
  let draws = 0;

  for (const m of matches) {
    if (m.home_goal === m.away_goal) {
      draws++;
    } else if (teamMatches(m.home_team, team1)) {
      m.home_goal > m.away_goal ? team1Wins++ : team2Wins++;
    } else {
      m.home_goal > m.away_goal ? team2Wins++ : team1Wins++;
    }
  }

  // Sort by date descending
  matches.sort((a, b) => b.date.localeCompare(a.date));

  return {
    team1: normalizeTeam(team1),
    team2: normalizeTeam(team2),
    team1Wins,
    team2Wins,
    draws,
    totalMatches: matches.length,
    matches,
  };
}

/**
 * Compute league standings from match results.
 */
export function getStandings(season: number, competition?: string): StandingEntry[] {
  const matches = getAllMatches().filter((m) => {
    if (m.season !== season) return false;
    if (competition) {
      return m.competition.toLowerCase().includes(competition.toLowerCase());
    }
    // Default to Brasileirão
    return m.competition.toLowerCase().includes("brasileirão");
  });

  const teamMap = new Map<string, {
    played: number; wins: number; draws: number; losses: number;
    goalsFor: number; goalsAgainst: number;
  }>();

  for (const m of matches) {
    const home = m.home_team;
    const away = m.away_team;

    if (!teamMap.has(home)) {
      teamMap.set(home, { played: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0 });
    }
    if (!teamMap.has(away)) {
      teamMap.set(away, { played: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0 });
    }

    const hs = teamMap.get(home)!;
    const as = teamMap.get(away)!;

    hs.played++;
    hs.goalsFor += m.home_goal;
    hs.goalsAgainst += m.away_goal;

    as.played++;
    as.goalsFor += m.away_goal;
    as.goalsAgainst += m.home_goal;

    if (m.home_goal > m.away_goal) {
      hs.wins++;
      as.losses++;
    } else if (m.home_goal < m.away_goal) {
      hs.losses++;
      as.wins++;
    } else {
      hs.draws++;
      as.draws++;
    }
  }

  const standings: StandingEntry[] = [];
  for (const [team, stats] of teamMap) {
    standings.push({
      position: 0,
      team,
      points: stats.wins * 3 + stats.draws,
      played: stats.played,
      wins: stats.wins,
      draws: stats.draws,
      losses: stats.losses,
      goalsFor: stats.goalsFor,
      goalsAgainst: stats.goalsAgainst,
      goalDiff: stats.goalsFor - stats.goalsAgainst,
    });
  }

  // Sort: points desc, then wins desc, then goal diff desc, then goals for desc
  standings.sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    if (b.wins !== a.wins) return b.wins - a.wins;
    if (b.goalDiff !== a.goalDiff) return b.goalDiff - a.goalDiff;
    return b.goalsFor - a.goalsFor;
  });

  // Assign positions
  for (let i = 0; i < standings.length; i++) {
    standings[i].position = i + 1;
  }

  return standings;
}

/**
 * Get the biggest wins in the dataset.
 */
export function getBiggestWins(limit: number = 10): UnifiedMatch[] {
  return getAllMatches()
    .filter((m) => {
      const diff = m.home_goal - m.away_goal;
      return diff >= 5 || diff <= -5;
    })
    .sort((a, b) => {
      const diffA = Math.abs(a.home_goal - a.away_goal);
      const diffB = Math.abs(b.home_goal - b.away_goal);
      return diffB - diffA;
    })
    .slice(0, limit);
}

/**
 * Get goal averages.
 */
export function getGoalAverages(competition?: string): {
  avgGoalsPerMatch: number;
  homeWinRate: number;
  drawRate: number;
  awayWinRate: number;
  totalMatches: number;
} {
  let matches = getAllMatches();
  if (competition) {
    const c = competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(c));
  }

  const total = matches.length;
  if (total === 0) return { avgGoalsPerMatch: 0, homeWinRate: 0, drawRate: 0, awayWinRate: 0, totalMatches: 0 };

  let totalGoals = 0;
  let homeWins = 0;
  let draws = 0;

  for (const m of matches) {
    totalGoals += m.home_goal + m.away_goal;
    if (m.home_goal > m.away_goal) homeWins++;
    else if (m.home_goal === m.away_goal) draws++;
  }

  return {
    avgGoalsPerMatch: totalGoals / total,
    homeWinRate: homeWins / total,
    drawRate: draws / total,
    awayWinRate: (total - homeWins - draws) / total,
    totalMatches: total,
  };
}

/**
 * Get home/away stats for a team.
 */
export function getHomeAwayStats(team: string, season?: number, competition?: string): {
  home: TeamStats;
  away: TeamStats;
  overall: TeamStats;
} {
  let matches = getAllMatches();

  // Filter to matches involving this team
  matches = matches.filter(
    (m) => teamMatches(m.home_team, team) || teamMatches(m.away_team, team),
  );

  if (season !== undefined) matches = matches.filter((m) => m.season === season);
  if (competition) {
    const c = competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(c));
  }

  const homeMatches = matches.filter((m) => teamMatches(m.home_team, team));
  const awayMatches = matches.filter((m) => teamMatches(m.away_team, team));

  return {
    home: computeTeamStats(team, homeMatches, true),
    away: computeTeamStats(team, awayMatches, false),
    overall: computeTeamStats(team, matches),
  };
}

// --- Internal helpers ---

function computeTeamStats(team: string, matches: UnifiedMatch[], isHome?: boolean): TeamStats {
  let wins = 0, draws = 0, losses = 0, goalsFor = 0, goalsAgainst = 0;
  const competitions = new Set<string>();
  const seasons = new Set<number>();

  for (const m of matches) {
    competitions.add(m.competition);
    seasons.add(m.season);

    if (isHome === undefined || isHome === true) {
      if (teamMatches(m.home_team, team)) {
        goalsFor += m.home_goal;
        goalsAgainst += m.away_goal;
        if (m.home_goal > m.away_goal) wins++;
        else if (m.home_goal === m.away_goal) draws++;
        else losses++;
      }
    }
    if (isHome === undefined || isHome === false) {
      if (teamMatches(m.away_team, team)) {
        if (isHome === undefined) {
          goalsFor += m.away_goal;
          goalsAgainst += m.home_goal;
          if (m.away_goal > m.home_goal) wins++;
          else if (m.away_goal === m.home_goal) draws++;
          else losses++;
        } else {
          goalsFor += m.away_goal;
          goalsAgainst += m.home_goal;
          if (m.away_goal > m.home_goal) wins++;
          else if (m.away_goal === m.home_goal) draws++;
          else losses++;
        }
      }
    }
  }

  const total = matches.length;
  return {
    team: normalizeTeam(team),
    matches: total,
    wins,
    draws,
    losses,
    goalsFor,
    goalsAgainst,
    goalDiff: goalsFor - goalsAgainst,
    winRate: total > 0 ? wins / total : 0,
    competitions: Array.from(competitions).sort(),
    seasons: Array.from(seasons).sort((a, b) => a - b),
  };
}