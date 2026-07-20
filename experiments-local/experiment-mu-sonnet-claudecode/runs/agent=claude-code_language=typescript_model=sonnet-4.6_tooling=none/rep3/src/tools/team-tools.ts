import { getDataStore, teamMatches } from "../data-loader.js";
import type { Match, TeamStats } from "../types.js";

function computeStats(matches: Match[], teamName: string): TeamStats {
  let wins = 0, draws = 0, losses = 0, goalsFor = 0, goalsAgainst = 0;

  for (const m of matches) {
    const isHome = teamMatches(m.homeTeam, teamName);
    const gf = isHome ? m.homeGoals : m.awayGoals;
    const ga = isHome ? m.awayGoals : m.homeGoals;
    goalsFor += gf;
    goalsAgainst += ga;
    if (gf > ga) wins++;
    else if (gf === ga) draws++;
    else losses++;
  }

  return {
    team: teamName,
    matches: matches.length,
    wins,
    draws,
    losses,
    goalsFor,
    goalsAgainst,
    points: wins * 3 + draws,
  };
}

export function getTeamStats(params: {
  team: string;
  competition?: string;
  season?: number;
  homeOnly?: boolean;
  awayOnly?: boolean;
}): string {
  const { matches } = getDataStore();

  let filtered = matches.filter((m) => {
    const isHome = teamMatches(m.homeTeam, params.team);
    const isAway = teamMatches(m.awayTeam, params.team);
    if (!isHome && !isAway) return false;
    if (params.homeOnly && !isHome) return false;
    if (params.awayOnly && !isAway) return false;
    if (params.competition) {
      const comp = params.competition.toLowerCase();
      if (comp.includes("brasileirao") && m.competition !== "brasileirao" && m.competition !== "historical") return false;
      if (comp.includes("copa do brasil") && m.competition !== "copa_do_brasil") return false;
      if (comp.includes("libertadores") && m.competition !== "libertadores") return false;
    }
    if (params.season && m.season !== params.season) return false;
    return true;
  });

  if (filtered.length === 0) {
    return `No matches found for ${params.team} with the given filters.`;
  }

  const stats = computeStats(filtered, params.team);
  const winRate = stats.matches > 0 ? ((stats.wins / stats.matches) * 100).toFixed(1) : "0.0";
  const avgGoalsFor = stats.matches > 0 ? (stats.goalsFor / stats.matches).toFixed(2) : "0.00";
  const avgGoalsAgainst = stats.matches > 0 ? (stats.goalsAgainst / stats.matches).toFixed(2) : "0.00";
  const goalDiff = stats.goalsFor - stats.goalsAgainst;

  const context = [
    params.competition ?? "All competitions",
    params.season ? `Season ${params.season}` : null,
    params.homeOnly ? "Home only" : params.awayOnly ? "Away only" : null,
  ]
    .filter(Boolean)
    .join(", ");

  return [
    `${stats.team} Statistics (${context})`,
    `Matches: ${stats.matches}`,
    `Record: ${stats.wins}W ${stats.draws}D ${stats.losses}L`,
    `Points: ${stats.points}`,
    `Goals For: ${stats.goalsFor} (avg ${avgGoalsFor}/match)`,
    `Goals Against: ${stats.goalsAgainst} (avg ${avgGoalsAgainst}/match)`,
    `Goal Difference: ${goalDiff >= 0 ? "+" : ""}${goalDiff}`,
    `Win Rate: ${winRate}%`,
  ].join("\n");
}

export function getStandings(params: { season: number; competition?: string }): string {
  const { matches } = getDataStore();

  let filtered = matches.filter((m) => {
    if (m.season !== params.season) return false;
    if (params.competition) {
      const comp = params.competition.toLowerCase();
      if (comp.includes("brasileirao") || comp.includes("serie a")) {
        if (m.competition !== "brasileirao" && m.competition !== "historical") return false;
      } else if (comp.includes("copa do brasil")) {
        if (m.competition !== "copa_do_brasil") return false;
      } else if (comp.includes("libertadores")) {
        if (m.competition !== "libertadores") return false;
      }
    } else {
      // Default to league matches
      if (m.competition !== "brasileirao" && m.competition !== "historical") return false;
    }
    return true;
  });

  if (filtered.length === 0) {
    return `No matches found for season ${params.season}.`;
  }

  const teamMap = new Map<string, { matches: Match[]; name: string }>();

  for (const m of filtered) {
    for (const team of [m.homeTeam, m.awayTeam]) {
      const key = team.toLowerCase();
      if (!teamMap.has(key)) teamMap.set(key, { matches: [], name: team });
      teamMap.get(key)!.matches.push(m);
    }
  }

  const table: TeamStats[] = [];
  for (const [, entry] of teamMap) {
    table.push(computeStats(entry.matches, entry.name));
  }

  table.sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    const gdB = b.goalsFor - b.goalsAgainst;
    const gdA = a.goalsFor - a.goalsAgainst;
    if (gdB !== gdA) return gdB - gdA;
    return b.goalsFor - a.goalsFor;
  });

  const compLabel = params.competition ?? "Brasileirão";
  const lines = table.slice(0, 20).map((t, i) => {
    const gd = t.goalsFor - t.goalsAgainst;
    const gdStr = (gd >= 0 ? "+" : "") + gd;
    return `${String(i + 1).padStart(2)}. ${t.team.padEnd(25)} ${String(t.points).padStart(3)} pts | ${t.wins}W ${t.draws}D ${t.losses}L | GF:${t.goalsFor} GA:${t.goalsAgainst} GD:${gdStr}`;
  });

  return [`${compLabel} ${params.season} Standings (calculated from results)`, "=".repeat(70), ...lines].join("\n");
}

