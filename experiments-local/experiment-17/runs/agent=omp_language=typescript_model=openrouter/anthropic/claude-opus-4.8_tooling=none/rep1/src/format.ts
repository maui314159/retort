/**
 * Context
 * =======
 * Human-readable response formatting for the Brazilian Soccer MCP server.
 *
 * MCP tools return text content blocks; these helpers turn the structured query
 * results from store.ts into the concise, readable summaries the spec's example
 * answer formats call for (match lists, team records with win rate, head-to-head
 * tallies, standings tables, player rankings, league aggregates).
 *
 * Formatting only — no data access. Percentages are rounded to one decimal,
 * averages to two, matching the spec's sample outputs.
 */

import type { Match, Player, StandingRow, TeamRecord } from './types.js';

const pct = (n: number): string => `${(n * 100).toFixed(1)}%`;

/** "Flamengo 2-1 Fluminense" with optional date/competition/round prefix line. */
export function formatMatchLine(m: Match): string {
  const score = `${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam}`;
  const meta: string[] = [];
  if (m.competition) meta.push(m.competition);
  if (m.round) meta.push(m.round);
  if (m.season && !m.round) meta.push(String(m.season));
  const date = m.date ?? (m.season ? String(m.season) : 'unknown date');
  return `${date}: ${score}${meta.length ? ` (${meta.join(' · ')})` : ''}`;
}

export function formatMatches(matches: Match[], total: number): string {
  if (matches.length === 0) return 'No matches found.';
  const lines = matches.map((m) => `- ${formatMatchLine(m)}`);
  const header =
    total > matches.length
      ? `Showing ${matches.length} of ${total} matches:`
      : `${matches.length} match${matches.length === 1 ? '' : 'es'}:`;
  return `${header}\n${lines.join('\n')}`;
}

export function formatTeamRecord(team: string, rec: TeamRecord, scope: string): string {
  if (rec.matches === 0) return `No matches found for ${team}${scope ? ` (${scope})` : ''}.`;
  const winRate = pct(rec.wins / rec.matches);
  return [
    `${team}${scope ? ` (${scope})` : ''}:`,
    `- Matches: ${rec.matches}`,
    `- Wins: ${rec.wins}, Draws: ${rec.draws}, Losses: ${rec.losses}`,
    `- Goals For: ${rec.goalsFor}, Goals Against: ${rec.goalsAgainst}`,
    `- Win rate: ${winRate}`,
  ].join('\n');
}

export function formatHeadToHead(h2h: {
  teamA: string;
  teamB: string;
  aWins: number;
  bWins: number;
  draws: number;
  aGoals: number;
  bGoals: number;
  matches: Match[];
}): string {
  const totalMeetings = h2h.aWins + h2h.bWins + h2h.draws;
  if (totalMeetings === 0) return `No matches found between ${h2h.teamA} and ${h2h.teamB}.`;
  const lines = h2h.matches.map((m) => `- ${formatMatchLine(m)}`);
  return [
    `${h2h.teamA} vs ${h2h.teamB}:`,
    ...lines,
    '',
    `Head-to-head: ${h2h.teamA} ${h2h.aWins} wins, ${h2h.teamB} ${h2h.bWins} wins, ${h2h.draws} draws`,
    `Goals: ${h2h.teamA} ${h2h.aGoals}, ${h2h.teamB} ${h2h.bGoals} (${totalMeetings} meetings)`,
  ].join('\n');
}

export function formatStandings(
  competition: string,
  season: number,
  rows: StandingRow[],
  limit: number,
): string {
  if (rows.length === 0) return `No data to compute ${competition} ${season} standings.`;
  const shown = rows.slice(0, limit);
  const body = shown.map((r, i) => {
    const pos = String(i + 1).padStart(2, ' ');
    return `${pos}. ${r.team} - ${r.points} pts (${r.wins}W ${r.draws}D ${r.losses}L, GF ${r.goalsFor} GA ${r.goalsAgainst}, GD ${r.goalDifference >= 0 ? '+' : ''}${r.goalDifference})`;
  });
  const champ = ` — Champion: ${rows[0].team}`;
  return `${competition} ${season} standings (computed from matches)${champ}:\n${body.join('\n')}`;
}

export function formatPlayer(p: Player): string {
  const parts = [`Overall: ${p.overall}`];
  if (p.position) parts.push(`Position: ${p.position}`);
  if (p.club) parts.push(`Club: ${p.club}`);
  if (p.age !== undefined) parts.push(`Age: ${p.age}`);
  return `${p.name} (${p.nationality}) - ${parts.join(', ')}`;
}

export function formatPlayers(players: Player[], total: number): string {
  if (players.length === 0) return 'No players found.';
  const lines = players.map((p, i) => `${i + 1}. ${formatPlayer(p)}`);
  const header =
    total > players.length
      ? `Showing top ${players.length} of ${total} players:`
      : `${players.length} player${players.length === 1 ? '' : 's'}:`;
  return `${header}\n${lines.join('\n')}`;
}

export function formatLeagueStats(
  scope: string,
  stats: {
    matches: number;
    totalGoals: number;
    avgGoalsPerMatch: number;
    homeWinRate: number;
    awayWinRate: number;
    drawRate: number;
  },
): string {
  if (stats.matches === 0) return `No matches found${scope ? ` for ${scope}` : ''}.`;
  return [
    `Statistics${scope ? ` (${scope})` : ''}:`,
    `- Matches: ${stats.matches}`,
    `- Total goals: ${stats.totalGoals}`,
    `- Average goals per match: ${stats.avgGoalsPerMatch.toFixed(2)}`,
    `- Home win rate: ${pct(stats.homeWinRate)}`,
    `- Away win rate: ${pct(stats.awayWinRate)}`,
    `- Draw rate: ${pct(stats.drawRate)}`,
  ].join('\n');
}

export function formatBiggestWins(matches: Match[], scope: string): string {
  if (matches.length === 0) return `No matches found${scope ? ` for ${scope}` : ''}.`;
  const lines = matches.map((m, i) => {
    const margin = Math.abs(m.homeGoals - m.awayGoals);
    return `${i + 1}. ${formatMatchLine(m)} [margin ${margin}]`;
  });
  return `Biggest victories${scope ? ` (${scope})` : ''}:\n${lines.join('\n')}`;
}
