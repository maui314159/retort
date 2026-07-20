/**
 * Brazilian Soccer MCP Server — response formatting
 * ==================================================
 * Context block:
 *   Pure helpers that turn `MatchRecord`/`PlayerRecord`/`TeamTally` objects
 *   into the human-readable text blocks shown in the MCP tool results. The
 *   formatting mirrors the "Example answer format" snippets in the task spec
 *   (e.g. "2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Round 22)").
 */

import type { MatchRecord, PlayerRecord } from './types.js';
import type { TeamTally } from './types.js';

/** Format a single match line: "YYYY-MM-DD: Home X-Y Away (Competition Round N)". */
export function formatMatch(m: MatchRecord): string {
  const date = m.dateStr || 'unknown date';
  const score =
    m.homeGoal !== null && m.awayGoal !== null ? `${m.homeGoal}-${m.awayGoal}` : '?-?';
  const extra: string[] = [m.competition];
  if (m.round) extra.push(`Round ${m.round}`);
  if (m.stage) extra.push(m.stage);
  if (m.arena) extra.push(m.arena);
  return `- ${date}: ${m.home} ${score} ${m.away} (${extra.join(', ')})`;
}

/** Format a player line: "Name — Overall: N, Position: P, Club: C (Nationality)". */
export function formatPlayer(p: PlayerRecord, rank?: number): string {
  const prefix = rank ? `${rank}. ` : '- ';
  const overall = p.overall ?? '—';
  return `${prefix}${p.name} — Overall: ${overall}, Position: ${p.position || '?'}, Club: ${p.club || '—'} (${p.nationality})`;
}

/** Format a standings row: "1. Team - PP pts (WW, DD, LL)". */
export function formatStanding(t: TeamTally, rank: number, champion?: boolean): string {
  const tag = champion ? ' - Champion' : '';
  return `${rank}. ${t.team} - ${t.points} pts (${t.wins}W, ${t.draws}D, ${t.losses}L) — GF:${t.goalsFor} GA:${t.goalsAgainst}${tag}`;
}

/** Format a team record summary block. */
export function formatTeamRecord(t: TeamTally, label: string): string {
  const total = t.played || 1;
  const winRate = ((t.wins / total) * 100).toFixed(1);
  return [
    `${label}:`,
    `- Matches: ${t.played}`,
    `- Wins: ${t.wins}, Draws: ${t.draws}, Losses: ${t.losses}`,
    `- Goals For: ${t.goalsFor}, Goals Against: ${t.goalsAgainst}`,
    `- Win rate: ${winRate}%`,
  ].join('\n');
}
