/**
 * Brazilian Soccer MCP Server — Query engine.
 *
 * Context block
 * -------------
 * Pure functions over the loaded `Dataset` that implement the five required
 * query categories from the spec:
 *   1. Match queries   — find matches by team(s), date range, competition, season
 *   2. Team queries     — win/loss/draw records, goals, per-competition splits
 *   3. Player queries   — search by name/nationality/club/position, sort by rating
 *   4. Competition queries — computed standings + champion/relegation
 *   5. Statistical analysis — avg goals, home/away rates, biggest wins, head-to-head
 *
 * Every function is deterministic and side-effect free, which makes them
 * trivially testable (the BDD suite in tests/ exercises them directly).
 */

import type {
  Competition,
  HeadToHead,
  MatchRecord,
  Player,
  StandingRow,
  TeamRecord,
} from "./types.js";
import { toISODate } from "./dates.js";
import type { Dataset } from "./loader.js";
import { computeStandings } from "./loader.js";

/** Filters applied to match queries. */
export interface MatchFilter {
  team?: string;
  opponent?: string;
  competition?: Competition | "all";
  season?: number;
  startDate?: string;
  endDate?: string;
  limit?: number;
}

/** Resolve a raw team name to its canonical display name registered in the dataset. */
export function resolveTeam(ds: Dataset, raw: string): string | null {
  const display = ds.teams.lookup(raw);
  if (display) return display;
  // Fall back: maybe caller already passed a canonical name.
  const key = raw.toLowerCase();
  for (const m of ds.matches) {
    if (m.homeTeam.toLowerCase() === key) return m.homeTeam;
    if (m.awayTeam.toLowerCase() === key) return m.awayTeam;
  }
  return null;
}

/** Outcome of a match from a team's perspective (win/draw/loss). */
function outcomeFor(m: MatchRecord, team: string): "win" | "draw" | "loss" | null {
  if (m.homeGoal === null || m.awayGoal === null) return null;
  const isHome = m.homeTeam === team;
  const isAway = m.awayTeam === team;
  if (!isHome && !isAway) return null;
  const gf = isHome ? m.homeGoal : m.awayGoal;
  const ga = isHome ? m.awayGoal : m.homeGoal;
  if (gf > ga) return "win";
  if (gf < ga) return "loss";
  return "draw";
}


/** Find matches matching the given filter. */
export function findMatches(ds: Dataset, filter: MatchFilter): MatchRecord[] {
  // A team/opponent that cannot be resolved to a known club matches nothing.
  if (filter.team && !resolveTeam(ds, filter.team)) return [];
  if (filter.opponent && !resolveTeam(ds, filter.opponent)) return [];
  const team = filter.team ? resolveTeam(ds, filter.team) : undefined;
  const opponent = filter.opponent ? resolveTeam(ds, filter.opponent) : undefined;
  const start = filter.startDate ? Date.parse(filter.startDate) : null;
  const end = filter.endDate ? Date.parse(filter.endDate) : null;

  let results = ds.matches.filter((m) => {
    if (filter.competition && filter.competition !== "all" && m.competition !== filter.competition) {
      return false;
    }
    if (filter.season !== undefined && m.season !== filter.season) return false;
    if (m.date) {
      const t = m.date.getTime();
      if (start !== null && t < start) return false;
      if (end !== null && t > end) return false;
    } else if (start !== null || end !== null) {
      return false;
    }
    if (team) {
      const involved = m.homeTeam === team || m.awayTeam === team;
      if (!involved) return false;
      if (opponent) {
        const oppInvolved = m.homeTeam === opponent || m.awayTeam === opponent;
        if (!oppInvolved) return false;
        // Ensure the two teams actually play each other in this match.
        if (m.homeTeam === team && m.awayTeam !== opponent) return false;
        if (m.awayTeam === team && m.homeTeam !== opponent) return false;
      }
    } else if (opponent) {
      const oppInvolved = m.homeTeam === opponent || m.awayTeam === opponent;
      if (!oppInvolved) return false;
    }
    return true;
  });

  // Sort by date descending (unknown dates last).
  results = results.sort((a, b) => {
    if (a.date && b.date) return b.date.getTime() - a.date.getTime();
    if (a.date) return -1;
    if (b.date) return 1;
    return 0;
  });

  if (filter.limit !== undefined && filter.limit > 0) {
    results = results.slice(0, filter.limit);
  }
  return results;
}

