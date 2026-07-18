/**
 * Brazilian Soccer MCP Server — Response Formatting
 * -----------------------------------------------------------------------------
 * Context block:
 *   The spec gives example answer formats (head-to-head summaries, team record
 *   blocks, standings tables, biggest-win lists). This module renders the
 *   structured results from `query.ts` into those human-readable strings.
 *
 *   All formatting is pure and synchronous. The MCP tools call these after
 *   running the query so the returned text is the value the LLM surfaces to the
 *   user. We keep numbers rounded to 1-2 decimals and omit nulls gracefully
 *   (e.g. Libertadores NA-row matches have no scores).
 */

import type {
  ClubBrazilianPlayers,
  HeadToHead,
  Match,
  MatchStatistics,
  Player,
  StandingRow,
  TeamStat,
} from "./types.js";

function round(n: number, dp = 2): number {
  const f = 10 ** dp;
  return Math.round(n * f) / f;
}

function pct(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

function scoreLine(m: Match): string {
  const hg = m.homeGoals != null ? String(m.homeGoals) : "-";
  const ag = m.awayGoals != null ? String(m.awayGoals) : "-";
  return `${m.homeTeam} ${hg}-${ag} ${m.awayTeam}`;
}

function dateShort(m: Match): string {
  return m.date ?? "????-??-??";
}

function competitionTag(m: Match): string {
  const parts: string[] = [m.competitionLabel];
  if (m.season != null) parts.push(String(m.season));
  if (m.round) parts.push(`Round ${m.round}`);
  if (m.stage) parts.push(m.stage);
  return parts.join(" ");
}

/** Format a head-to-head summary. */
export function formatHeadToHead(h2h: HeadToHead): string {
  const lines: string[] = [];
  lines.push(`${h2h.team1} vs ${h2h.team2} (head-to-head in dataset):`);
  const shown = h2h.matches.slice(0, 5);
  for (const m of shown) {
    lines.push(`- ${dateShort(m)}: ${scoreLine(m)} (${competitionTag(m)})`);
  }
  const remaining = h2h.matches.length - shown.length;
  if (remaining > 0) lines.push(`- ... (${remaining} more matches in dataset)`);
  lines.push("");
  lines.push(
    `Head-to-head in dataset: ${h2h.team1} ${h2h.team1Wins} wins, ${h2h.team2} ${h2h.team2Wins} wins, ${h2h.draws} draws`,
  );
  return lines.join("\n");
}

/** Format a team statistics block. */
export function formatTeamStats(team: string, stats: TeamStat, scopeLabel = ""): string {
  const lines: string[] = [];
  lines.push(`${team} ${scopeLabel ? `(${scopeLabel})` : ""}:`.trim());
  lines.push(`- Matches: ${stats.played}`);
  lines.push(`- Wins: ${stats.wins}, Draws: ${stats.draws}, Losses: ${stats.losses}`);
  lines.push(`- Goals For: ${stats.goalsFor}, Goals Against: ${stats.goalsAgainst}`);
  lines.push(`- Win rate: ${pct(stats.winRate)}`);
  lines.push(`- Points: ${stats.points}, GD: ${stats.goalDifference >= 0 ? "+" : ""}${stats.goalDifference}`);
  return lines.join("\n");
}

/** Format a standings table. */
export function formatStandings(rows: StandingRow[], title = "Standings"): string {
  const lines: string[] = [`${title}:`, ""];
  lines.push("Pos | Team               | P   | W   | D   | L   | GF  | GA  | GD   | Pts");
  lines.push("----|--------------------|-----|-----|-----|-----|-----|-----|------|----");
  for (const r of rows) {
    lines.push(
      [
        String(r.position).padStart(3),
        r.team.slice(0, 20).padEnd(20),
        String(r.played).padStart(3),
        String(r.wins).padStart(3),
        String(r.draws).padStart(3),
        String(r.losses).padStart(3),
        String(r.goalsFor).padStart(3),
        String(r.goalsAgainst).padStart(3),
        `${r.goalDifference >= 0 ? "+" : ""}${r.goalDifference}`.padStart(5),
        String(r.points).padStart(3),
      ].join(" | "),
    );
  }
  const champ = rows[0];
  if (champ) lines.push("", `Champion: ${champ.team} (${champ.points} pts)`);
  return lines.join("\n");
}

/** Format aggregate match statistics. */
export function formatStatistics(stats: MatchStatistics, title = "Match statistics"): string {
  const lines: string[] = [`${title}:`, ""];
  lines.push(`- Matches: ${stats.matches} (scored: ${stats.scoredMatches})`);
  lines.push(`- Total goals: ${stats.totalGoals}`);
  lines.push(`- Average goals per match: ${round(stats.averageGoals)}`);
  lines.push(`- Home wins: ${stats.homeWins} (${pct(stats.homeWinRate)})`);
  lines.push(`- Away wins: ${stats.awayWins} (${pct(stats.awayWinRate)})`);
  lines.push(`- Draws: ${stats.draws} (${pct(stats.drawRate)})`);
  lines.push(`- Average home goals: ${round(stats.averageHomeGoals)}`);
  lines.push(`- Average away goals: ${round(stats.averageAwayGoals)}`);
  if (stats.biggestHomeWin) {
    lines.push(`- Biggest home win: ${dateShort(stats.biggestHomeWin)} ${scoreLine(stats.biggestHomeWin)}`);
  }
  if (stats.biggestAwayWin) {
    lines.push(`- Biggest away win: ${dateShort(stats.biggestAwayWin)} ${scoreLine(stats.biggestAwayWin)}`);
  }
  return lines.join("\n");
}

/** Format a list of biggest victories. */
export function formatBiggestWins(matches: Match[], title = "Biggest victories"): string {
  const lines: string[] = [`${title}:`];
  matches.forEach((m, i) => {
    lines.push(`${i + 1}. ${dateShort(m)}: ${scoreLine(m)} (${competitionTag(m)})`);
  });
  const scored = matches.filter((m) => m.homeGoals != null && m.awayGoals != null);
  if (scored.length) {
    const total = scored.reduce((s, m) => s + (m.homeGoals ?? 0) + (m.awayGoals ?? 0), 0);
    lines.push("", `Average goals per match: ${round(total / scored.length)}`);
  }
  return lines.join("\n");
}

/** Format a list of matches compactly. */
export function formatMatches(matches: Match[], title = "Matches"): string {
  if (matches.length === 0) return `${title}: none found.`;
  const lines: string[] = [`${title} (${matches.length} found):`];
  const shown = matches.slice(0, 20);
  for (const m of shown) {
    lines.push(`- ${dateShort(m)}: ${scoreLine(m)} (${competitionTag(m)})`);
  }
  const remaining = matches.length - shown.length;
  if (remaining > 0) lines.push(`- ... (${remaining} more matches)`);
  return lines.join("\n");
}

/** Format a ranked player list. */
export function formatPlayers(players: Player[], title = "Players"): string {
  if (players.length === 0) return `${title}: none found.`;
  const lines: string[] = [`${title}:`];
  players.forEach((p, i) => {
    lines.push(
      `${i + 1}. ${p.name} - Overall: ${p.overall ?? "?"}, Position: ${p.position || "?"}, Club: ${p.club || "?"}, Nationality: ${p.nationality || "?"}`,
    );
  });
  return lines.join("\n");
}

/** Format Brazilian players at Brazilian clubs (grouped). */
export function formatClubBrazilianPlayers(groups: ClubBrazilianPlayers[], title = "Brazilian players at Brazilian clubs"): string {
  if (groups.length === 0) return `${title}: none found.`;
  const lines: string[] = [`${title}:`];
  for (const g of groups) {
    lines.push(`- ${g.club}: ${g.count} players (avg rating: ${round(g.averageOverall, 1)})`);
  }
  return lines.join("\n");
}

/** Format a single match for a "last match" lookup. */
export function formatMatch(m: Match, title = "Match"): string {
  const lines: string[] = [`${title}:`];
  lines.push(`- Date: ${dateShort(m)}${m.datetime && m.datetime.length > 10 ? " " + m.datetime.slice(11) : ""}`);
  lines.push(`- Competition: ${competitionTag(m)}`);
  lines.push(`- Score: ${scoreLine(m)}`);
  if (m.stadium) lines.push(`- Stadium: ${m.stadium}`);
  if (m.stage) lines.push(`- Stage: ${m.stage}`);
  return lines.join("\n");
}
