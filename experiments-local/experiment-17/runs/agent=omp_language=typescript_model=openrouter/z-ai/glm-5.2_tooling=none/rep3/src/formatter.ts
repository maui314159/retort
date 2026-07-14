/**
 * brazilian-soccer-mcp / src/formatter.ts
 *
 * Presentation layer.
 *
 * Context block:
 * Turns structured query results into the human-readable answer formats shown
 * in the TASK.md examples (match lists, team records, head-to-head, standings,
 * biggest wins, aggregate stats, player lists). The MCP server returns these
 * as tool-result text so an attached LLM can relay them verbatim or paraphrase.
 */

import type {
  Match, TeamStats, HeadToHead, StandingRow, AggregateStats, Player, ClubSummary,
} from './types.js';
function fmtDate(m: Match): string {
  return m.date ? m.date.toISOString().slice(0, 10) : (m.dateRaw || 'unknown date');
}

function competitionTag(m: Match): string {
  const parts = [m.competition];
  if (m.round) parts.push(`Round ${m.round}`);
  if (m.stage) parts.push(m.stage);
  return parts.join(' ');
}

/** Format a match list with an optional head-to-head summary line. */
export function formatMatchList(matches: Match[], heading?: string): string {
  const lines: string[] = [];
  if (heading) lines.push(heading);
  if (matches.length === 0) {
    lines.push('No matches found.');
    return lines.join('\n');
  }
  const shown = matches.slice(0, 50);
  for (const m of shown) {
    const hg = m.homeGoals ?? '?';
    const ag = m.awayGoals ?? '?';
    lines.push(`- ${fmtDate(m)}: ${m.homeTeam} ${hg}-${ag} ${m.awayTeam} (${competitionTag(m)})`);
  }
  const remaining = matches.length - shown.length;
  if (remaining > 0) lines.push(`... (${remaining} more matches in dataset)`);
  return lines.join('\n');
}

/** Format a head-to-head summary plus the recent match list. */
export function formatHeadToHead(h2h: HeadToHead, matches: Match[]): string {
  const lines: string[] = [];
  lines.push(`Head-to-head in dataset (${h2h.teamA} vs ${h2h.teamB}): ${h2h.matches} matches`);
  lines.push(`${h2h.teamA} ${h2h.aWins} wins, ${h2h.teamB} ${h2h.bWins} wins, ${h2h.draws} draws`);
  lines.push('');
  lines.push(formatMatchList(matches));
  return lines.join('\n');
}

/** Format a TeamStats record with a venue label. */
export function formatTeamStats(stats: TeamStats, venueLabel?: string): string {
  const pct = (stats.winRate * 100).toFixed(1);
  const heading = venueLabel
    ? `${stats.team} ${venueLabel} record (${stats.matches} matches)`
    : `${stats.team} record (${stats.matches} matches)`;
  return [
    heading,
    `- Wins: ${stats.wins}, Draws: ${stats.draws}, Losses: ${stats.losses}`,
    `- Goals For: ${stats.goalsFor}, Goals Against: ${stats.goalsAgainst}, GD: ${stats.goalDifference > 0 ? '+' : ''}${stats.goalDifference}`,
    `- Points: ${stats.points}`,
    `- Win rate: ${pct}%`,
  ].join('\n');
}

/** Format a standings table; marks the champion (position 1). */
export function formatStandings(rows: StandingRow[], competition: string, season: number): string {
  const lines: string[] = [`${season} ${competition} Standings (calculated from matches):`];
  if (rows.length === 0) {
    lines.push('No standings data found for this competition/season.');
    return lines.join('\n');
  }
  const shown = rows.slice(0, 20);
  for (const r of shown) {
    const champ = r.position === 1 ? ' - Champion' : '';
    lines.push(`${r.position}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L, GD ${r.goalDifference > 0 ? '+' : ''}${r.goalDifference})${champ}`);
  }
  const remaining = rows.length - shown.length;
  if (remaining > 0) lines.push(`... (${remaining} more teams)`);
  return lines.join('\n');
}

/** Format the biggest victories list. */
export function formatBiggestWins(matches: Match[]): string {
  const lines: string[] = ['Biggest victories in dataset:'];
  if (matches.length === 0) {
    lines.push('No matches found.');
    return lines.join('\n');
  }
  matches.forEach((m, i) => {
    lines.push(`${i + 1}. ${fmtDate(m)}: ${m.homeTeam} ${m.homeGoals ?? '?'}-${m.awayGoals ?? '?'} ${m.awayTeam} (${m.competition})`);
  });
  return lines.join('\n');
}

/** Format aggregate stats for a match set. */
export function formatAggregateStats(stats: AggregateStats, label?: string): string {
  const lines: string[] = [];
  if (label) lines.push(label);
  lines.push(`Matches with scores: ${stats.matches}`);
  lines.push(`Total goals: ${stats.totalGoals}`);
  lines.push(`Average goals per match: ${stats.averageGoalsPerMatch.toFixed(2)}`);
  lines.push(`Home win rate: ${(stats.homeWinRate * 100).toFixed(1)}%`);
  lines.push(`Away win rate: ${(stats.awayWinRate * 100).toFixed(1)}%`);
  lines.push(`Draw rate: ${(stats.drawRate * 100).toFixed(1)}%`);
  return lines.join('\n');
}

/** Format a player list, ranked by overall rating. */
export function formatPlayerList(players: Player[], heading?: string): string {
  const lines: string[] = [];
  if (heading) lines.push(heading);
  if (players.length === 0) {
    lines.push('No players found.');
    return lines.join('\n');
  }
  players.forEach((p, i) => {
    lines.push(`${i + 1}. ${p.name} - Overall: ${p.overall ?? '?'}, Position: ${p.position || '?'}, Club: ${p.club || '?'}, Age: ${p.age ?? '?'}, Nationality: ${p.nationality}`);
  });
  return lines.join('\n');
}

/** Format a Brazilian-clubs summary (player counts and average ratings). */
export function formatBrazilianClubsSummary(summary: ClubSummary[]): string {
  const lines: string[] = ['Brazilian players at Brazilian clubs:'];
  if (summary.length === 0) {
    lines.push('No Brazilian clubs found in player dataset.');
    return lines.join('\n');
  }
  for (const s of summary) {
    lines.push(`- ${s.club}: ${s.count} players (avg rating: ${s.avgOverall.toFixed(0)})`);
  }
  return lines.join('\n');
}
