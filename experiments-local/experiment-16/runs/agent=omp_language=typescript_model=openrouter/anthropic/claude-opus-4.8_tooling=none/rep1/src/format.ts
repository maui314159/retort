/**
 * Context
 * -------
 * Human-readable formatters that turn query results into the text blocks the
 * spec illustrates (match lists, team records, standings tables, player lists,
 * head-to-head summaries). The MCP tools return these strings as their primary
 * text content so an LLM client gets ready-to-present prose, while also
 * returning structured JSON for programmatic clients.
 */

import type {
  GoalsSummary,
  HeadToHead,
  StandingRow,
  TeamStats,
} from "./queries.js";
import type { Match, Player, TeamRecord } from "./types.js";

function scoreLine(m: Match): string {
  const date = m.date ?? m.dateRaw ?? "unknown date";
  const hg = m.homeGoal ?? "?";
  const ag = m.awayGoal ?? "?";
  const round = m.round ? ` ${m.competition} ${roundLabel(m.round)}` : ` ${m.competition}`;
  return `${date}: ${m.homeTeam} ${hg}-${ag} ${m.awayTeam} (${round.trim()})`;
}

function roundLabel(round: string): string {
  return /^\d+$/.test(round) ? `Round ${round}` : round;
}

/** Format a list of matches, capping the visible rows. */
export function formatMatches(matches: Match[], limit = 20): string {
  if (matches.length === 0) return "No matches found.";
  const shown = matches.slice(0, limit).map((m) => `- ${scoreLine(m)}`);
  let out = shown.join("\n");
  if (matches.length > limit) {
    out += `\n- ... (${matches.length - limit} more matches in dataset)`;
  }
  return out;
}

function recordLine(label: string, r: TeamRecord): string {
  const winRate = r.matches === 0 ? 0 : (r.wins / r.matches) * 100;
  return [
    `${label}:`,
    `  Matches: ${r.matches}`,
    `  Wins: ${r.wins}, Draws: ${r.draws}, Losses: ${r.losses}`,
    `  Goals For: ${r.goalsFor}, Goals Against: ${r.goalsAgainst}`,
    `  Win rate: ${winRate.toFixed(1)}%`,
  ].join("\n");
}

/** Format a team's overall/home/away record. */
export function formatTeamStats(stats: TeamStats, scope: string): string {
  return [
    `${stats.team} record (${scope}):`,
    recordLine("Overall", stats.overall),
    recordLine("Home", stats.home),
    recordLine("Away", stats.away),
  ].join("\n");
}

/** Format a head-to-head summary plus recent meetings. */
export function formatHeadToHead(h: HeadToHead, limit = 10): string {
  const header = `${h.teamA} vs ${h.teamB} head-to-head (${h.matches.length} matches in dataset):`;
  const summary = `${h.teamA} ${h.aWins} wins, ${h.teamB} ${h.bWins} wins, ${h.draws} draws (goals ${h.aGoals}-${h.bGoals})`;
  if (h.matches.length === 0) return `${header}\nNo matches found.`;
  return [header, summary, "", formatMatches(h.matches, limit)].join("\n");
}

/** Format a league standings table. */
export function formatStandings(
  rows: StandingRow[],
  title: string,
  limit = 30,
): string {
  if (rows.length === 0) return `${title}\nNo matches found for this season.`;
  const lines = rows.slice(0, limit).map((r, i) => {
    const champ = i === 0 ? " - Champion" : "";
    return `${i + 1}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L, GD ${r.goalDiff >= 0 ? "+" : ""}${r.goalDiff})${champ}`;
  });
  return [title, ...lines].join("\n");
}

/** Format a list of players. */
export function formatPlayers(players: Player[], limit = 25): string {
  if (players.length === 0) return "No players found.";
  const lines = players.slice(0, limit).map((p, i) => {
    const ovr = p.overall ?? "?";
    return `${i + 1}. ${p.name} - Overall: ${ovr}, Position: ${p.position || "?"}, Club: ${p.club || "?"}`;
  });
  let out = lines.join("\n");
  if (players.length > limit) {
    out += `\n... (${players.length - limit} more players)`;
  }
  return out;
}

/** Format an aggregate goals summary. */
export function formatGoalsSummary(s: GoalsSummary, scope: string): string {
  return [
    `Statistics (${scope}):`,
    `- Matches: ${s.matches} (${s.matchesWithScore} with recorded scores)`,
    `- Total goals: ${s.totalGoals}`,
    `- Average goals per match: ${s.goalsPerMatch.toFixed(2)}`,
    `- Home wins: ${s.homeWins}, Away wins: ${s.awayWins}, Draws: ${s.draws}`,
    `- Home win rate: ${(s.homeWinRate * 100).toFixed(1)}%`,
  ].join("\n");
}