/** Build a TeamRecord (W/D/L, GF/GA, points) for a team over a match set. */
export function teamRecord(
  matches: MatchRecord[],
  team: string,
  venue?: "home" | "away",
): TeamRecord {
  const rec: TeamRecord = {
    team,
    matches: 0,
    wins: 0,
    draws: 0,
    losses: 0,
    goalsFor: 0,
    goalsAgainst: 0,
    points: 0,
  };
  for (const m of matches) {
    const isHome = m.homeTeam === team;
    const isAway = m.awayTeam === team;
    if (!isHome && !isAway) continue;
    if (venue === "home" && !isHome) continue;
    if (venue === "away" && !isAway) continue;
    if (m.homeGoal === null || m.awayGoal === null) continue;
    rec.matches++;
    const gf = isHome ? m.homeGoal : m.awayGoal;
    const ga = isHome ? m.awayGoal : m.homeGoal;
    rec.goalsFor += gf;
    rec.goalsAgainst += ga;
    const o = outcomeFor(m, team);
    if (o === "win") {
      rec.wins++;
      rec.points += 3;
    } else if (o === "draw") {
      rec.draws++;
      rec.points++;
    } else if (o === "loss") {
      rec.losses++;
    }
  }
  return rec;
}

/** Compute head-to-head summary between two teams. */
export function headToHead(ds: Dataset, teamA: string, teamB: string): HeadToHead {
  const a = resolveTeam(ds, teamA);
  const b = resolveTeam(ds, teamB);
  const h2h: HeadToHead = {
    teamA: a ?? teamA,
    teamB: b ?? teamB,
    matches: 0,
    teamAWins: 0,
    teamBWins: 0,
    draws: 0,
    teamAGoals: 0,
    teamBGoals: 0,
  };
  if (!a || !b) return h2h;
  for (const m of ds.matches) {
    const aHome = m.homeTeam === a && m.awayTeam === b;
    const aAway = m.awayTeam === a && m.homeTeam === b;
    if (!aHome && !aAway) continue;
    if (m.homeGoal === null || m.awayGoal === null) continue;
    h2h.matches++;
    const aG = aHome ? m.homeGoal : m.awayGoal;
    const bG = aHome ? m.awayGoal : m.homeGoal;
    h2h.teamAGoals += aG;
    h2h.teamBGoals += bG;
    if (aG > bG) h2h.teamAWins++;
    else if (aG < bG) h2h.teamBWins++;
    else h2h.draws++;
  }
  return h2h;
}

/** Player search options. */
export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  sortBy?: "overall" | "potential" | "age" | "name";
  limit?: number;
}

/** Search players by name/nationality/club/position. */
export function findPlayers(ds: Dataset, filter: PlayerFilter): Player[] {
  const name = filter.name?.toLowerCase().trim();
  const nat = filter.nationality?.toLowerCase().trim();
  const club = filter.club?.toLowerCase().trim();
  const pos = filter.position?.toLowerCase().trim();
  let results = ds.players.filter((p) => {
    if (name && !p.name.toLowerCase().includes(name)) return false;
    if (nat && !p.nationality.toLowerCase().includes(nat)) return false;
    if (club && !p.club.toLowerCase().includes(club)) return false;
    if (pos && !p.position.toLowerCase().includes(pos)) return false;
    if (filter.minOverall !== undefined && (p.overall ?? 0) < filter.minOverall) return false;
    return true;
  });
  const sortBy = filter.sortBy ?? "overall";
  results = results.sort((a, b) => {
    switch (sortBy) {
      case "overall":
        return (b.overall ?? 0) - (a.overall ?? 0) || a.name.localeCompare(b.name);
      case "potential":
        return (b.potential ?? 0) - (a.potential ?? 0) || a.name.localeCompare(b.name);
      case "age":
        return (a.age ?? 0) - (b.age ?? 0) || a.name.localeCompare(b.name);
      case "name":
        return a.name.localeCompare(b.name);
    }
  });
  if (filter.limit !== undefined && filter.limit > 0) {
    results = results.slice(0, filter.limit);
  }
  return results;
}

/** Standings for a competition season. */
export function standings(
  ds: Dataset,
  competition: Competition | "all",
  season: number | null,
): StandingRow[] {
  return computeStandings(ds.matches, season, competition);
}

/** Aggregate statistics over a set of matches. */
export interface MatchStats {
  matches: number;
  homeWins: number;
  draws: number;
  awayWins: number;
  totalGoals: number;
  avgGoalsPerMatch: number;
  homeWinRate: number;
  awayWinRate: number;
  drawRate: number;
}

