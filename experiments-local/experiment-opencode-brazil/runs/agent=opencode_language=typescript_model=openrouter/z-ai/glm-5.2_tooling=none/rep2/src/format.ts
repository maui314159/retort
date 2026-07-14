/**
 * Plain-text formatters for query results.
 *
 * The MCP tools return these human-readable strings as their primary content
 * (matching the spec's "Example answer format" blocks). The underlying
 * structured data is also attached as JSON for programmatic consumers.
 */

import type { Match, Player, TeamRecord, HeadToHead } from './types.js';
import { averageGoalsPerMatch, homeAwayRates } from './query.js';

/** Format a single match as a one-line summary. */
export function formatMatch(m: Match): string {
  const score =
    m.homeGoal != null && m.awayGoal != null
      ? `${m.homeGoal}-${m.awayGoal}`
      : '?-?';
  const parts: string[] = [];
  if (m.date) parts.push(m.date);
  parts.push(`${m.homeTeam} ${score} ${m.awayTeam}`);
  const ctx: string[] = [m.competition];
  if (m.round != null) ctx.push(`Round ${m.round}`);
  if (m.stage) ctx.push(String(m.stage));
  if (m.season != null) ctx.push(String(m.season));
  parts.push(`(${ctx.join(', ')})`);
  return parts.join(' ');
}

/** Format a list of matches with an optional header. */
export function formatMatches(matches: Match[], header?: string): string {
  const lines: string[] = [];
  if (header) lines.push(header);
  if (matches.length === 0) {
    lines.push('No matches found.');
    return lines.join('\n');
  }
  for (const m of matches) lines.push(`- ${formatMatch(m)}`);
  lines.push(`(${matches.length} match(es) in dataset)`);
  return lines.join('\n');
}

/** Format a head-to-head summary. */
export function formatHeadToHead(h2h: HeadToHead): string {
  const lines: string[] = [];
  lines.push(`${h2h.teamA} vs ${h2h.teamB}:`);
  for (const m of h2h.matches) lines.push(`- ${formatMatch(m)}`);
  lines.push('');
  lines.push(
    `Head-to-head in dataset: ${h2h.teamA} ${h2h.teamAWins} wins, ${h2h.teamB} ${h2h.teamBWins} wins, ${h2h.draws} draws`,
  );
  return lines.join('\n');
}

/** Format a TeamRecord (statistics block). */
export function formatTeamRecord(rec: TeamRecord, label?: string): string {
  const winRate =
    rec.matches > 0 ? ((rec.wins / rec.matches) * 100).toFixed(1) : '0.0';
  const lines: string[] = [];
  if (label) lines.push(label);
  lines.push(`- Matches: ${rec.matches}`);
  lines.push(`- Wins: ${rec.wins}, Draws: ${rec.draws}, Losses: ${rec.losses}`);
  lines.push(`- Goals For: ${rec.goalsFor}, Goals Against: ${rec.goalsAgainst}`);
  lines.push(`- Points: ${rec.points}`);
  lines.push(`- Win rate: ${winRate}%`);
  return lines.join('\n');
}

/** Format a standings table. */
export function formatStandings(table: TeamRecord[], title?: string): string {
  const lines: string[] = [];
  if (title) lines.push(title);
  if (table.length === 0) {
    lines.push('No standings available.');
    return lines.join('\n');
  }
  table.forEach((r, i) => {
    const gd = r.goalsFor - r.goalsAgainst;
    const champ = i === 0 ? ' - Champion' : '';
    lines.push(
      `${i + 1}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L, GD ${gd >= 0 ? '+' : ''}${gd})${champ}`,
    );
  });
  return lines.join('\n');
}

/** Format a player list (top-N). */
export function formatPlayers(
  players: Player[],
  header?: string,
): string {
  const lines: string[] = [];
  if (header) lines.push(header);
  if (players.length === 0) {
    lines.push('No players found.');
    return lines.join('\n');
  }
  players.forEach((p, i) => {
    lines.push(
      `${i + 1}. ${p.name} - Overall: ${p.overall ?? '?'}, Position: ${p.position ?? '?'}, Club: ${p.club ?? '?'}, Nationality: ${p.nationality ?? '?'}`,
    );
  });
  return lines.join('\n');
}

/** Format aggregate statistics over a match set. */
export function formatStats(matches: Match[], header?: string): string {
  const lines: string[] = [];
  if (header) lines.push(header);
  const avg = averageGoalsPerMatch(matches);
  const rates = homeAwayRates(matches);
  lines.push(`Average goals per match: ${avg.toFixed(2)}`);
  lines.push(`Home win rate: ${(rates.homeWinRate * 100).toFixed(1)}%`);
  lines.push(`Draw rate: ${(rates.drawRate * 100).toFixed(1)}%`);
  lines.push(`Away win rate: ${(rates.awayWinRate * 100).toFixed(1)}%`);
  lines.push(`Total matches: ${rates.total}`);
  return lines.join('\n');
}
