/**
 * Brazilian Soccer MCP Server — Tool Implementations
 *
 * Each function implements one MCP tool's business logic.
 * All tools return { content: [{ type: "text", text: string }] }.
 */

import type { SoccerData, NormalizedMatch, HeadToHead, TeamStats, Standing } from "./types.js";
import { lookupTeam, buildKnownTeams, normalizeTeamName } from "./types.js";

function formatMatch(m: NormalizedMatch, i?: number): string {
  const prefix = i !== undefined ? `${i + 1}. ` : "- ";
  return `${prefix}${m.date}: ${m.homeTeam} ${m.homeGoal}-${m.awayGoal} ${m.awayTeam} (${m.competition}${m.round ? ` ${m.round}` : ""})`;
}

// ─── Match Search ────────────────────────────────────────────────────────────

export interface SearchMatchesArgs {
  team?: string;
  opponent?: string;
  competition?: string;
  season?: number;
  dateFrom?: string;
  dateTo?: string;
  limit?: number;
}

export function searchMatches(data: SoccerData, args: SearchMatchesArgs) {
  const { team, opponent, competition, season, dateFrom, dateTo, limit = 50 } = args;
  const knownTeams = team ? buildKnownTeams(data.matches) : new Set<string>();
  const resolvedTeam = team ? lookupTeam(team, knownTeams) : undefined;
  // Always normalize opponent too — it might be a team name
  const knownOpponents = opponent ? buildKnownTeams(data.matches) : new Set<string>();
  const resolvedOpponent = opponent ? lookupTeam(opponent, knownOpponents) : undefined;

  let results = data.matches;

  if (resolvedTeam) {
    const t = resolvedTeam.toLowerCase();
    results = results.filter(
      (m) => m.homeTeam.toLowerCase() === t || m.awayTeam.toLowerCase() === t,
    );
  } else if (team) {
    // Fallback: fuzzy match
    const tn = normalizeTeamName(team).toLowerCase();
    results = results.filter(
      (m) =>
        normalizeTeamName(m.homeTeam).toLowerCase().includes(tn) ||
        normalizeTeamName(m.awayTeam).toLowerCase().includes(tn),
    );
  }

  if (resolvedOpponent) {
    const o = resolvedOpponent.toLowerCase();
    results = results.filter(
      (m) =>
        (m.homeTeam.toLowerCase() === o && m.awayTeam.toLowerCase() === (resolvedTeam?.toLowerCase() || "")) ||
        (m.awayTeam.toLowerCase() === o && m.homeTeam.toLowerCase() === (resolvedTeam?.toLowerCase() || "")),
    );
  }

  if (competition) {
    const c = competition.toLowerCase();
    results = results.filter((m) => m.competition.toLowerCase().includes(c));
  }

  if (season) {
    results = results.filter((m) => m.season === season);
  }

  if (dateFrom) {
    results = results.filter((m) => m.date >= dateFrom);
  }

  if (dateTo) {
    results = results.filter((m) => m.date <= dateTo);
  }

  // Sort by date descending
  results.sort((a, b) => b.date.localeCompare(a.date) || a.homeTeam.localeCompare(b.homeTeam));

  const total = results.length;
  results = results.slice(0, limit);

  const lines: string[] = [];
  const what = resolvedTeam || team || "all teams";
  if (opponent) lines.push(`Matches between ${what} and ${opponent}:`);
  else lines.push(`Matches for ${what}:`);

  if (results.length === 0) {
    lines.push("No matches found.");
  } else {
    results.forEach((m, i) => lines.push(formatMatch(m, i)));
    if (total > limit) {
      lines.push(`... and ${total - limit} more matches (limit=${limit})`);
    }
  }

  return { content: [{ type: "text" as const, text: lines.join("\n") }] };
}

// ─── Player Search ───────────────────────────────────────────────────────────

export interface SearchPlayersArgs {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  maxOverall?: number;
  limit?: number;
}