/** Compute aggregate match statistics. */
export function matchStats(matches: MatchRecord[]): MatchStats {
  let homeWins = 0,
    draws = 0,
    awayWins = 0,
    totalGoals = 0,
    scored = 0;
  for (const m of matches) {
    if (m.homeGoal === null || m.awayGoal === null) continue;
    scored++;
    totalGoals += m.homeGoal + m.awayGoal;
    if (m.homeGoal > m.awayGoal) homeWins++;
    else if (m.homeGoal < m.awayGoal) awayWins++;
    else draws++;
  }
  return {
    matches: scored,
    homeWins,
    draws,
    awayWins,
    totalGoals,
    avgGoalsPerMatch: scored ? totalGoals / scored : 0,
    homeWinRate: scored ? homeWins / scored : 0,
    awayWinRate: scored ? awayWins / scored : 0,
    drawRate: scored ? draws / scored : 0,
  };
}

/** Biggest victories (by goal difference) in a match set. */
export function biggestWins(matches: MatchRecord[], limit = 10): MatchRecord[] {
  return matches
    .filter((m) => m.homeGoal !== null && m.awayGoal !== null)
    .map((m) => ({ m, diff: Math.abs(m.homeGoal! - m.awayGoal!) }))
    .sort((a, b) => b.diff - a.diff || (b.m.date?.getTime() ?? 0) - (a.m.date?.getTime() ?? 0))
    .slice(0, limit)
    .map((x) => x.m);
}

// ---- Formatting helpers (produce the human-readable answer text) ----

/** Format a single match as a one-line summary. */
export function formatMatch(m: MatchRecord): string {
  const date = toISODate(m.date, m.rawDate);
  const score =
    m.homeGoal !== null && m.awayGoal !== null
      ? `${m.homeGoal}-${m.awayGoal}`
      : "?-?";
  const ctx = [
    m.competition,
    m.round ? `Round ${m.round}` : undefined,
    m.stage,
    m.season !== null ? String(m.season) : undefined,
  ]
    .filter(Boolean)
    .join(" ");
  return `- ${date}: ${m.homeTeam} ${score} ${m.awayTeam} (${ctx})`;
}

/** Format a TeamRecord as a multi-line block. */
export function formatTeamRecord(rec: TeamRecord, label: string): string {
  const winRate = rec.matches ? ((rec.wins / rec.matches) * 100).toFixed(1) : "0.0";
  return [
    `${label}:`,
    `- Matches: ${rec.matches}`,
    `- Wins: ${rec.wins}, Draws: ${rec.draws}, Losses: ${rec.losses}`,
    `- Goals For: ${rec.goalsFor}, Goals Against: ${rec.goalsAgainst}`,
    `- Points: ${rec.points}`,
    `- Win rate: ${winRate}%`,
  ].join("\n");
}

/** Format a head-to-head summary. */
export function formatHeadToHead(h2h: HeadToHead): string {
  return [
    `Head-to-head: ${h2h.teamA} vs ${h2h.teamB}`,
    `- Matches: ${h2h.matches}`,
    `- ${h2h.teamA} wins: ${h2h.teamAWins} (goals: ${h2h.teamAGoals})`,
    `- ${h2h.teamB} wins: ${h2h.teamBWins} (goals: ${h2h.teamBGoals})`,
    `- Draws: ${h2h.draws}`,
  ].join("\n");
}

/** Format standings table. `totalTeams` (defaults to rows.length) controls the
 * relegation-zone marker so truncating the displayed table does not mislabel
 * the champion row. */
export function formatStandings(rows: StandingRow[], title: string, totalTeams: number = rows.length): string {
  const lines = [`${title}:`];
  const relFrom = totalTeams - 4;
  rows.forEach((r, i) => {
    const champ = i === 0 ? " - Champion" : "";
    const rel = i + 1 > relFrom ? " (relegation zone)" : "";
    lines.push(
      `${i + 1}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L) ` +
        `GF:${r.goalsFor} GA:${r.goalsAgainst} GD:${r.goalDifference >= 0 ? "+" : ""}${r.goalDifference}${champ}${rel}`,
    );
  });
  return lines.join("\n");
}

/** Format a player as a one-line summary. */
export function formatPlayer(p: Player): string {
  return `- ${p.name} (OVR ${p.overall ?? "?"}, POT ${p.potential ?? "?"}) — ${p.position || "?"}, ${p.club || "no club"}, ${p.nationality}`;
}
