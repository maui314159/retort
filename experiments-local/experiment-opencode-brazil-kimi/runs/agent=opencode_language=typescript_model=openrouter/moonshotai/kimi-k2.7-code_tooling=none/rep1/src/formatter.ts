/*
 * Brazilian Soccer MCP Server - Response formatters
 *
 * Turns query-engine results into the human-readable formats shown in the
 * specification, including head-to-head summaries, team records, standings,
 * player rankings, and statistical aggregates.
 */

import { Match, Player, Standing, TeamRecord, HeadToHead } from './types.js';
import { inferResult, winnerTeam } from './normalizer.js';

function fmtScore(match: Match): string {
  if (match.homeGoal === null || match.awayGoal === null) return 'vs';
  return `${match.homeGoal}-${match.awayGoal}`;
}

function fmtContext(match: Match): string {
  const parts: string[] = [];
  if (match.competition) parts.push(match.competition);
  if (match.round) parts.push(`Round ${match.round}`);
  else if (match.stage) parts.push(match.stage);
  return parts.length > 0 ? ` (${parts.join(' ')})` : '';
}

export function formatMatches(matches: Match[]): string {
  if (matches.length === 0) return 'No matches found.';
  const lines = matches.map(
    (m) => `- ${m.date}: ${m.homeTeam} ${fmtScore(m)} ${m.awayTeam}${fmtContext(m)}`
  );
  return lines.join('\n');
}

export function formatHeadToHead(h2h: HeadToHead): string {
  const lines: string[] = [
    `${h2h.teamA} vs ${h2h.teamB}:`,
    formatMatches(h2h.matches.slice(0, 10))
  ];

  const remaining = h2h.matches.length - 10;
  if (remaining > 0) {
    lines.push(`... (${remaining} more matches in dataset)`);
  }

  lines.push(
    `\nHead-to-head in dataset: ${h2h.teamA} ${h2h.teamAWins} wins, ${h2h.teamB} ${h2h.teamBWins} wins, ${h2h.draws} draws`
  );

  return lines.join('\n');
}

export function formatTeamRecord(record: TeamRecord, label?: string): string {
  const title = label ? `${label}:` : `${record.team}:`;
  const winRate = record.matches > 0 ? ((record.wins / record.matches) * 100).toFixed(1) : '0.0';
  return [
    title,
    `- Matches: ${record.matches}`,
    `- Wins: ${record.wins}, Draws: ${record.draws}, Losses: ${record.losses}`,
    `- Goals For: ${record.goalsFor}, Goals Against: ${record.goalsAgainst}`,
    `- Win rate: ${winRate}%`
  ].join('\n');
}

export function formatStandings(standings: Standing[], label: string): string {
  if (standings.length === 0) return `No standings available for ${label}.`;
  const lines = [`${label} Final Standings (calculated from matches):`];
  for (const s of standings.slice(0, 20)) {
    const gd = s.goalsFor - s.goalsAgainst;
    const gdStr = gd >= 0 ? `+${gd}` : `${gd}`;
    const champ = s.position === 1 ? ' - Champion' : '';
    lines.push(
      `${s.position}. ${s.team} - ${s.points} pts (${s.wins}W, ${s.draws}D, ${s.losses}L) GD ${gdStr}${champ}`
    );
  }
  return lines.join('\n');
}

export function formatPlayers(players: Player[], label: string): string {
  if (players.length === 0) return `No players found for ${label}.`;
  const lines = [`${label}:`];
  for (let i = 0; i < players.length; i++) {
    const p = players[i];
    lines.push(
      `${i + 1}. ${p.name} - Overall: ${p.overall ?? 'N/A'}, Position: ${p.position ?? 'N/A'}, Club: ${p.club ?? 'N/A'}`
    );
  }
  return lines.join('\n');
}

export function formatPlayerClubsSummary(
  summary: Map<string, { count: number; average: number }>,
  label: string
): string {
  const entries = Array.from(summary.entries()).sort((a, b) => b[1].count - a[1].count);
  if (entries.length === 0) return `${label}: no clubs found.`;
  const lines = [`${label}:`];
  for (const [club, data] of entries) {
    lines.push(`- ${club}: ${data.count} players (avg rating: ${data.average})`);
  }
  return lines.join('\n');
}

export function formatBiggestWins(matches: Match[]): string {
  if (matches.length === 0) return 'No matches found.';
  return formatMatches(matches);
}

export function formatAverageGoals(average: number, filters?: string): string {
  const prefix = filters ? `Average goals per match${filters}` : 'Average goals per match';
  return `${prefix}: ${average.toFixed(2)}`;
}

export function formatHomeWinRate(rate: number): string {
  return `Home win rate: ${(rate * 100).toFixed(1)}%`;
}

export function formatSimpleAnswer(question: string, result: unknown): string {
  if (result === undefined || result === null) return 'I could not find an answer to that question.';
  if (typeof result === 'string') return result;
  if (Array.isArray(result)) {
    if (result.length === 0) return 'No results found.';
    if (typeof result[0] === 'object' && 'name' in result[0]) {
      return formatPlayers(result as Player[], question);
    }
    if (typeof result[0] === 'object' && 'homeTeam' in result[0]) {
      return formatMatches(result as Match[]);
    }
    return JSON.stringify(result, null, 2);
  }
  if (typeof result === 'object' && 'team' in result) {
    return formatTeamRecord(result as TeamRecord, question);
  }
  return JSON.stringify(result, null, 2);
}