export function compareTeams(params: { team1: string; team2: string; season?: number }): string {
  const { matches } = getDataStore();

  const getTeamMatches = (team: string) =>
    matches.filter((m) => {
      const involved = teamMatches(m.homeTeam, team) || teamMatches(m.awayTeam, team);
      if (!involved) return false;
      if (params.season && m.season !== params.season) return false;
      if (m.competition !== "brasileirao" && m.competition !== "historical") return false;
      return true;
    });

  const m1 = getTeamMatches(params.team1);
  const m2 = getTeamMatches(params.team2);

  if (m1.length === 0 && m2.length === 0) {
    return `No data found for either ${params.team1} or ${params.team2}.`;
  }

  const s1 = computeStats(m1, params.team1);
  const s2 = computeStats(m2, params.team2);

  const seasonStr = params.season ? ` (${params.season})` : "";

  const formatRow = (label: string, v1: string | number, v2: string | number) =>
    `${label.padEnd(20)} ${String(v1).padStart(10)}   ${String(v2).padStart(10)}`;

  return [
    `Team Comparison${seasonStr}`,
    formatRow("", params.team1, params.team2),
    "-".repeat(45),
    formatRow("Matches", s1.matches, s2.matches),
    formatRow("Points", s1.points, s2.points),
    formatRow("Wins", s1.wins, s2.wins),
    formatRow("Draws", s1.draws, s2.draws),
    formatRow("Losses", s1.losses, s2.losses),
    formatRow("Goals For", s1.goalsFor, s2.goalsFor),
    formatRow("Goals Against", s1.goalsAgainst, s2.goalsAgainst),
    formatRow(
      "Goal Diff",
      (s1.goalsFor - s1.goalsAgainst >= 0 ? "+" : "") + (s1.goalsFor - s1.goalsAgainst),
      (s2.goalsFor - s2.goalsAgainst >= 0 ? "+" : "") + (s2.goalsFor - s2.goalsAgainst)
    ),
    formatRow("Win Rate", s1.matches > 0 ? `${((s1.wins / s1.matches) * 100).toFixed(1)}%` : "0%", s2.matches > 0 ? `${((s2.wins / s2.matches) * 100).toFixed(1)}%` : "0%"),
  ].join("\n");
}

export function getBestHomeRecord(params: { season?: number; competition?: string; limit?: number }): string {
  const { matches } = getDataStore();
  const limit = params.limit ?? 10;

  const filtered = matches.filter((m) => {
    if (params.season && m.season !== params.season) return false;
    if (params.competition) {
      const comp = params.competition.toLowerCase();
      if ((comp.includes("brasileirao") || comp.includes("serie a")) && m.competition !== "brasileirao" && m.competition !== "historical") return false;
    } else {
      if (m.competition !== "brasileirao" && m.competition !== "historical") return false;
    }
    return true;
  });

  const homeMap = new Map<string, { wins: number; draws: number; losses: number; matches: number }>();
  for (const m of filtered) {
    const key = m.homeTeam.toLowerCase();
    if (!homeMap.has(key)) homeMap.set(key, { wins: 0, draws: 0, losses: 0, matches: 0, name: m.homeTeam } as any);
    const entry = homeMap.get(key)!;
    entry.matches++;
    if (m.homeGoals > m.awayGoals) entry.wins++;
    else if (m.homeGoals === m.awayGoals) entry.draws++;
    else entry.losses++;
  }

  const teams = Array.from(homeMap.entries())
    .map(([, v]) => v as any)
    .filter((v) => v.matches >= 5)
    .sort((a, b) => {
      const rateB = b.wins / b.matches;
      const rateA = a.wins / a.matches;
      return rateB - rateA;
    });

  const seasonStr = params.season ? ` (${params.season})` : "";
  const lines = teams.slice(0, limit).map((t, i) => {
    const rate = ((t.wins / t.matches) * 100).toFixed(1);
    return `${i + 1}. ${t.name}: ${t.wins}W ${t.draws}D ${t.losses}L (${rate}% win rate, ${t.matches} home matches)`;
  });

  return [`Best Home Records${seasonStr}`, ...lines].join("\n");
}
