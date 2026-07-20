import { loadAllMatches, loadFifaPlayers, normalizeTeamName, teamsMatch } from "./dataLoader.js";
import type { NormalizedMatch, TeamStats, HeadToHeadResult, FifaPlayer } from "./types.js";

export interface SearchMatchesArgs {
  team?: string;
  team2?: string;
  competition?: string;
  season?: number;
  date_from?: string;
  date_to?: string;
  limit?: number;
}

export function searchMatches(args: SearchMatchesArgs): {
  matches: NormalizedMatch[];
  total: number;
  summary?: string;
} {
  const limit = args.limit ?? 20;
  let matches = loadAllMatches();

  if (args.team) {
    matches = matches.filter(
      (m) => teamsMatch(m.home_team, args.team!) || teamsMatch(m.away_team, args.team!)
    );
  }

  if (args.team2) {
    matches = matches.filter(
      (m) => teamsMatch(m.home_team, args.team2!) || teamsMatch(m.away_team, args.team2!)
    );
  }

  if (args.competition) {
    const comp = args.competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(comp));
  }

  if (args.season) {
    matches = matches.filter((m) => m.season === args.season);
  }

  if (args.date_from) {
    matches = matches.filter((m) => m.datetime >= args.date_from!);
  }

  if (args.date_to) {
    matches = matches.filter((m) => m.datetime <= args.date_to!);
  }

  // Sort by datetime descending
  matches = matches.sort((a, b) => b.datetime.localeCompare(a.datetime));

  const total = matches.length;
  const limited = matches.slice(0, limit);

  return { matches: limited, total };
}

export interface GetTeamStatsArgs {
  team: string;
  competition?: string;
  season?: number;
}

export function getTeamStats(args: GetTeamStatsArgs): TeamStats & { competition?: string; season?: number } {
  let matches = loadAllMatches();

  matches = matches.filter(
    (m) => teamsMatch(m.home_team, args.team) || teamsMatch(m.away_team, args.team)
  );

  if (args.competition) {
    const comp = args.competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(comp));
  }

  if (args.season) {
    matches = matches.filter((m) => m.season === args.season);
  }

  let wins = 0;
  let draws = 0;
  let losses = 0;
  let goals_for = 0;
  let goals_against = 0;

  for (const m of matches) {
    const isHome = teamsMatch(m.home_team, args.team);
    const gf = isHome ? m.home_goal : m.away_goal;
    const ga = isHome ? m.away_goal : m.home_goal;
    goals_for += gf;
    goals_against += ga;
    if (gf > ga) wins++;
    else if (gf === ga) draws++;
    else losses++;
  }

  const total = matches.length;
  return {
    team: args.team,
    matches: total,
    wins,
    draws,
    losses,
    goals_for,
    goals_against,
    goal_difference: goals_for - goals_against,
    points: wins * 3 + draws,
    win_rate: total > 0 ? Math.round((wins / total) * 1000) / 10 : 0,
    competition: args.competition,
    season: args.season,
  };
}

export interface HeadToHeadArgs {
  team1: string;
  team2: string;
  competition?: string;
  season?: number;
  limit?: number;
}

export function headToHead(args: HeadToHeadArgs): HeadToHeadResult {
  const limit = args.limit ?? 10;
  let matches = loadAllMatches();

  matches = matches.filter(
    (m) =>
      (teamsMatch(m.home_team, args.team1) && teamsMatch(m.away_team, args.team2)) ||
      (teamsMatch(m.home_team, args.team2) && teamsMatch(m.away_team, args.team1))
  );

  if (args.competition) {
    const comp = args.competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(comp));
  }

  if (args.season) {
    matches = matches.filter((m) => m.season === args.season);
  }

  matches = matches.sort((a, b) => b.datetime.localeCompare(a.datetime));

  let team1_wins = 0;
  let team2_wins = 0;
  let draws = 0;
  let team1_goals = 0;
  let team2_goals = 0;

  for (const m of matches) {
    const team1IsHome = teamsMatch(m.home_team, args.team1);
    const g1 = team1IsHome ? m.home_goal : m.away_goal;
    const g2 = team1IsHome ? m.away_goal : m.home_goal;
    team1_goals += g1;
    team2_goals += g2;
    if (g1 > g2) team1_wins++;
    else if (g1 === g2) draws++;
    else team2_wins++;
  }

  return {
    team1: args.team1,
    team2: args.team2,
    total_matches: matches.length,
    team1_wins,
    team2_wins,
    draws,
    team1_goals,
    team2_goals,
    matches: matches.slice(0, limit),
  };
}

export interface SearchPlayersArgs {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  min_overall?: number;
  limit?: number;
}

export function searchPlayers(args: SearchPlayersArgs): {
  players: FifaPlayer[];
  total: number;
} {
  const limit = args.limit ?? 20;
  let players = loadFifaPlayers();

  if (args.name) {
    const nameLower = args.name.toLowerCase();
    players = players.filter((p) => p.name.toLowerCase().includes(nameLower));
  }

  if (args.nationality) {
    const natLower = args.nationality.toLowerCase();
    players = players.filter((p) => p.nationality.toLowerCase().includes(natLower));
  }

  if (args.club) {
    const clubLower = args.club.toLowerCase();
    players = players.filter((p) => p.club.toLowerCase().includes(clubLower));
  }

  if (args.position) {
    const posLower = args.position.toLowerCase();
    players = players.filter((p) => p.position.toLowerCase().includes(posLower));
  }

  if (args.min_overall) {
    players = players.filter((p) => p.overall >= args.min_overall!);
  }

  players = players.sort((a, b) => b.overall - a.overall);

  return { players: players.slice(0, limit), total: players.length };
}

