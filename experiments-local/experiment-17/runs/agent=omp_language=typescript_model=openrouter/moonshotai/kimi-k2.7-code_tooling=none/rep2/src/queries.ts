/**
 * Brazilian Soccer MCP Server
 * Query and analysis functions operating over the loaded repository.
 */

import {
  canonicalizeTeamName,
  Match,
  matchesTeam,
  Player,
  SoccerRepository,
} from './data.js';
export interface MatchFilter {
  team?: string;
  homeTeam?: string;
  awayTeam?: string;
  teamA?: string;
  teamB?: string;
  competition?: string;
  season?: number;
  fromDate?: string;
  toDate?: string;
  round?: string;
  limit?: number;
}

export interface TeamStats {
  team: string;
  competition: string | null;
  season: number | null;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  winRate: number;
}

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

function normalizeCompetitionAlias(input?: string): string | undefined {
  if (!input) return input;
  const lower = input.toLowerCase();
  if (lower.includes('brasileir') || lower.includes('serie a')) return 'brasileirão';
  if (lower.includes('copa do brasil') || lower.includes('brazilian cup')) return 'copadobrasil';
  if (lower.includes('libertadores')) return 'copalibertadores';
  return lower;
}

function dateFilter(m: Match, fromDate?: string, toDate?: string): boolean {
  if (!m.datetime && (fromDate || toDate)) return false;
  const ts = m.datetime?.getTime();
  if (fromDate && ts && ts < new Date(fromDate).getTime()) return false;
  if (toDate && ts && ts > new Date(toDate).getTime()) return false;
  return true;
}

export function findMatches(repo: SoccerRepository, filter: MatchFilter): Match[] {
  const compAlias = normalizeCompetitionAlias(filter.competition);
  let result = repo.matches.filter((m) => {
    if (!m.homeTeam || !m.awayTeam) return false;
    if (compAlias) {
      const mComp = m.competition.toLowerCase().replace(/\s+/g, '');
      if (mComp !== compAlias) return false;
    }
    if (filter.season !== undefined && m.season !== filter.season) return false;
    if (filter.round !== undefined && m.round !== filter.round) return false;
    if (!dateFilter(m, filter.fromDate, filter.toDate)) return false;

    if (filter.team) {
      const teamCanonical = canonicalizeTeamName(filter.team);
      if (!matchesTeam(m.homeTeam, teamCanonical) && !matchesTeam(m.awayTeam, teamCanonical)) {
        return false;
      }
    }
    if (filter.homeTeam && !matchesTeam(m.homeTeam, filter.homeTeam)) return false;
    if (filter.awayTeam && !matchesTeam(m.awayTeam, filter.awayTeam)) return false;
    if (filter.teamA && filter.teamB) {
      const a = canonicalizeTeamName(filter.teamA);
      const b = canonicalizeTeamName(filter.teamB);
      const homeMatchesBoth =
        (matchesTeam(m.homeTeam, a) && matchesTeam(m.awayTeam, b)) ||
        (matchesTeam(m.homeTeam, b) && matchesTeam(m.awayTeam, a));
      if (!homeMatchesBoth) return false;
    }
    return true;
  });

  result = result.sort(
    (a, b) => (b.datetime?.getTime() ?? 0) - (a.datetime?.getTime() ?? 0)
  );

  if (filter.limit && result.length > filter.limit) {
    result = result.slice(0, filter.limit);
  }
  return result;
}

function decideResult(m: Match, team: string): 'win' | 'draw' | 'loss' | null {
  if (m.homeGoals === null || m.awayGoals === null) return null;
  const isHome = matchesTeam(m.homeTeam, team);
  const isAway = matchesTeam(m.awayTeam, team);
  if (!isHome && !isAway) return null;
  const teamGoals = isHome ? m.homeGoals : m.awayGoals;
  const otherGoals = isHome ? m.awayGoals : m.homeGoals;
  if (teamGoals > otherGoals) return 'win';
  if (teamGoals < otherGoals) return 'loss';
  return 'draw';
}

