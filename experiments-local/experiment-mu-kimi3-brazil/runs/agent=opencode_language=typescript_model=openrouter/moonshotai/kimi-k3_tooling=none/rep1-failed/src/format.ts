/**
 * Human-readable formatting for tool responses, matching the answer
 * styles shown in the specification.
 */
import type { Match, Player } from "./types.js";
import type { HeadToHead } from "./services/matches.js";
import type { TeamStats } from "./services/teams.js";
import type { StandingRow } from "./services/competitions.js";

const pct = (x: number) => `${(x * 100).toFixed(1)}%`;
const f2 = (x: number) => x.toFixed(2);

export function formatMatchLine(m: Match): string {
  const ctx = [m.competition, m.round ? `Round ${m.round}` : null, m.stage && m.stage !== "final" ? m.stage : null]
    .filter(Boolean)
    .join(" ");
  return `${m.date ?? "????-??-??"}: ${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam} (${ctx})`;
}

export function formatMatchList(title: string, matches: Match[], total?: number): string {
  if (matches.length === 0) return `${title}\nNo matches found in dataset.`;
  const lines = matches.map((m) => `- ${formatMatchLine(m)}`);
  const extra = total !== undefined && total > matches.length
    ? [`... (${total - matches.length} more matches in dataset)`]
    : [];
  return [`${title}:`, ...lines, ...extra].join("\n");
}

export function formatHeadToHead(h: HeadToHead): string {
  const parts = [
    `${h.teamA} vs ${h.teamB} — head-to-head in dataset:`,
    `Matches: ${h.matches} | ${h.teamA} ${h.winsA} wins, ${h.teamB} ${h.winsB} wins, ${h.draws} draws`,
    `Goals: ${h.teamA} ${h.goalsA}, ${h.teamB} ${h.goalsB}`,
  ];
  if (h.recent.length) {
    parts.push("Most recent meetings:");
    parts.push(...h.recent.map((m) => `- ${formatMatchLine(m)}`));
  }
  return parts.join("\n");
}

function fmtRecord(label: string, r: { matches: number; wins: number; draws: number; losses: number; goalsFor: number; goalsAgainst: number }): string {
  const winRate = r.matches ? r.wins / r.matches : 0;
  return `${label}: ${r.matches} matches | W ${r.wins}, D ${r.draws}, L ${r.losses} | GF ${r.goalsFor}, GA ${r.goalsAgainst} | Win rate ${pct(winRate)}`;
}

export function formatTeamStats(s: TeamStats, scope: string): string {
  const lines = [`${s.team} record (${scope}):`, fmtRecord("Overall", s)];
  lines.push(fmtRecord("Home", s.home));
  lines.push(fmtRecord("Away", s.away));
  if (s.byCompetition.size) {
    lines.push("By competition:");
    for (const [comp, r] of [...s.byCompetition.entries()].sort()) {
      lines.push(`- ${fmtRecord(comp, r)}`);
    }
  }
  return lines.join("\n");
}

export function formatPlayer(p: Player): string {
  const bits = [
    `${p.name}`,
    p.overall !== null ? `Overall: ${p.overall}` : null,
    p.potential !== null ? `Potential: ${p.potential}` : null,
    p.position ? `Position: ${p.position}` : null,
    p.club ? `Club: ${p.club}` : null,
    p.nationality ? `Nation: ${p.nationality}` : null,
    p.age !== null ? `Age: ${p.age}` : null,
    p.jerseyNumber !== null ? `#${p.jerseyNumber}` : null,
  ].filter(Boolean);
  return bits.join(" | ");
}

export function formatPlayerDetail(p: Player): string {
  const lines = [formatPlayer(p)];
  const s = p.skills;
  const skills = [
    s.finishing !== undefined ? `Finishing ${s.finishing}` : null,
    s.dribbling !== undefined ? `Dribbling ${s.dribbling}` : null,
    s.shortPassing !== undefined ? `ShortPass ${s.shortPassing}` : null,
    s.ballControl !== undefined ? `BallControl ${s.ballControl}` : null,
    s.sprintSpeed !== undefined ? `Sprint ${s.sprintSpeed}` : null,
    s.shotPower !== undefined ? `ShotPower ${s.shotPower}` : null,
    s.crossing !== undefined ? `Crossing ${s.crossing}` : null,
    s.longShots !== undefined ? `LongShots ${s.longShots}` : null,
    s.gkDiving !== undefined ? `GKDiving ${s.gkDiving}` : null,
  ].filter(Boolean);
  if (skills.length) lines.push(`Skills: ${skills.join(", ")}`);
  const phys = [p.height, p.weight, p.preferredFoot ? `${p.preferredFoot} foot` : null].filter(Boolean);
  if (phys.length) lines.push(`Physical: ${phys.join(" | ")}`);
  return lines.join("\n");
}

export function formatStandings(title: string, rows: StandingRow[], limit = 20): string {
  if (!rows.length) return `${title}\nNo matches found for this competition/season.`;
  const lines = rows.slice(0, limit).map((r, i) => {
    const tag = i === 0 ? " - Champion" : "";
    return `${r.position}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L) GD ${r.goalDifference >= 0 ? "+" : ""}${r.goalDifference}${tag}`;
  });
  return [`${title} (calculated from matches):`, ...lines].join("\n");
}

export function formatStats(title: string, s: {
  matches: number; totalGoals: number; avgGoalsPerMatch: number;
  homeWinRate: number; drawRate: number; awayWinRate: number;
  avgHomeGoals: number; avgAwayGoals: number;
}): string {
  return [
    `${title}:`,
    `Matches: ${s.matches} | Total goals: ${s.totalGoals}`,
    `Average goals per match: ${f2(s.avgGoalsPerMatch)} (home ${f2(s.avgHomeGoals)}, away ${f2(s.avgAwayGoals)})`,
    `Home win rate: ${pct(s.homeWinRate)} | Draws: ${pct(s.drawRate)} | Away win rate: ${pct(s.awayWinRate)}`,
  ].join("\n");
}
