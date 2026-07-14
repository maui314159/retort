/**
 * Statistical analysis tools: biggest wins, averages, home/away performance.
 */

import { normalizeTeamName } from '../data/normalize.js';
import type { Match } from '../data/types.js';

export interface MatchStats {
  totalMatches: number;
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

function filterByCompetitionAndSeason(matches: Match[], competition?: string, season?: number): Match[] {
  let filtered = matches;
  if (competition) {
    const f = competition.toLowerCase();
    filtered = filtered.filter((m) => {
      const c = m.competition.toLowerCase();
      if (f === 'brasileirao' || f === 'serie a') return c === 'brasileirao' || c === 'historico';
      return c.includes(f) || f.includes(c);
    });
  }
  if (season) filtered = filtered.filter((m) => m.season === season);
  return filtered.filter((m) => m.date !== '');
}

export function computeStats(matches: Match[], competition?: string, season?: number): MatchStats {
  const filtered = filterByCompetitionAndSeason(matches, competition, season);

  let totalGoals = 0, homeWins = 0, draws = 0, awayWins = 0;
  let homeGoals = 0, awayGoals = 0;

  for (const m of filtered) {
    totalGoals += m.homeGoals + m.awayGoals;
    homeGoals += m.homeGoals;
    awayGoals += m.awayGoals;
    if (m.homeGoals > m.awayGoals) homeWins++;
    else if (m.homeGoals === m.awayGoals) draws++;
    else awayWins++;
  }

  const total = filtered.length;
  return {
    totalMatches: total,
    totalGoals,
    avgGoalsPerMatch: total > 0 ? Math.round((totalGoals / total) * 100) / 100 : 0,
    homeWins,
    draws,
    awayWins,
    homeWinRate: total > 0 ? Math.round((homeWins / total) * 1000) / 10 : 0,
    drawRate: total > 0 ? Math.round((draws / total) * 1000) / 10 : 0,
    awayWinRate: total > 0 ? Math.round((awayWins / total) * 1000) / 10 : 0,
    avgHomeGoals: total > 0 ? Math.round((homeGoals / total) * 100) / 100 : 0,
    avgAwayGoals: total > 0 ? Math.round((awayGoals / total) * 100) / 100 : 0,
  };
}

export function getBiggestWins(matches: Match[], competition?: string, limit = 10): Match[] {
  const filtered = filterByCompetitionAndSeason(matches, competition);
  return filtered
    .filter((m) => m.homeGoals + m.awayGoals > 0)
    .sort((a, b) => {
      const gdA = Math.abs(a.homeGoals - a.awayGoals);
      const gdB = Math.abs(b.homeGoals - b.awayGoals);
      if (gdB !== gdA) return gdB - gdA;
      return (b.homeGoals + b.awayGoals) - (a.homeGoals + a.awayGoals);
    })
    .slice(0, limit);
}

export function formatStats(stats: MatchStats, competition?: string, season?: number): string {
  const ctx = [
    competition ? competition.replace(/_/g, ' ') : 'all competitions',
    season ? String(season) : '',
  ].filter(Boolean).join(' ');

  const lines: string[] = [];
  lines.push(`Statistics — ${ctx}:`);
  lines.push('');
  lines.push(`Total matches: ${stats.totalMatches}`);
  lines.push(`Total goals: ${stats.totalGoals}`);
  lines.push(`Avg goals/match: ${stats.avgGoalsPerMatch}`);
  lines.push('');
  lines.push(`Home wins: ${stats.homeWins} (${stats.homeWinRate}%)`);
  lines.push(`Draws: ${stats.draws} (${stats.drawRate}%)`);
  lines.push(`Away wins: ${stats.awayWins} (${stats.awayWinRate}%)`);
  lines.push('');
  lines.push(`Avg home goals: ${stats.avgHomeGoals}`);
  lines.push(`Avg away goals: ${stats.avgAwayGoals}`);

  return lines.join('\n');
}

export function formatBiggestWins(wins: Match[], competition?: string): string {
  if (wins.length === 0) return 'No match data found.';

  const ctx = competition ? competition.replace(/_/g, ' ') : 'all competitions';
  const lines: string[] = [`Biggest wins — ${ctx}:`];
  lines.push('');

  for (let i = 0; i < wins.length; i++) {
    const m = wins[i];
    const winner = m.homeGoals > m.awayGoals
      ? `${normalizeTeamName(m.homeTeam)} ${m.homeGoals}-${m.awayGoals} ${normalizeTeamName(m.awayTeam)}`
      : `${normalizeTeamName(m.awayTeam)} ${m.awayGoals}-${m.homeGoals} ${normalizeTeamName(m.homeTeam)}`;
    const gd = Math.abs(m.homeGoals - m.awayGoals);
    lines.push(`${i + 1}. ${m.date}: ${winner} (GD: +${gd}) [${m.competition.replace(/_/g, ' ')} ${m.season || ''}]`);
  }

  return lines.join('\n');
}
