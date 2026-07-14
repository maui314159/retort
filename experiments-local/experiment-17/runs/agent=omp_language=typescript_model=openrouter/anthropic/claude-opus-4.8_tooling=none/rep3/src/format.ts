/**
 * Context
 * -------
 * Human-readable rendering for the Brazilian Soccer MCP server. The query
 * engine (queries.ts) returns structured data; these functions turn it into the
 * plain-text answer formats shown in the spec (match lists, head-to-head
 * summaries, team records, league standings, player tables, statistics).
 *
 * Rendering is intentionally separated from querying so the same results can be
 * surfaced either as formatted text (MCP tool default) or as raw JSON.
 */

import type {
  AggregateStats,
  ClubSquadSummary,
  HeadToHead,
  StandingRow,
  TeamRecord,
} from "./queries.js";
import type { Match, Player } from "./types.js";

/** Render a single match as "DATE: Home H-A Away (Competition Round)". */
export function formatMatch(m: Match): string {
  const date = m.date ?? "unknown date";
  const score =
    m.homeGoals !== undefined && m.awayGoals !== undefined
      ? `${m.homeGoals}-${m.awayGoals}`
      : "?-?";
  const context: string[] = [m.competition];
  if (m.round) context.push(`Round ${m.round}`);
  if (m.stage) context.push(m.stage);
  if (m.season !== undefined && !m.round) context.push(String(m.season));
  return `${date}: ${m.homeTeam} ${score} ${m.awayTeam} (${context.join(" ")})`;
}

/** Render a list of matches with an optional header and total count. */
export function formatMatchList(matches: Match[], header?: string, total?: number): string {
  if (matches.length === 0) return header ? `${header}\nNo matches found.` : "No matches found.";
  const lines = matches.map((m) => `- ${formatMatch(m)}`);
  const shown = total !== undefined && total > matches.length
    ? `${lines.join("\n")}\n... (${total - matches.length} more in dataset)`
    : lines.join("\n");
  return header ? `${header}\n${shown}` : shown;
}

/** Render a head-to-head summary block. */
export function formatHeadToHead(h: HeadToHead, sample = 10): string {
  if (h.totalMatches === 0) {
    return `No matches found between ${h.teamA} and ${h.teamB} in the dataset.`;
  }
  const header = `${h.teamA} vs ${h.teamB} (head-to-head):`;
  const list = formatMatchList(h.matches.slice(0, sample), undefined, h.totalMatches);
  const summary =
    `Head-to-head in dataset: ${h.teamA} ${h.teamAWins} wins, ` +
    `${h.teamB} ${h.teamBWins} wins, ${h.draws} draws ` +
    `(goals ${h.teamAGoals}-${h.teamBGoals}).`;
  return `${header}\n${list}\n\n${summary}`;
}

/** Render a team's W/D/L record. */
export function formatTeamRecord(rec: TeamRecord, label?: string): string {
  const title = label ?? `${rec.team} record:`;
  return [
    title,
    `- Matches: ${rec.matches}`,
    `- Wins: ${rec.wins}, Draws: ${rec.draws}, Losses: ${rec.losses}`,
    `- Goals For: ${rec.goalsFor}, Goals Against: ${rec.goalsAgainst}`,
    `- Points: ${rec.points}`,
    `- Win rate: ${(rec.winRate * 100).toFixed(1)}%`,
  ].join("\n");
}

/** Render a calculated league table. */
export function formatStandings(rows: StandingRow[], header: string, limit?: number): string {
  if (rows.length === 0) return `${header}\nNo data available.`;
  const shown = typeof limit === "number" ? rows.slice(0, limit) : rows;
  const lines = shown.map((r) => {
    const tag = r.rank === 1 ? " - Champion" : "";
    return `${r.rank}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L)${tag}`;
  });
  return `${header}\n${lines.join("\n")}`;
}

/** Render a single player line. */
export function formatPlayer(p: Player, rank?: number): string {
  const prefix = rank !== undefined ? `${rank}. ` : "";
  const parts = [
    `${prefix}${p.name}`,
    p.overall !== undefined ? `Overall: ${p.overall}` : undefined,
    p.position ? `Position: ${p.position}` : undefined,
    p.club ? `Club: ${p.club}` : undefined,
    `Nationality: ${p.nationality}`,
  ].filter(Boolean);
  return parts.join(" - ");
}

/** Render a list of players. */
export function formatPlayerList(players: Player[], header?: string, total?: number): string {
  if (players.length === 0) {
    return header ? `${header}\nNo players found.` : "No players found.";
  }
  const lines = players.map((p, i) => formatPlayer(p, i + 1));
  const shown = total !== undefined && total > players.length
    ? `${lines.join("\n")}\n... (${total - players.length} more in dataset)`
    : lines.join("\n");
  return header ? `${header}\n${shown}` : shown;
}

/** Render club squad summaries (e.g. Brazilian players by club). */
export function formatClubSquads(rows: ClubSquadSummary[], header: string): string {
  if (rows.length === 0) return `${header}\nNo data available.`;
  const lines = rows.map(
    (r) => `- ${r.club}: ${r.playerCount} players (avg rating: ${r.averageOverall.toFixed(0)})`
  );
  return `${header}\n${lines.join("\n")}`;
}

/** Render aggregate match statistics. */
export function formatAggregateStats(s: AggregateStats, header: string): string {
  return [
    header,
    `- Matches analysed: ${s.matches}`,
    `- Total goals: ${s.totalGoals}`,
    `- Average goals per match: ${s.averageGoals.toFixed(2)}`,
    `- Home win rate: ${(s.homeWinRate * 100).toFixed(1)}%`,
    `- Away win rate: ${(s.awayWinRate * 100).toFixed(1)}%`,
    `- Draw rate: ${(s.drawRate * 100).toFixed(1)}%`,
  ].join("\n");
}
