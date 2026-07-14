/**
 * Match query tools: search matches by team, competition, season, date range.
 * Handles head-to-head queries between two teams.
 */

import { teamMatchesSearch, normalizeTeamName } from '../data/normalize.js';
import type { Match, HeadToHeadResult } from '../data/types.js';

export interface MatchSearchParams {
  team?: string;
  team1?: string;
  team2?: string;
  competition?: string;
  season?: number;
  dateFrom?: string;
  dateTo?: string;
  limit?: number;
}

function competitionMatchesFilter(comp: string, filter: string): boolean {
  const f = filter.toLowerCase();
  const c = comp.toLowerCase();
  // Aliases
  if (f === 'brasileirao' || f === 'serie a') return c === 'brasileirao' || c === 'historico';
  if (f === 'historico' || f === 'historical') return c === 'historico';
  if (f === 'copa' || f === 'copa do brasil' || f === 'cup') return c === 'copa_do_brasil';
  if (f === 'libertadores') return c === 'libertadores';
  if (f === 'extended') return c !== 'brasileirao' && c !== 'copa_do_brasil' && c !== 'libertadores' && c !== 'historico';
  return c.includes(f) || f.includes(c);
}

export function searchMatches(matches: Match[], params: MatchSearchParams): Match[] {
  let results = matches;

  if (params.team) {
    results = results.filter(
      (m) => teamMatchesSearch(m.homeTeam, params.team!) || teamMatchesSearch(m.awayTeam, params.team!)
    );
  }

  if (params.team1 && params.team2) {
    results = results.filter(
      (m) =>
        (teamMatchesSearch(m.homeTeam, params.team1!) && teamMatchesSearch(m.awayTeam, params.team2!)) ||
        (teamMatchesSearch(m.homeTeam, params.team2!) && teamMatchesSearch(m.awayTeam, params.team1!))
    );
  } else if (params.team1) {
    results = results.filter(
      (m) => teamMatchesSearch(m.homeTeam, params.team1!) || teamMatchesSearch(m.awayTeam, params.team1!)
    );
  }

  if (params.competition) {
    results = results.filter((m) => competitionMatchesFilter(m.competition, params.competition!));
  }

  if (params.season) {
    results = results.filter((m) => m.season === params.season);
  }

  if (params.dateFrom) {
    results = results.filter((m) => m.date >= params.dateFrom!);
  }

  if (params.dateTo) {
    results = results.filter((m) => m.date <= params.dateTo!);
  }

  results = results.filter((m) => m.date !== '');

  // Sort descending by date
  results.sort((a, b) => b.date.localeCompare(a.date));

  const limit = params.limit ?? 20;
  return results.slice(0, limit);
}

export function getHeadToHead(matches: Match[], team1: string, team2: string, competition?: string, season?: number): HeadToHeadResult {
  let h2h = matches.filter(
    (m) =>
      (teamMatchesSearch(m.homeTeam, team1) && teamMatchesSearch(m.awayTeam, team2)) ||
      (teamMatchesSearch(m.homeTeam, team2) && teamMatchesSearch(m.awayTeam, team1))
  );

  if (competition) h2h = h2h.filter((m) => competitionMatchesFilter(m.competition, competition));
  if (season) h2h = h2h.filter((m) => m.season === season);

  h2h.sort((a, b) => b.date.localeCompare(a.date));

  let team1Wins = 0, team2Wins = 0, draws = 0;
  let team1Goals = 0, team2Goals = 0;

  for (const m of h2h) {
    const team1IsHome = teamMatchesSearch(m.homeTeam, team1);
    const t1g = team1IsHome ? m.homeGoals : m.awayGoals;
    const t2g = team1IsHome ? m.awayGoals : m.homeGoals;
    team1Goals += t1g;
    team2Goals += t2g;
    if (t1g > t2g) team1Wins++;
    else if (t2g > t1g) team2Wins++;
    else draws++;
  }

  return { matches: h2h, team1Wins, team2Wins, draws, team1Goals, team2Goals };
}

export function formatMatch(m: Match): string {
  const score = `${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam}`;
  const comp = m.competition.replace(/_/g, ' ');
  const round = m.round ? ` Round ${m.round}` : '';
  const stage = m.stage ? ` (${m.stage})` : '';
  return `${m.date}: ${score} [${comp}${round}${stage} ${m.season || ''}]`;
}

export function formatSearchResults(matches: Match[], total: number, params: MatchSearchParams): string {
  if (matches.length === 0) return 'No matches found for the given criteria.';

  const lines: string[] = [];
  const teamDesc = params.team1 && params.team2
    ? `${normalizeTeamName(params.team1)} vs ${normalizeTeamName(params.team2)}`
    : params.team
      ? normalizeTeamName(params.team)
      : 'all teams';

  lines.push(`Matches for ${teamDesc}${params.season ? ` (${params.season})` : ''}:`);
  lines.push('');

  for (const m of matches) {
    lines.push(`- ${formatMatch(m)}`);
  }

  if (total > matches.length) {
    lines.push('');
    lines.push(`Showing ${matches.length} of ${total} matches. Use dateFrom/dateTo or season to narrow results.`);
  }

  return lines.join('\n');
}

export function formatHeadToHead(result: HeadToHeadResult, team1: string, team2: string): string {
  const t1 = normalizeTeamName(team1);
  const t2 = normalizeTeamName(team2);
  const lines: string[] = [];

  lines.push(`Head-to-head: ${t1} vs ${t2}`);
  lines.push(`Record: ${t1} ${result.team1Wins}W / ${result.draws}D / ${result.team2Wins}W ${t2}`);
  lines.push(`Goals: ${t1} ${result.team1Goals} - ${result.team2Goals} ${t2}`);
  lines.push('');
  lines.push(`Recent matches (${result.matches.length} total):`);

  for (const m of result.matches.slice(0, 20)) {
    lines.push(`- ${formatMatch(m)}`);
  }

  if (result.matches.length > 20) {
    lines.push(`... and ${result.matches.length - 20} more matches`);
  }

  return lines.join('\n');
}
