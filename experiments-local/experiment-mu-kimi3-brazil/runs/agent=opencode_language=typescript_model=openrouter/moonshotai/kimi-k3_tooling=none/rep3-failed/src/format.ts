/**
 * Response formatting helpers — produce the concise text layouts shown in
 * the specification's example answers.
 */
import { Match, TeamIdentity, TeamRecord } from './types.js';

export function formatTeamName(t: TeamIdentity): string {
  return t.displayName;
}

export function formatMatch(m: Match): string {
  const date = m.date ?? 'unknown date';
  const score = m.played ? `${m.homeGoals}-${m.awayGoals}` : 'vs (not played)';
  const context = [m.competition, m.round].filter(Boolean).join(' ');
  const season = m.season !== undefined ? ` ${m.season}` : '';
  return `${date}: ${m.homeTeam.displayName} ${score} ${m.awayTeam.displayName} (${context}${season})`.replace(/\s+\)/, ')');
}

export function formatMatchList(matches: Match[], max = 25): string {
  const shown = matches.slice(0, max);
  const lines = shown.map((m) => `- ${formatMatch(m)}`);
  if (matches.length > shown.length) {
    lines.push(`... (${matches.length - shown.length} more matches in dataset)`);
  }
  return lines.join('\n');
}

export function winRate(r: TeamRecord): string {
  return r.matches ? `${((r.wins / r.matches) * 100).toFixed(1)}%` : '0.0%';
}

export function formatRecord(r: TeamRecord): string {
  return [
    `Matches: ${r.matches}`,
    `Wins: ${r.wins}, Draws: ${r.draws}, Losses: ${r.losses}`,
    `Goals For: ${r.goalsFor}, Goals Against: ${r.goalsAgainst}`,
    `Win rate: ${winRate(r)}`,
  ].join('\n');
}

export function pct(x: number): string {
  return `${(x * 100).toFixed(1)}%`;
}

export function num(x: number, digits = 2): string {
  return x.toFixed(digits);
}
