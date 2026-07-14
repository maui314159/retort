import type { Match, Player, TeamStats, CompetitionStanding } from './types.js';

export function formatMatch(m: Match): string {
  const date = m.date ?? 'Unknown date';
  const comp = m.competition;
  const extra: string[] = [];
  if (m.round) extra.push(`Round ${m.round}`);
  if (m.stage) extra.push(m.stage);
  const extraStr = extra.length ? ` (${extra.join(', ')})` : '';
  return `${date}: ${m.home_team} ${m.home_goal}-${m.away_goal} ${m.away_team} (${comp}${extraStr})`.replace(' ()', '');
}

export function formatMatches(matches: Match[], title: string): string {
  if (matches.length === 0) return `${title}\nNo matches found.`;
  const lines = [`${title}:`];
  for (const m of matches) {
    lines.push(`- ${formatMatch(m)}`);
  }
  return lines.join('\n');
}

export function formatTeamStats(stats: TeamStats): string {
  const lines = [`${stats.team}:`];
  lines.push(`- Matches: ${stats.matches}`);
  lines.push(`- Wins: ${stats.wins}, Draws: ${stats.draws}, Losses: ${stats.losses}`);
  lines.push(`- Goals For: ${stats.goalsFor}, Goals Against: ${stats.goalsAgainst}`);
  if (stats.matches) {
    lines.push(`- Win rate: ${((stats.wins / stats.matches) * 100).toFixed(1)}%`);
  }
  if (stats.homeMatches && stats.homeMatches.matches) {
    const h = stats.homeMatches;
    lines.push(`- Home matches: ${h.matches} (${h.wins}W/${h.draws}D/${h.losses}L), ${h.goalsFor} GF / ${h.goalsAgainst} GA`);
  }
  if (stats.awayMatches && stats.awayMatches.matches) {
    const a = stats.awayMatches;
    lines.push(`- Away matches: ${a.matches} (${a.wins}W/${a.draws}D/${a.losses}L), ${a.goalsFor} GF / ${a.goalsAgainst} GA`);
  }
  return lines.join('\n');
}

export function formatHeadToHead(
  team1: string,
  team2: string,
  result: { matches: Match[]; team1Wins: number; team2Wins: number; draws: number }
): string {
  const lines = [`${team1} vs ${team2}:`];
  for (const m of result.matches.slice(0, 20)) {
    lines.push(`- ${formatMatch(m)}`);
  }
  if (result.matches.length > 20) {
    lines.push(`- ... (${result.matches.length - 20} more matches in dataset)`);
  }
  lines.push(`\nHead-to-head in dataset: ${team1} ${result.team1Wins} wins, ${team2} ${result.team2Wins} wins, ${result.draws} draws`);
  return lines.join('\n');
}

export function formatStandings(standings: CompetitionStanding[], competition: string, season: number): string {
  const lines = [`${season} ${competition} Final Standings (calculated from matches):`];
  for (const s of standings.slice(0, 20)) {
    const tag = s.position === 1 ? ' - Champion' : '';
    lines.push(`${s.position}. ${s.team} - ${s.points} pts (${s.wins}W, ${s.draws}D, ${s.losses}L)${tag}`);
  }
  if (standings.length > 20) {
    lines.push(`... (${standings.length - 20} more teams)`);
  }
  return lines.join('\n');
}

export function formatPlayer(p: Player): string {
  return `${p.name} - Overall: ${p.overall ?? 'N/A'}, Position: ${p.position ?? 'N/A'}, Club: ${p.club ?? 'N/A'}`;
}

export function formatPlayers(players: Player[], title: string): string {
  if (players.length === 0) return `${title}\nNo players found.`;
  const lines = [`${title}:`];
  for (let i = 0; i < players.length; i++) {
    lines.push(`${i + 1}. ${formatPlayer(players[i])}`);
  }
  return lines.join('\n');
}

export function formatStatsSummary(summary: {
  totalMatches: number;
  totalGoals: number;
  averageGoalsPerMatch: number;
  homeWinRate: number;
  awayWinRate: number;
  drawRate: number;
  homeWins: number;
  awayWins: number;
  draws: number;
  biggestWins: Match[];
}): string {
  const lines = [
    `Biggest victories:`,
  ];
  for (let i = 0; i < summary.biggestWins.length; i++) {
    lines.push(`${i + 1}. ${formatMatch(summary.biggestWins[i])}`);
  }
  lines.push('');
  lines.push(`Average goals per match: ${summary.averageGoalsPerMatch.toFixed(2)}`);
  lines.push(`Home win rate: ${(summary.homeWinRate * 100).toFixed(1)}%`);
  lines.push(`Away win rate: ${(summary.awayWinRate * 100).toFixed(1)}%`);
  lines.push(`Draw rate: ${(summary.drawRate * 100).toFixed(1)}%`);
  return lines.join('\n');
}