export function searchPlayers(data: SoccerData, args: SearchPlayersArgs) {
  const { name, nationality, club, position, minOverall, maxOverall, limit = 50 } = args;

  let results = data.players;

  if (name) {
    const n = name.toLowerCase();
    results = results.filter((p) => p.name.toLowerCase().includes(n));
  }

  if (nationality) {
    const nat = nationality.toLowerCase();
    results = results.filter((p) => p.nationality.toLowerCase().includes(nat));
  }

  if (club) {
    const c = club.toLowerCase();
    results = results.filter((p) => p.club.toLowerCase().includes(c));
  }

  if (position) {
    const pos = position.toUpperCase();
    results = results.filter((p) => p.position.toUpperCase().includes(pos));
  }

  if (minOverall !== undefined) {
    results = results.filter((p) => p.overall >= minOverall);
  }

  if (maxOverall !== undefined) {
    results = results.filter((p) => p.overall <= maxOverall);
  }

  // Sort by overall rating descending
  results.sort((a, b) => b.overall - a.overall || a.name.localeCompare(b.name));

  const total = results.length;
  results = results.slice(0, limit);

  const lines: string[] = [];
  const criteria: string[] = [];
  if (name) criteria.push(`name="${name}"`);
  if (nationality) criteria.push(`nationality="${nationality}"`);
  if (club) criteria.push(`club="${club}"`);
  if (position) criteria.push(`position="${position}"`);

  lines.push(`Players${criteria.length ? " matching " + criteria.join(", ") : ""}:`);

  if (results.length === 0) {
    lines.push("No players found.");
  } else {
    results.forEach((p, i) => {
      lines.push(
        `${i + 1}. ${p.name} - Overall: ${p.overall}, Position: ${p.position}, Club: ${p.club}, Nationality: ${p.nationality}, Age: ${p.age}`,
      );
    });
    if (total > limit) {
      lines.push(`... and ${total - limit} more players (limit=${limit})`);
    }
  }

  return { content: [{ type: "text" as const, text: lines.join("\n") }] };
}

// ─── Team Stats ──────────────────────────────────────────────────────────────

export interface GetTeamStatsArgs {
  team: string;
  competition?: string;
  season?: number;
  homeOnly?: boolean;
}

export function getTeamStats(data: SoccerData, args: GetTeamStatsArgs) {
  const { team, competition, season, homeOnly } = args;
  const knownTeams = buildKnownTeams(data.matches);
  const resolved = lookupTeam(team, knownTeams);
  const teamName = resolved || team;

  let matches = data.matches;
  const tn = resolved ? resolved.toLowerCase() : normalizeTeamName(team).toLowerCase();

  if (homeOnly) {
    matches = matches.filter((m) => m.homeTeam.toLowerCase() === tn);
  } else {
    matches = matches.filter(
      (m) => m.homeTeam.toLowerCase() === tn || m.awayTeam.toLowerCase() === tn,
    );
  }

  if (competition) {
    const c = competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(c));
  }

  if (season) {
    matches = matches.filter((m) => m.season === season);
  }

  const stats: TeamStats = {
    team: resolved || team,
    matches: matches.length,
    wins: 0,
    draws: 0,
    losses: 0,
    goalsFor: 0,
    goalsAgainst: 0,
    winRate: 0,
  };

  for (const m of matches) {
    const isHome = m.homeTeam.toLowerCase() === tn;
    const gf = isHome ? m.homeGoal : m.awayGoal;
    const ga = isHome ? m.awayGoal : m.homeGoal;

    stats.goalsFor += gf;
    stats.goalsAgainst += ga;

    if (gf > ga) stats.wins++;
    else if (gf === ga) stats.draws++;
    else stats.losses++;
  }

  if (stats.matches > 0) {
    stats.winRate = Math.round((stats.wins / stats.matches) * 1000) / 10;
  }

  const venue = homeOnly ? "home" : "overall";
  const filterStr = [competition && `${competition}`, season && `${season} season`]
    .filter(Boolean)
    .join(" ");

  const lines: string[] = [
    `${teamName} ${venue} record${filterStr ? ` (${filterStr})` : ""}:`,
    `- Matches: ${stats.matches}`,
    `- Wins: ${stats.wins}, Draws: ${stats.draws}, Losses: ${stats.losses}`,
    `- Goals For: ${stats.goalsFor}, Goals Against: ${stats.goalsAgainst}`,
    `- Win rate: ${stats.winRate}%`,
  ];

  return { content: [{ type: "text" as const, text: lines.join("\n") }] };
}

// ─── Head to Head ────────────────────────────────────────────────────────────

export interface HeadToHeadArgs {
  teamA: string;
  teamB: string;
}

