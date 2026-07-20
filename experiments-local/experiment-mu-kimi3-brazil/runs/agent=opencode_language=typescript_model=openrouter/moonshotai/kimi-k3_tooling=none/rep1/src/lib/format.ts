/**
 * Response formatters — render query results in the answer styles
 * shown in the specification examples.
 */
import { Match, Player, Team } from "./types.js";
import { BigWin, CompetitionStats, HeadToHead, StandingRow, TeamRecord } from "./queries.js";

export function teamLabel(t: Team): string {
  return t.uf ? `${t.name}-${t.uf}` : t.name;
}

export function formatMatchLine(m: Match): string {
  const score =
    m.homeGoals !== null && m.awayGoals !== null
      ? `${m.homeGoals}-${m.awayGoals}`
      : "vs (not played)";
  let compLabel: string;
  if (m.competition === "Copa Libertadores") {
    compLabel = m.round ? ` (${m.competition}, ${m.round})` : ` (${m.competition})`;
  } else if (m.round) {
    compLabel = ` (${m.competition} Round ${m.round})`;
  } else {
    compLabel = ` (${m.competition})`;
  }
  return `- ${m.date ?? "unknown date"}: ${teamLabel(m.homeTeam)} ${score} ${teamLabel(m.awayTeam)}${compLabel}`;
}

export function formatMatchList(matches: Match[], limit: number): { lines: string[]; hiddenCount: number } {
  const shown = matches.slice(0, limit);
  return {
    lines: shown.map(formatMatchLine),
    hiddenCount: Math.max(0, matches.length - shown.length),
  };
}

export function formatTeamRecord(team: Team, record: TeamRecord, context: string): string {
  return [
    `${team.name} ${context}:`,
    `- Matches: ${record.matches}`,
    `- Wins: ${record.wins}, Draws: ${record.draws}, Losses: ${record.losses}`,
    `- Goals For: ${record.goalsFor}, Goals Against: ${record.goalsAgainst}`,
    `- Win rate: ${record.winRate.toFixed(1)}%`,
  ].join("\n");
}

export function formatHeadToHead(a: Team, b: Team, h2h: HeadToHead, listLimit = 10): string {
  const { lines, hiddenCount } = formatMatchList(h2h.matches, listLimit);
  const parts = [
    `${a.name} vs ${b.name}:`,
    ...lines,
  ];
  if (hiddenCount > 0) parts.push(`- ... (${hiddenCount} more matches in dataset)`);
  parts.push("");
  parts.push(
    `Head-to-head in dataset: ${a.name} ${h2h.winsA} wins, ${b.name} ${h2h.winsB} wins, ${h2h.draws} draws (goals: ${h2h.goalsA}-${h2h.goalsB})`,
  );
  return parts.join("\n");
}

export function formatStandings(rows: StandingRow[], competition: string, season: number): string {
  const lines = [`${season} ${competition} Standings (calculated from matches):`];
  rows.forEach((r, i) => {
    const tags: string[] = [];
    if (i === 0) tags.push("Champion");
    if (competition.includes("Série A") && i >= rows.length - 4) tags.push("Relegated");
    const tag = tags.length > 0 ? ` - ${tags.join(", ")}` : "";
    lines.push(
      `${i + 1}. ${r.team.name} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L, ${r.goalsFor}-${r.goalsAgainst})${tag}`,
    );
  });
  return lines.join("\n");
}

export function formatPlayer(p: Player, rank?: number): string {
  const prefix = rank !== undefined ? `${rank}. ` : "- ";
  const bits = [
    `Overall: ${p.overall ?? "?"}`,
    p.position ? `Position: ${p.position}` : null,
    p.club ? `Club: ${p.club}` : null,
    p.age !== null ? `Age: ${p.age}` : null,
  ].filter(Boolean);
  return `${prefix}${p.name} - ${bits.join(", ")}`;
}

export function formatCompetitionStats(s: CompetitionStats): string {
  const scope = `${s.competition === "all" ? "All competitions" : s.competition}${s.season ? ` ${s.season}` : ""}`;
  const lines = [
    `${scope} (provided data):`,
    `- Matches played: ${s.matches}`,
    `- Total goals: ${s.totalGoals}`,
    `- Average goals per match: ${s.avgGoalsPerMatch.toFixed(2)}`,
    `- Home win rate: ${s.homeWinRate.toFixed(1)}%`,
    `- Draw rate: ${s.drawRate.toFixed(1)}%`,
    `- Away win rate: ${s.awayWinRate.toFixed(1)}%`,
  ];
  if (s.topScoringTeam) {
    lines.push(`- Most goals scored: ${s.topScoringTeam.team.name} (${s.topScoringTeam.goals})`);
  }
  return lines.join("\n");
}

export function formatBigWins(wins: BigWin[], scope: string): string {
  const lines = [`Biggest victories ${scope}:`];
  wins.forEach((w, i) => {
    const m = w.match;
    lines.push(
      `${i + 1}. ${m.date ?? "unknown date"}: ${teamLabel(m.homeTeam)} ${m.homeGoals}-${m.awayGoals} ${teamLabel(m.awayTeam)} (${m.competition})`,
    );
  });
  return lines.join("\n");
}
