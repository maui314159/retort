/**
 * Human-readable formatters matching the example answer formats in the spec.
 */

import type { Match, Player, StandingRow, TeamRecord } from "./types.js";

export function formatMatchLine(m: Match): string {
  const score =
    m.homeGoals !== null && m.awayGoals !== null
      ? `${m.homeGoals}-${m.awayGoals}`
      : "vs";
  const ctx = [m.competition, m.round ? `Round ${m.round}` : null, m.stage]
    .filter(Boolean)
    .join(" ");
  return `- ${m.date ?? "unknown date"}: ${m.homeTeam} ${score} ${m.awayTeam} (${ctx})`;
}

export function formatMatchList(matches: Match[], total?: number): string {
  const shown = matches.slice(0, 15).map(formatMatchLine).join("\n");
  const extra =
    total !== undefined && total > matches.length
      ? `\n- ... (${total - matches.length} more matches in dataset)`
      : total !== undefined && matches.length < total
        ? `\n- ... (${total - matches.length} more matches in dataset)`
        : "";
  return shown + extra;
}

export function formatTeamRecord(
  label: string,
  rec: TeamRecord,
): string {
  const winRate = rec.matches ? ((rec.wins / rec.matches) * 100).toFixed(1) : "0.0";
  return [
    `${label}:`,
    `- Matches: ${rec.matches}`,
    `- Wins: ${rec.wins}, Draws: ${rec.draws}, Losses: ${rec.losses}`,
    `- Goals For: ${rec.goalsFor}, Goals Against: ${rec.goalsAgainst}`,
    `- Win rate: ${winRate}%`,
  ].join("\n");
}

export function formatStandings(rows: StandingRow[], title: string): string {
  const lines = rows.map((r, i) => {
    const suffix = i === 0 ? " - Champion" : "";
    return `${i + 1}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L) GD ${r.goalDifference}${suffix}`;
  });
  return `${title} (calculated from matches):\n${lines.join("\n")}`;
}

export function formatPlayer(p: Player): string {
  return `${p.name} - Overall: ${p.overall ?? "?"}, Position: ${p.position || "?"}, Club: ${p.club || "?"}, Nationality: ${p.nationality}, Age: ${p.age ?? "?"}`;
}

export function formatPlayerList(players: Player[]): string {
  return players.map((p, i) => `${i + 1}. ${formatPlayer(p)}`).join("\n");
}