export function headToHead(data: SoccerData, args: HeadToHeadArgs) {
  const { teamA, teamB } = args;
  const knownTeams = buildKnownTeams(data.matches);
  const resolvedA = lookupTeam(teamA, knownTeams) || teamA;
  const resolvedB = lookupTeam(teamB, knownTeams) || teamB;

  const ta = resolvedA.toLowerCase();
  const tb = resolvedB.toLowerCase();

  const matches = data.matches.filter(
    (m) =>
      (m.homeTeam.toLowerCase() === ta && m.awayTeam.toLowerCase() === tb) ||
      (m.homeTeam.toLowerCase() === tb && m.awayTeam.toLowerCase() === ta),
  );

  matches.sort((a, b) => b.date.localeCompare(a.date));

  const result: HeadToHead = {
    teamA: resolvedA,
    teamB: resolvedB,
    matches,
    teamAWins: 0,
    teamBWins: 0,
    draws: 0,
  };

  for (const m of matches) {
    const aIsHome = m.homeTeam.toLowerCase() === ta;
    const aGoals = aIsHome ? m.homeGoal : m.awayGoal;
    const bGoals = aIsHome ? m.awayGoal : m.homeGoal;
    if (aGoals > bGoals) result.teamAWins++;
    else if (bGoals > aGoals) result.teamBWins++;
    else result.draws++;
  }

  const lines: string[] = [
    `${resolvedA} vs ${resolvedB} head-to-head:`,
  ];

  if (matches.length === 0) {
    lines.push("No matches found between these teams.");
  } else {
    matches.forEach((m, i) => lines.push(formatMatch(m, i)));
    lines.push("");
    lines.push(
      `Head-to-head in dataset: ${resolvedA} ${result.teamAWins} wins, ${resolvedB} ${result.teamBWins} wins, ${result.draws} draws`,
    );
  }

  return { content: [{ type: "text" as const, text: lines.join("\n") }] };
}

// ─── Competition Standings ───────────────────────────────────────────────────

export interface CompetitionStandingsArgs {
  competition: string;
  season: number;
}

export function competitionStandings(data: SoccerData, args: CompetitionStandingsArgs) {
  const { competition, season } = args;
  const c = competition.toLowerCase();

  const matches = data.matches.filter(
    (m) => m.competition.toLowerCase().includes(c) && m.season === season,
  );

  // Build standings from match results
  const teamMap = new Map<string, {
    played: number; wins: number; draws: number; losses: number;
    goalsFor: number; goalsAgainst: number;
  }>();

  for (const m of matches) {
    const home = teamMap.get(m.homeTeam) || { played: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0 };
    const away = teamMap.get(m.awayTeam) || { played: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0 };

    home.played++; away.played++;
    home.goalsFor += m.homeGoal; home.goalsAgainst += m.awayGoal;
    away.goalsFor += m.awayGoal; away.goalsAgainst += m.homeGoal;

    if (m.homeGoal > m.awayGoal) { home.wins++; away.losses++; }
    else if (m.awayGoal > m.homeGoal) { away.wins++; home.losses++; }
    else { home.draws++; away.draws++; }

    teamMap.set(m.homeTeam, home);
    teamMap.set(m.awayTeam, away);
  }

  const standings: Standing[] = [];
  let pos = 0;
  for (const [team, s] of teamMap) {
    pos++;
    standings.push({
      position: 0, // filled after sort
      team,
      points: s.wins * 3 + s.draws,
      played: s.played,
      wins: s.wins,
      draws: s.draws,
      losses: s.losses,
      goalsFor: s.goalsFor,
      goalsAgainst: s.goalsAgainst,
      goalDifference: s.goalsFor - s.goalsAgainst,
    });
  }

  standings.sort((a, b) =>
    b.points - a.points ||
    b.wins - a.wins ||
    b.goalDifference - a.goalDifference ||
    b.goalsFor - a.goalsFor,
  );
  standings.forEach((s, i) => (s.position = i + 1));

  const lines: string[] = [
    `${competition} ${season} Standings (calculated from matches):`,
  ];

  if (standings.length === 0) {
    lines.push("No match data found for this competition and season.");
  } else {
    for (const s of standings) {
      const champion = s.position === 1 ? " - Champion" : "";
      lines.push(
        `${s.position}. ${s.team} - ${s.points} pts (${s.wins}W, ${s.draws}D, ${s.losses}L) GF:${s.goalsFor} GA:${s.goalsAgainst} GD:${s.goalDifference >= 0 ? "+" : ""}${s.goalDifference}${champion}`,
      );
    }
  }

  return { content: [{ type: "text" as const, text: lines.join("\n") }] };
}