export function teamStatistics(
  repo: SoccerRepository,
  team: string,
  options: { season?: number; competition?: string; venue?: 'home' | 'away' } = {}
): TeamStats {
  const canonical = canonicalizeTeamName(team);
  const matches = findMatches(repo, {
    team: canonical,
    season: options.season,
    competition: options.competition,
  }).filter((m) => {
    if (options.venue === 'home') return matchesTeam(m.homeTeam, canonical);
    if (options.venue === 'away') return matchesTeam(m.awayTeam, canonical);
    return true;
  });

  let wins = 0;
  let draws = 0;
  let losses = 0;
  let goalsFor = 0;
  let goalsAgainst = 0;

  for (const m of matches) {
    if (m.homeGoals === null || m.awayGoals === null) continue;
    const result = decideResult(m, canonical);
    if (result === 'win') wins++;
    else if (result === 'draw') draws++;
    else if (result === 'loss') losses++;
    const isHome = matchesTeam(m.homeTeam, canonical);
    goalsFor += isHome ? m.homeGoals : m.awayGoals;
    goalsAgainst += isHome ? m.awayGoals : m.homeGoals;
  }

  const total = wins + draws + losses;
  return {
    team: canonical,
    competition: options.competition ?? null,
    season: options.season ?? null,
    matches: total,
    wins,
    draws,
    losses,
    goalsFor,
    goalsAgainst,
    winRate: total > 0 ? Number(((wins / total) * 100).toFixed(1)) : 0,
  };
}

export interface HeadToHeadResult {
  matches: Match[];
  teamA: string;
  teamB: string;
  winsA: number;
  winsB: number;
  draws: number;
  goalsA: number;
  goalsB: number;
}

export function headToHead(
  repo: SoccerRepository,
  teamAInput: string,
  teamBInput: string
): HeadToHeadResult {
  const teamA = canonicalizeTeamName(teamAInput);
  const teamB = canonicalizeTeamName(teamBInput);
  const matches = findMatches(repo, { teamA, teamB });

  let winsA = 0;
  let winsB = 0;
  let draws = 0;
  let goalsA = 0;
  let goalsB = 0;

  for (const m of matches) {
    if (m.homeGoals === null || m.awayGoals === null) continue;
    const homeIsA = matchesTeam(m.homeTeam, teamA);
    const aGoals = homeIsA ? m.homeGoals : m.awayGoals;
    const bGoals = homeIsA ? m.awayGoals : m.homeGoals;
    goalsA += aGoals;
    goalsB += bGoals;
    if (aGoals > bGoals) winsA++;
    else if (aGoals < bGoals) winsB++;
    else draws++;
  }

  return { matches, teamA, teamB, winsA, winsB, draws, goalsA, goalsB };
}

export function findPlayers(
  repo: SoccerRepository,
  options: {
    name?: string;
    nationality?: string;
    club?: string;
    position?: string;
    minOverall?: number;
    limit?: number;
  } = {}
): Player[] {
  let result = repo.players.filter((p) => {
    if (options.name) {
      const q = options.name.toLowerCase();
      if (!p.name.toLowerCase().includes(q)) return false;
    }
    if (options.nationality) {
      const q = options.nationality.toLowerCase();
      if (!p.nationality?.toLowerCase().includes(q)) return false;
    }
    if (options.club) {
      const q = options.club.toLowerCase();
      if (!p.club?.toLowerCase().includes(q)) return false;
    }
    if (options.position) {
      const q = options.position.toLowerCase();
      if (!p.position?.toLowerCase().includes(q)) return false;
    }
    if (options.minOverall !== undefined && (p.overall ?? 0) < options.minOverall) {
      return false;
    }
    return true;
  });

  result = result.sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
  if (options.limit && result.length > options.limit) {
    result = result.slice(0, options.limit);
  }
  return result;
}

