import type {
  HeadToHeadRecord,
  NormalizedMatch,
  PlayerRecord,
  StandingResult,
  TeamStats,
} from "./types.js";

const fmtMatchLine = (m: NormalizedMatch): string => {
  const score = m.homeGoals != null && m.awayGoals != null
    ? `${m.homeGoals}-${m.awayGoals}`
    : "vs";
  const round = m.round ? ` ${m.competitionLabel} Round ${m.round}` : ` ${m.competitionLabel}`;
  const stage = m.stage ? ` (${m.stage})` : "";
  return `- ${m.date}: ${m.homeTeam} ${score} ${m.awayTeam}${round}${stage}`;
};

export const formatMatchList = (
  title: string,
  matches: NormalizedMatch[],
  totalInDataset?: number
): string => {
  if (matches.length === 0) return `${title}\n\nNo matches found in dataset.`;
  const lines = matches.map(fmtMatchLine);
  const shown = lines.length;
  const total = totalInDataset ?? matches.length;
  let suffix = "";
  if (shown < total) {
    const remaining = total - shown;
    suffix = `\n\n... (${remaining} more matches in dataset)`;
  }
  return `${title}\n\n${lines.join("\n")}${suffix}`;
};

export const formatHeadToHead = (h: HeadToHeadRecord): string => {
  if (h.matches === 0) {
    return `Head-to-head: ${h.teamA} vs ${h.teamB}\n\nNo matches found in dataset.`;
  }
  const lines = h.matchesList.map(fmtMatchLine);
  const summary = `Head-to-head in dataset: ${h.teamA} ${h.teamAWins} wins, ${h.teamB} ${h.teamBWins} wins, ${h.draws} draws`;
  return `Head-to-head: ${h.teamA} vs ${h.teamB}\n\n${lines.join("\n")}\n\n${summary}`;
};

export const formatTeamStats = (s: TeamStats): string => {
  const venueLabel = s.venue === "all" ? "overall" : s.venue;
  const seasonLabel = s.season === "All" ? "all seasons" : `season ${s.season}`;
  const compLabel = s.competition === "All" ? "all competitions" : String(s.competition);
  const header = `${s.team} ${venueLabel} record (${seasonLabel} ${compLabel})`;
  if (s.matches === 0) return `${header}\n\nNo matches found in dataset.`;
  return [
    header,
    `- Matches: ${s.matches}`,
    `- Wins: ${s.wins}, Draws: ${s.draws}, Losses: ${s.losses}`,
    `- Goals For: ${s.goalsFor}, Goals Against: ${s.goalsAgainst}`,
    `- Win rate: ${s.winRate}%`,
  ].join("\n");
};

export const formatStanding = (s: StandingResult, limit = 20): string => {
  if (s.rows.length === 0) {
    return `${s.competition} ${s.season} standings\n\nNo matches found in dataset.`;
  }
  const shown = s.rows.slice(0, limit);
  const lines = shown.map((r, i) => {
    const pos = i + 1;
    const tag = pos === 1 ? " - Champion" : "";
    return `${pos}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L)${tag}`;
  });
  const remaining = s.rows.length - shown.length;
  let suffix = "";
  if (remaining > 0) suffix = `\n\n... (${remaining} more teams in dataset)`;
  return `${s.competition} ${s.season} Standings (calculated from matches):\n\n${lines.join("\n")}${suffix}`;
};

export const formatBiggestWins = (matches: NormalizedMatch[], limit = 10): string => {
  if (matches.length === 0) return "Biggest victories: none found.";
  const lines = matches.map((m) => {
    const score = `${m.homeGoals}-${m.awayGoals}`;
    return `- ${m.date}: ${m.homeTeam} ${score} ${m.awayTeam} (${m.competitionLabel})`;
  });
  return `Biggest victories in dataset:\n\n${lines.slice(0, limit).join("\n")}`;
};

export const formatAverageGoals = (data: {
  average: number;
  totalMatches: number;
  totalGoals: number;
  homeWinRate: number;
  drawRate: number;
  awayWinRate: number;
}): string => {
  return [
    `Average goals per match: ${data.average}`,
    `Total matches: ${data.totalMatches}`,
    `Total goals: ${data.totalGoals}`,
    `Home win rate: ${data.homeWinRate}%`,
    `Draw rate: ${data.drawRate}%`,
    `Away win rate: ${data.awayWinRate}%`,
  ].join("\n");
};

export const formatPlayerList = (
  title: string,
  players: PlayerRecord[]
): string => {
  if (players.length === 0) return `${title}\n\nNo players found in dataset.`;
  const lines = players.map((p, i) => {
    return `${i + 1}. ${p.name} - Overall: ${p.overall ?? "n/a"}, Position: ${p.position || "n/a"}, Club: ${p.club || "n/a"}, Nationality: ${p.nationality}`;
  });
  return `${title}\n\n${lines.join("\n")}`;
};

export const formatClubRoster = (
  club: string,
  players: PlayerRecord[]
): string => {
  if (players.length === 0) {
    return `Players at ${club}: none found in dataset.`;
  }
  const avg =
    players.reduce((s, p) => s + (p.overall ?? 0), 0) / players.length;
  return [
    `Players at ${club}:`,
    `- Total in dataset: ${players.length}`,
    `- Average overall rating: ${Number(avg.toFixed(1))}`,
    "",
    ...players.map((p) => `- ${p.name} (${p.position || "n/a"}, OVR ${p.overall ?? "n/a"})`),
  ].join("\n");
};

export const formatLastMatch = (
  teamA: string,
  teamB: string,
  m: NormalizedMatch | null
): string => {
  if (!m) return `No matches found between ${teamA} and ${teamB} in dataset.`;
  const score = m.homeGoals != null && m.awayGoals != null ? `${m.homeGoals}-${m.awayGoals}` : "n/a";
  return [
    `Last match between ${teamA} and ${teamB}:`,
    `- Date: ${m.date}`,
    `- ${m.homeTeam} ${score} ${m.awayTeam}`,
    `- Competition: ${m.competitionLabel}`,
  ].join("\n");
};