// ─── Biggest Wins ────────────────────────────────────────────────────────────

export interface BiggestWinsArgs {
  competition?: string;
  limit?: number;
}

export function biggestWins(data: SoccerData, args: BiggestWinsArgs) {
  const { competition, limit = 20 } = args;

  let matches = data.matches;

  if (competition) {
    const c = competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(c));
  }

  // Sort by goal difference descending
  matches.sort((a, b) => {
    const diffA = Math.abs(a.homeGoal - a.awayGoal);
    const diffB = Math.abs(b.homeGoal - b.awayGoal);
    return diffB - diffA || b.date.localeCompare(a.date);
  });

  matches = matches.slice(0, limit);

  const lines: string[] = [
    `Biggest victories${competition ? ` in ${competition}` : ""}:`,
  ];

  if (matches.length === 0) {
    lines.push("No matches found.");
  } else {
    matches.forEach((m, i) => {
      const diff = Math.abs(m.homeGoal - m.awayGoal);
      const winner = m.homeGoal > m.awayGoal ? m.homeTeam : m.awayTeam;
      const loser = m.homeGoal > m.awayGoal ? m.awayTeam : m.homeTeam;
      const winnerGoals = m.homeGoal > m.awayGoal ? m.homeGoal : m.awayGoal;
      const loserGoals = m.homeGoal > m.awayGoal ? m.awayGoal : m.homeGoal;
      lines.push(
        `${i + 1}. ${m.date}: ${winner} ${winnerGoals}-${loserGoals} ${loser} (${m.competition}, goal diff: ${diff})`,
      );
    });
  }

  return { content: [{ type: "text" as const, text: lines.join("\n") }] };
}

// ─── Goals Per Match ─────────────────────────────────────────────────────────

export interface GoalsPerMatchArgs {
  competition?: string;
  season?: number;
}

export function goalsPerMatch(data: SoccerData, args: GoalsPerMatchArgs) {
  const { competition, season } = args;

  let matches = data.matches;

  if (competition) {
    const c = competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(c));
  }

  if (season) {
    matches = matches.filter((m) => m.season === season);
  }

  if (matches.length === 0) {
    return { content: [{ type: "text" as const, text: "No matches found for the given criteria." }] };
  }

  let totalGoals = 0;
  let homeWins = 0;
  let awayWins = 0;
  let draws = 0;

  for (const m of matches) {
    totalGoals += m.homeGoal + m.awayGoal;
    if (m.homeGoal > m.awayGoal) homeWins++;
    else if (m.awayGoal > m.homeGoal) awayWins++;
    else draws++;
  }

  const avg = Math.round((totalGoals / matches.length) * 100) / 100;
  const homeWinRate = Math.round((homeWins / matches.length) * 1000) / 10;
  const awayWinRate = Math.round((awayWins / matches.length) * 1000) / 10;
  const drawRate = Math.round((draws / matches.length) * 1000) / 10;

  const filterStr = [competition && `${competition}`, season && `${season} season`]
    .filter(Boolean)
    .join(" ");

  const lines: string[] = [
    `Match statistics${filterStr ? ` for ${filterStr}` : ""}:`,
    `- Total matches: ${matches.length}`,
    `- Total goals: ${totalGoals}`,
    `- Average goals per match: ${avg}`,
    `- Home win rate: ${homeWinRate}%`,
    `- Away win rate: ${awayWinRate}%`,
    `- Draw rate: ${drawRate}%`,
  ];

  return { content: [{ type: "text" as const, text: lines.join("\n") }] };
}

// ─── Top Teams ───────────────────────────────────────────────────────────────

export interface TopTeamsArgs {
  competition?: string;
  season?: number;
  metric?: "wins" | "goalsFor" | "goalsAgainst" | "winRate";
  limit?: number;
}

