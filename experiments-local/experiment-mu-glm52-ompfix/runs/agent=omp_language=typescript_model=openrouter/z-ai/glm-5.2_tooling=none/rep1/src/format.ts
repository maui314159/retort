/**
 * brazilian-soccer-mcp — response formatters
 *
 * Context block
 * ============
 * See src/types.ts for the top-level project context block.
 *
 * Pure functions turning query-engine results into the human-readable
 * string formats specified in TASK.md (match lists, team records, H2H,
 * standings, biggest wins, player lists). Kept separate from the engine
 * so they are trivially unit-testable and reusable by non-MCP callers.
 */

import type {
  HeadToHead,
  MatchRecord,
  PlayerRecord,
  StandingRow,
  TeamStats,
} from "./types.js";

function fmtScore(m: MatchRecord): string {
  const h = m.homeGoal ?? "?";
  const a = m.awayGoal ?? "?";
  return `${m.homeTeam} ${h}-${a} ${m.awayTeam}`;
}

function fmtDate(m: MatchRecord): string {
  return m.date ?? "unknown date";
}

/** Format a single match line: "2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Round 22)". */
export function formatMatchLine(m: MatchRecord): string {
  const round = m.round ? ` Round ${m.round}` : "";
  return `- ${fmtDate(m)}: ${fmtScore(m)} (${m.competition}${round})`;
}

/** Format a list of matches with a header and a count footer. */
export function formatMatchList(header: string, matches: MatchRecord[]): string {
  const lines = matches.map(formatMatchLine);
  const shown = lines.slice(0, 20);
  const more = matches.length - shown.length;
  const body = shown.join("\n");
  const footer = more > 0 ? `\n... (${more} more matches in dataset)` : "";
  return `${header}:\n${body}${footer}`;
}

/** Format a head-to-head summary. */
export function formatHeadToHead(h2h: HeadToHead): string {
  const body = h2h.matchesList.slice(0, 20).map(formatMatchLine).join("\n");
  const more =
    h2h.matchesList.length > 20
      ? `\n... (${h2h.matchesList.length - 20} more matches in dataset)`
      : "";
  return `${h2h.teamA} vs ${h2h.teamB}:\n${body}${more}\n\nHead-to-head in dataset: ${h2h.teamA} ${h2h.teamAWins} wins, ${h2h.teamB} ${h2h.teamBWins} wins, ${h2h.draws} draws`;
}

/** Format a team's stats record (total + home/away split). */
export function formatTeamStats(
  s: TeamStats,
  label?: string,
): string {
  const title = label ?? `${s.team} record`;
  const rate = s.matches > 0 ? ((s.wins / s.matches) * 100).toFixed(1) : "0.0";
  const lines = [
    `${title}:`,
    `- Matches: ${s.matches}`,
    `- Wins: ${s.wins}, Draws: ${s.draws}, Losses: ${s.losses}`,
    `- Goals For: ${s.goalsFor}, Goals Against: ${s.goalsAgainst}`,
    `- Win rate: ${rate}%`,
    `- Home: ${s.home.matches} (W${s.home.wins} D${s.home.draws} L${s.home.losses}, GF${s.home.goalsFor} GA${s.home.goalsAgainst})`,
    `- Away: ${s.away.matches} (W${s.away.wins} D${s.away.draws} L${s.away.losses}, GF${s.away.goalsFor} GA${s.away.goalsAgainst})`,
  ];
  return lines.join("\n");
}

/** Format a league standings table. */
export function formatStandings(rows: StandingRow[]): string {
  if (rows.length === 0) return "No standings available for that competition/season.";
  const header =
    "Pos | Team | P | W | D | L | GF | GA | GD | Pts";
  const body = rows
    .slice(0, 20)
    .map(
      (r) =>
        `${String(r.position).padStart(3)} | ${r.team} | ${r.played} | ${r.wins} | ${r.draws} | ${r.losses} | ${r.goalsFor} | ${r.goalsAgainst} | ${r.goalDifference >= 0 ? "+" : ""}${r.goalDifference} | ${r.points}`,
    )
    .join("\n");
  const champ = rows.length > 0 ? `\nChampion: ${rows[0].team}` : "";
  return `${header}\n${body}${champ}`;
}

/** Format a list of players. */
export function formatPlayerList(
  header: string,
  players: PlayerRecord[],
): string {
  if (players.length === 0) return `${header}:\n(no players found)`;
  const lines = players.slice(0, 25).map((p, i) => {
    const overall = p.overall ?? "—";
    return `${i + 1}. ${p.name} - Overall: ${overall}, Position: ${p.position}, Club: ${p.club}`;
  });
  const more = players.length > 25 ? `\n... (${players.length - 25} more)` : "";
  return `${header}:\n${lines.join("\n")}${more}`;
}

/** Format biggest victories list. */
export function formatBiggestWins(matches: MatchRecord[]): string {
  if (matches.length === 0) return "No matches found.";
  const lines = matches.map((m, i) => {
    const diff = Math.abs((m.homeGoal ?? 0) - (m.awayGoal ?? 0));
    return `${i + 1}. ${fmtDate(m)}: ${fmtScore(m)} (${m.competition}, +${diff})`;
  });
  return `Biggest victories (provided data):\n${lines.join("\n")}`;
}

/** Format the average-goals summary. */
export function formatAverageGoals(r: {
  matches: number;
  avgGoals: number;
  homeWinRate: number;
  awayWinRate: number;
  drawRate: number;
}): string {
  return [
    `Matches analysed: ${r.matches}`,
    `Average goals per match: ${r.avgGoals.toFixed(2)}`,
    `Home win rate: ${(r.homeWinRate * 100).toFixed(1)}%`,
    `Away win rate: ${(r.awayWinRate * 100).toFixed(1)}%`,
    `Draw rate: ${(r.drawRate * 100).toFixed(1)}%`,
  ].join("\n");
}
