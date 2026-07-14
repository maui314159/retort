/**
 * Context
 * -------
 * Human-readable formatting for query results, matching the answer shapes shown
 * in the spec (match lists with "Home X-Y Away (Competition Round N)", team
 * records with win rate, ranked player lists, league standings, stat blocks).
 *
 * Keeping formatting separate from `service.ts` means queries return structured
 * data (reusable by tests) while these functions own the presentation.
 */

import type { Match, Player } from "./models.js";
import type { CompetitionStats, StandingRow } from "./service.js";

/** Round/stage suffix for a match line, e.g. " Round 22" or " group stage". */
function context(m: Match): string {
  if (m.stage) return ` ${m.stage}`;
  if (m.round) return /^\d+$/.test(m.round) ? ` Round ${m.round}` : ` ${m.round}`;
  return "";
}

/** One match as a bullet line: "- 2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A Round 22)". */
export function formatMatchLine(m: Match): string {
  const date = m.date?.iso ?? "date unknown";
  const home = m.home.displayBase;
  const away = m.away.displayBase;
  return `- ${date}: ${home} ${m.homeGoals}-${m.awayGoals} ${away} (${m.competition}${context(m)})`;
}

/** A list of matches with a header and an optional truncation note. */
export function formatMatchList(title: string, matches: Match[], shown: Match[]): string {
  if (matches.length === 0) return `${title}\nNo matches found in the dataset.`;
  const lines = shown.map(formatMatchLine);
  const extra = matches.length - shown.length;
  const more = extra > 0 ? `\n- ... (${extra} more ${extra === 1 ? "match" : "matches"} in dataset)` : "";
  return `${title} (${matches.length} ${matches.length === 1 ? "match" : "matches"}):\n${lines.join("\n")}${more}`;
}

/** Head-to-head summary line. */
export function formatHeadToHead(
  teamA: string,
  teamB: string,
  h2h: { aWins: number; bWins: number; draws: number; aGoals: number; bGoals: number; matches: Match[] },
): string {
  return [
    `Head-to-head in dataset (${h2h.matches.length} ${h2h.matches.length === 1 ? "match" : "matches"}):`,
    `${teamA} ${h2h.aWins} wins, ${teamB} ${h2h.bWins} wins, ${h2h.draws} draws`,
    `Goals: ${teamA} ${h2h.aGoals}, ${teamB} ${h2h.bGoals}`,
  ].join("\n");
}

/** Team record block with win rate. */
export function formatTeamRecord(
  title: string,
  r: { matches: number; wins: number; draws: number; losses: number; goalsFor: number; goalsAgainst: number },
): string {
  const winRate = r.matches ? ((r.wins / r.matches) * 100).toFixed(1) : "0.0";
  return [
    `${title}:`,
    `- Matches: ${r.matches}`,
    `- Wins: ${r.wins}, Draws: ${r.draws}, Losses: ${r.losses}`,
    `- Goals For: ${r.goalsFor}, Goals Against: ${r.goalsAgainst}`,
    `- Win rate: ${winRate}%`,
  ].join("\n");
}

/** Ranked player list. */
export function formatPlayers(title: string, players: Player[], total: number): string {
  if (players.length === 0) return `${title}\nNo players found in the dataset.`;
  const lines = players.map((p, i) => {
    const overall = p.overall ?? "?";
    const pos = p.position || "?";
    const club = p.club || "Unattached";
    return `${i + 1}. ${p.name} - Overall: ${overall}, Position: ${pos}, Club: ${club}`;
  });
  const note = total > players.length ? `\n... (${total} players total in dataset)` : "";
  return `${title} (${total} total):\n${lines.join("\n")}${note}`;
}

/** League standings table. */
export function formatStandings(title: string, rows: StandingRow[]): string {
  if (rows.length === 0) return `${title}\nNo data for that competition/season.`;
  const lines = rows.map((r, i) => {
    const champ = i === 0 ? " - Champion" : "";
    return `${i + 1}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L) GF:${r.goalsFor} GA:${r.goalsAgainst}${champ}`;
  });
  return `${title}:\n${lines.join("\n")}`;
}

/** Aggregate competition stats block. */
export function formatStats(s: CompetitionStats): string {
  const scope = s.season !== undefined ? `${s.competition} ${s.season}` : `${s.competition} (all seasons)`;
  return [
    `${scope} statistics:`,
    `- Matches: ${s.matches}`,
    `- Total goals: ${s.totalGoals}`,
    `- Average goals per match: ${s.goalsPerMatch.toFixed(2)}`,
    `- Home wins: ${s.homeWins}, Away wins: ${s.awayWins}, Draws: ${s.draws}`,
    `- Home win rate: ${(s.homeWinRate * 100).toFixed(1)}%`,
  ].join("\n");
}