export function topTeams(data: SoccerData, args: TopTeamsArgs) {
  const { competition, season, metric = "wins", limit = 10 } = args;

  let matches = data.matches;

  if (competition) {
    matches = matches.filter((m) => m.competition.toLowerCase().includes(competition.toLowerCase()));
  }

  if (season) {
    matches = matches.filter((m) => m.season === season);
  }

  // Aggregate per team
  const teamMap = new Map<string, TeamStats>();

  for (const m of matches) {
    for (const side of ["home", "away"] as const) {
      const team = side === "home" ? m.homeTeam : m.awayTeam;
      let stats = teamMap.get(team);
      if (!stats) {
        stats = { team, matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0, winRate: 0 };
        teamMap.set(team, stats);
      }

      const gf = side === "home" ? m.homeGoal : m.awayGoal;
      const ga = side === "home" ? m.awayGoal : m.homeGoal;

      stats.matches++;
      stats.goalsFor += gf;
      stats.goalsAgainst += ga;
      if (gf > ga) stats.wins++;
      else if (gf === ga) stats.draws++;
      else stats.losses++;
    }
  }

  for (const s of teamMap.values()) {
    s.winRate = s.matches > 0 ? Math.round((s.wins / s.matches) * 1000) / 10 : 0;
  }

  const teams = [...teamMap.values()];

  switch (metric) {
    case "wins":
      teams.sort((a, b) => b.wins - a.wins || b.winRate - a.winRate);
      break;
    case "goalsFor":
      teams.sort((a, b) => b.goalsFor - a.goalsFor);
      break;
    case "goalsAgainst":
      teams.sort((a, b) => a.goalsAgainst - b.goalsAgainst);
      break;
    case "winRate":
      teams.sort((a, b) => b.winRate - a.winRate || b.wins - a.wins);
      break;
  }

  const top = teams.slice(0, limit);

  const filterStr = [competition && `${competition}`, season && `season ${season}`]
    .filter(Boolean)
    .join(" ");

  const lines: string[] = [
    `Top teams by ${metric}${filterStr ? ` (${filterStr})` : ""}:`,
  ];

  if (top.length === 0) {
    lines.push("No match data found.");
  } else {
    top.forEach((t, i) => {
      lines.push(
        `${i + 1}. ${t.team} - ${t.wins}W/${t.draws}D/${t.losses}L, GF:${t.goalsFor}, GA:${t.goalsAgainst}, Win rate: ${t.winRate}%`,
      );
    });
  }

  return { content: [{ type: "text" as const, text: lines.join("\n") }] };
}

// ─── Best Home / Away Record ─────────────────────────────────────────────────

export interface BestRecordArgs {
  venue: "home" | "away";
  competition?: string;
  season?: number;
  limit?: number;
}

export function bestRecord(data: SoccerData, args: BestRecordArgs) {
  const { venue, competition, season, limit = 10 } = args;

  let matches = data.matches;

  if (competition) {
    matches = matches.filter((m) => m.competition.toLowerCase().includes(competition.toLowerCase()));
  }

  if (season) {
    matches = matches.filter((m) => m.season === season);
  }

  const teamMap = new Map<string, TeamStats>();

  for (const m of matches) {
    const team = venue === "home" ? m.homeTeam : m.awayTeam;
    const gf = venue === "home" ? m.homeGoal : m.awayGoal;
    const ga = venue === "home" ? m.awayGoal : m.homeGoal;

    let stats = teamMap.get(team);
    if (!stats) {
      stats = { team, matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0, winRate: 0 };
      teamMap.set(team, stats);
    }

    stats.matches++;
    stats.goalsFor += gf;
    stats.goalsAgainst += ga;
    if (gf > ga) stats.wins++;
    else if (gf === ga) stats.draws++;
    else stats.losses++;
  }

  for (const s of teamMap.values()) {
    s.winRate = s.matches > 0 ? Math.round((s.wins / s.matches) * 1000) / 10 : 0;
  }

  const teams = [...teamMap.values()]
    .sort((a, b) => b.winRate - a.winRate || b.wins - a.wins);

  const top = teams.slice(0, limit);

  const filterStr = [competition && `${competition}`, season && `season ${season}`]
    .filter(Boolean)
    .join(" ");

  const lines: string[] = [
    `Best ${venue} record${filterStr ? ` (${filterStr})` : ""}:`,
  ];

  if (top.length === 0) {
    lines.push("No match data found.");
  } else {
    top.forEach((t, i) => {
      lines.push(
        `${i + 1}. ${t.team} - ${t.wins}W/${t.draws}D/${t.losses}L, GF:${t.goalsFor}, GA:${t.goalsAgainst}, Win rate: ${t.winRate}%`,
      );
    });
  }

  return { content: [{ type: "text" as const, text: lines.join("\n") }] };
}