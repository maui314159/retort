/**
 * Format store results as natural-language text for MCP tool responses.
 */

import type { HeadToHead, Match, Player, TeamRecord } from "./types.js";

function formatDate(date: Date | null): string {
  if (!date) return "Unknown date";
  return date.toISOString().slice(0, 10);
}

function formatMatchLine(m: Match): string {
  const round = m.round ? ` (${m.competition} ${m.round})` : ` (${m.competition})`;
  return `- ${formatDate(m.date)}: ${m.homeTeam} ${m.homeGoals ?? "?"}-${m.awayGoals ?? "?"} ${m.awayTeam}${round}`;
}

export function formatMatchList(matches: Match[], title?: string): string {
  if (matches.length === 0) return title ? `${title}\nNo matches found.` : "No matches found.";
  const lines = title ? [title] : [];
  for (const m of matches.slice(0, 25)) {
    lines.push(formatMatchLine(m));
  }
  if (matches.length > 25) {
    lines.push(`... (${matches.length - 25} more matches in dataset)`);
  }
  return lines.join("\n");
}

export function formatHeadToHead(h2h: HeadToHead): string {
  const lines: string[] = [
    `${h2h.teamA} vs ${h2h.teamB}:`,
  ];
  for (const m of h2h.matches.slice(0, 15)) {
    lines.push(formatMatchLine(m));
  }
  if (h2h.matches.length > 15) {
    lines.push(`... (${h2h.matches.length - 15} more matches in dataset)`);
  }
  lines.push(
    ``,
    `Head-to-head in dataset: ${h2h.teamA} ${h2h.winsA} wins, ${h2h.teamB} ${h2h.winsB} wins, ${h2h.draws} draws`
  );
  return lines.join("\n");
}

export function formatTeamRecord(record: TeamRecord, label?: string): string {
  const winRate = record.matches > 0 ? ((record.wins / record.matches) * 100).toFixed(1) : "0.0";
  const lines = [
    label ?? `${record.team} record:`,
    `- Matches: ${record.matches}`,
    `- Wins: ${record.wins}, Draws: ${record.draws}, Losses: ${record.losses}`,
    `- Goals For: ${record.goalsFor}, Goals Against: ${record.goalsAgainst}`,
    `- Win rate: ${winRate}%`,
  ];
  return lines.join("\n");
}

export function formatStandings(standings: TeamRecord[], title?: string): string {
  if (standings.length === 0) return title ? `${title}\nNo standings available.` : "No standings available.";
  const lines = title ? [title] : [];
  for (let i = 0; i < standings.length; i++) {
    const s = standings[i];
    const tag = i === 0 ? " - Champion" : "";
    lines.push(
      `${i + 1}. ${s.team} - ${s.points} pts (${s.wins}W, ${s.draws}D, ${s.losses}L)${tag}`
    );
  }
  return lines.join("\n");
}

export function formatPlayerList(players: Player[], title?: string): string {
  if (players.length === 0) return title ? `${title}\nNo players found.` : "No players found.";
  const lines = title ? [title] : [];
  for (let i = 0; i < players.length; i++) {
    const p = players[i];
    lines.push(
      `${i + 1}. ${p.name} - Overall: ${p.overall ?? "?"}, Position: ${p.position ?? "?"}, Club: ${p.club ?? "?"}`
    );
  }
  return lines.join("\n");
}

export function formatBiggestWins(matches: Match[], title?: string): string {
  if (matches.length === 0) return title ? `${title}\nNo results found.` : "No results found.";
  const lines = title ? [title] : [];
  for (let i = 0; i < matches.length; i++) {
    const m = matches[i];
    lines.push(`${i + 1}. ${formatMatchLine(m)}`);
  }
  return lines.join("\n");
}

export function formatAverageGoals(average: number, label?: string): string {
  return `${label ?? "Average goals per match"}: ${average.toFixed(2)}`;
}