export interface GetStandingsArgs {
  competition: string;
  season: number;
}

export function getStandings(args: GetStandingsArgs): {
  competition: string;
  season: number;
  standings: TeamStats[];
} {
  const comp = args.competition.toLowerCase();
  let matches = loadAllMatches().filter(
    (m) => m.competition.toLowerCase().includes(comp) && m.season === args.season
  );

  const teamMap = new Map<string, TeamStats>();

  function getOrCreate(rawName: string): TeamStats {
    const key = normalizeTeamName(rawName);
    if (!teamMap.has(key)) {
      teamMap.set(key, {
        team: rawName,
        matches: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        goals_for: 0,
        goals_against: 0,
        goal_difference: 0,
        points: 0,
        win_rate: 0,
      });
    }
    return teamMap.get(key)!;
  }

  for (const m of matches) {
    const home = getOrCreate(m.home_team);
    const away = getOrCreate(m.away_team);

    home.matches++;
    away.matches++;
    home.goals_for += m.home_goal;
    home.goals_against += m.away_goal;
    away.goals_for += m.away_goal;
    away.goals_against += m.home_goal;

    if (m.home_goal > m.away_goal) {
      home.wins++;
      away.losses++;
    } else if (m.home_goal === m.away_goal) {
      home.draws++;
      away.draws++;
    } else {
      away.wins++;
      home.losses++;
    }
  }

  const standings = Array.from(teamMap.values()).map((s) => ({
    ...s,
    goal_difference: s.goals_for - s.goals_against,
    points: s.wins * 3 + s.draws,
    win_rate: s.matches > 0 ? Math.round((s.wins / s.matches) * 1000) / 10 : 0,
  }));

  standings.sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    if (b.wins !== a.wins) return b.wins - a.wins;
    return b.goal_difference - a.goal_difference;
  });

  return { competition: args.competition, season: args.season, standings };
}

export interface GetTopStatsArgs {
  stat: "biggest_wins" | "most_goals" | "home_record" | "away_record" | "averages";
  competition?: string;
  season?: number;
  limit?: number;
}

export function getTopStats(args: GetTopStatsArgs): Record<string, unknown> {
  const limit = args.limit ?? 10;
  let matches = loadAllMatches();

  if (args.competition) {
    const comp = args.competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(comp));
  }

  if (args.season) {
    matches = matches.filter((m) => m.season === args.season);
  }

  if (args.stat === "biggest_wins") {
    const sorted = [...matches]
      .map((m) => ({ ...m, margin: Math.abs(m.home_goal - m.away_goal) }))
      .sort((a, b) => b.margin - a.margin || b.home_goal + b.away_goal - (a.home_goal + a.away_goal))
      .slice(0, limit);
    return { stat: "biggest_wins", results: sorted };
  }

  if (args.stat === "most_goals") {
    const sorted = [...matches]
      .map((m) => ({ ...m, total_goals: m.home_goal + m.away_goal }))
      .sort((a, b) => b.total_goals - a.total_goals)
      .slice(0, limit);
    return { stat: "most_goals", results: sorted };
  }

  if (args.stat === "averages") {
    const total = matches.length;
    const totalGoals = matches.reduce((s, m) => s + m.home_goal + m.away_goal, 0);
    const homeWins = matches.filter((m) => m.home_goal > m.away_goal).length;
    const draws = matches.filter((m) => m.home_goal === m.away_goal).length;
    const awayWins = matches.filter((m) => m.away_goal > m.home_goal).length;

    return {
      stat: "averages",
      total_matches: total,
      avg_goals_per_match: total > 0 ? Math.round((totalGoals / total) * 100) / 100 : 0,
      home_win_rate: total > 0 ? Math.round((homeWins / total) * 1000) / 10 : 0,
      draw_rate: total > 0 ? Math.round((draws / total) * 1000) / 10 : 0,
      away_win_rate: total > 0 ? Math.round((awayWins / total) * 1000) / 10 : 0,
    };
  }

  if (args.stat === "home_record" || args.stat === "away_record") {
    const teamMap = new Map<string, { team: string; wins: number; draws: number; losses: number; matches: number }>();

    for (const m of matches) {
      const isHomeRecord = args.stat === "home_record";
      const teamName = isHomeRecord ? m.home_team_normalized : m.away_team_normalized;
      const rawName = isHomeRecord ? m.home_team : m.away_team;

      if (!teamMap.has(teamName)) {
        teamMap.set(teamName, { team: rawName, wins: 0, draws: 0, losses: 0, matches: 0 });
      }
      const stats = teamMap.get(teamName)!;
      stats.matches++;

      const gf = isHomeRecord ? m.home_goal : m.away_goal;
      const ga = isHomeRecord ? m.away_goal : m.home_goal;
      if (gf > ga) stats.wins++;
      else if (gf === ga) stats.draws++;
      else stats.losses++;
    }

    const results = Array.from(teamMap.values())
      .filter((t) => t.matches >= 5)
      .map((t) => ({
        ...t,
        win_rate: Math.round((t.wins / t.matches) * 1000) / 10,
        points: t.wins * 3 + t.draws,
      }))
      .sort((a, b) => b.win_rate - a.win_rate)
      .slice(0, limit);

    return { stat: args.stat, results };
  }

  return { error: "Unknown stat type" };
}