export function competitionStandings(
  repo: SoccerRepository,
  competition: string,
  season: number
): StandingRow[] {
  const matches = findMatches(repo, { competition, season });
  const table = new Map<
    string,
    { w: number; d: number; l: number; gf: number; ga: number }
  >();

  for (const m of matches) {
    if (m.homeGoals === null || m.awayGoals === null) continue;
    const homeEntry = table.get(m.homeTeam) ?? { w: 0, d: 0, l: 0, gf: 0, ga: 0 };
    const awayEntry = table.get(m.awayTeam) ?? { w: 0, d: 0, l: 0, gf: 0, ga: 0 };

    homeEntry.gf += m.homeGoals;
    homeEntry.ga += m.awayGoals;
    awayEntry.gf += m.awayGoals;
    awayEntry.ga += m.homeGoals;

    if (m.homeGoals > m.awayGoals) {
      homeEntry.w += 1;
      awayEntry.l += 1;
    } else if (m.homeGoals < m.awayGoals) {
      homeEntry.l += 1;
      awayEntry.w += 1;
    } else {
      homeEntry.d += 1;
      awayEntry.d += 1;
    }

    table.set(m.homeTeam, homeEntry);
    table.set(m.awayTeam, awayEntry);
  }

  const rows: StandingRow[] = Array.from(table.entries()).map(([team, r], index) => ({
    position: index + 1,
    team,
    points: r.w * 3 + r.d,
    played: r.w + r.d + r.l,
    wins: r.w,
    draws: r.d,
    losses: r.l,
    goalsFor: r.gf,
    goalsAgainst: r.ga,
    goalDifference: r.gf - r.ga,
  }));

  rows.sort(
    (a, b) =>
      b.points - a.points ||
      b.goalDifference - a.goalDifference ||
      b.goalsFor - a.goalsFor
  );

  rows.forEach((row, index) => {
    row.position = index + 1;
  });

  return rows;
}

export interface CompetitionStats {
  totalMatches: number;
  averageGoalsPerMatch: number;
  homeWinRate: number;
  drawRate: number;
  awayWinRate: number;
  biggestWins: Match[];
}

export function competitionStats(
  repo: SoccerRepository,
  competition?: string
): CompetitionStats {
  const matches = competition
    ? findMatches(repo, { competition })
    : repo.matches.filter((m) => m.homeGoals !== null && m.awayGoals !== null);

  const validMatches = matches.filter((m) => m.homeGoals !== null && m.awayGoals !== null);
  let totalGoals = 0;
  let homeWins = 0;
  let draws = 0;
  let awayWins = 0;

  for (const m of validMatches) {
    totalGoals += m.homeGoals! + m.awayGoals!;
    if (m.homeGoals! > m.awayGoals!) homeWins++;
    else if (m.homeGoals! < m.awayGoals!) awayWins++;
    else draws++;
  }

  const total = validMatches.length;
  const biggestWins = [...validMatches]
    .sort((a, b) => Math.abs(b.homeGoals! - b.awayGoals!) - Math.abs(a.homeGoals! - a.awayGoals!))
    .slice(0, 10);

  return {
    totalMatches: total,
    averageGoalsPerMatch: total > 0 ? Number((totalGoals / total).toFixed(2)) : 0,
    homeWinRate: total > 0 ? Number(((homeWins / total) * 100).toFixed(1)) : 0,
    drawRate: total > 0 ? Number(((draws / total) * 100).toFixed(1)) : 0,
    awayWinRate: total > 0 ? Number(((awayWins / total) * 100).toFixed(1)) : 0,
    biggestWins,
  };
}

export function bestAwayRecord(repo: SoccerRepository, competition?: string): TeamStats[] {
  const valid = findMatches(repo, { competition }).filter((m) => m.awayGoals !== null && m.homeGoals !== null);
  const stats = new Map<string, { w: number; d: number; l: number; gf: number; ga: number; matches: number }>();

  for (const m of valid) {
    const entry = stats.get(m.awayTeam) ?? { w: 0, d: 0, l: 0, gf: 0, ga: 0, matches: 0 };
    entry.matches += 1;
    entry.gf += m.awayGoals!;
    entry.ga += m.homeGoals!;
    if (m.awayGoals! > m.homeGoals!) entry.w += 1;
    else if (m.awayGoals! < m.homeGoals!) entry.l += 1;
    else entry.d += 1;
    stats.set(m.awayTeam, entry);
  }

  return Array.from(stats.entries())
    .filter(([, s]) => s.matches >= 5)
    .map(([team, s]) => ({
      team,
      competition: competition ?? null,
      season: null,
      matches: s.matches,
      wins: s.w,
      draws: s.d,
      losses: s.l,
      goalsFor: s.gf,
      goalsAgainst: s.ga,
      winRate: Number(((s.w / s.matches) * 100).toFixed(1)),
    }))
    .sort((a, b) => b.winRate - a.winRate || b.wins - a.wins)
    .slice(0, 20);
}

export function formatMatchList(matches: Match[]): string {
  if (matches.length === 0) return 'No matches found.';
  return matches
    .map((m) => {
      const date = m.datetime ? m.datetime.toISOString().split('T')[0] : 'unknown date';
      const score =
        m.homeGoals !== null && m.awayGoals !== null
          ? `${m.homeGoals}-${m.awayGoals}`
          : 'vs';
      const detail = [m.round ? `Round ${m.round}` : '', m.stage]
        .filter(Boolean)
        .join(' ');
      return `- ${date}: ${m.homeTeam} ${score} ${m.awayTeam} (${m.competition}${
        detail ? ` ${detail}` : ''
      })`;
    })
    .join('\n');
}

export function formatHeadToHead(result: HeadToHeadResult): string {
  const lines: string[] = [
    `${result.teamA} vs ${result.teamB} head-to-head in dataset:`,
    formatMatchList(result.matches),
    '',
    `Record: ${result.teamA} ${result.winsA} wins, ${result.teamB} ${result.winsB} wins, ${result.draws} draws`,
    `Goals: ${result.teamA} ${result.goalsA}-${result.goalsB} ${result.teamB}`,
  ];
  return lines.join('\n');
}

export function formatTeamStats(stats: TeamStats): string {
  const scope = [stats.competition, stats.season ? String(stats.season) : '']
    .filter(Boolean)
    .join(' ');
  return [
    `${stats.team} ${scope ? `(${scope})` : ''} record:`,
    `- Matches: ${stats.matches}`,
    `- Wins: ${stats.wins}, Draws: ${stats.draws}, Losses: ${stats.losses}`,
    `- Goals For: ${stats.goalsFor}, Goals Against: ${stats.goalsAgainst}`,
    `- Win rate: ${stats.winRate}%`,
  ].join('\n');
}

export function formatStandings(rows: StandingRow[], season: number, competition: string): string {
  if (rows.length === 0) return `No standings data for ${competition} ${season}.`;
  const lines = [
    `${season} ${competition} Final Standings (calculated from matches):`,
    ...rows.map(
      (r) =>
        `${r.position}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L)${
          r.position === 1 ? ' - Champion' : ''
        }`
    ),
  ];
  return lines.join('\n');
}

export function formatPlayers(players: Player[], totalCount?: number): string {
  if (players.length === 0) return 'No players found.';
  const lines = players.map(
    (p, i) =>
      `${i + 1}. ${p.name} - Overall: ${p.overall ?? '?'}, Nationality: ${
        p.nationality ?? '?'
      }, Position: ${p.position ?? '?'}, Club: ${p.club ?? '?'}`
  );
  if (totalCount !== undefined && totalCount > players.length) {
    lines.push(`(${totalCount - players.length} more players not shown)`);
  }
  return lines.join('\n');
}

export function formatCompetitionStats(stats: CompetitionStats, competition?: string): string {
  const label = competition ?? 'All competitions';
  return [
    `${label} statistics:`,
    `- Total matches: ${stats.totalMatches}`,
    `- Average goals per match: ${stats.averageGoalsPerMatch}`,
    `- Home win rate: ${stats.homeWinRate}%`,
    `- Draw rate: ${stats.drawRate}%`,
    `- Away win rate: ${stats.awayWinRate}%`,
    '',
    `Biggest wins in ${label} (provided data):`,
    formatMatchList(stats.biggestWins),
  ].join('\n');
}
