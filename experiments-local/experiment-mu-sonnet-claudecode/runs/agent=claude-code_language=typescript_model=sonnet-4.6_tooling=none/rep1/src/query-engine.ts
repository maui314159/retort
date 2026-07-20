import { normalizeTeam, teamMatches } from "./data-loader.js";

function normalizeStr(s: string): string {
  return s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
}
import type {
  NormalizedMatch,
  FifaPlayer,
  ExtendedMatch,
  TeamStats,
} from "./types.js";

export interface Database {
  matches: NormalizedMatch[];
  extended: ExtendedMatch[];
  players: FifaPlayer[];
}

// --- Match queries ---

export function searchMatches(
  db: Database,
  opts: {
    team?: string;
    homeTeam?: string;
    awayTeam?: string;
    opponent?: string;
    season?: number;
    competition?: string;
    dateFrom?: string;
    dateTo?: string;
    limit?: number;
  }
): NormalizedMatch[] {
  let results = db.matches;

  if (opts.homeTeam) {
    const ht = normalizeTeam(opts.homeTeam);
    results = results.filter((m) => teamMatches(ht, m.home_team));
  }

  if (opts.awayTeam) {
    const at = normalizeTeam(opts.awayTeam);
    results = results.filter((m) => teamMatches(at, m.away_team));
  }

  if (opts.team && !opts.homeTeam && !opts.awayTeam) {
    const t = normalizeTeam(opts.team);
    results = results.filter(
      (m) => teamMatches(t, m.home_team) || teamMatches(t, m.away_team)
    );
  }

  if (opts.opponent && opts.team) {
    const t = normalizeTeam(opts.team);
    const o = normalizeTeam(opts.opponent);
    results = results.filter((m) => {
      const homeIsTeam = teamMatches(t, m.home_team);
      const awayIsTeam = teamMatches(t, m.away_team);
      const homeIsOpp = teamMatches(o, m.home_team);
      const awayIsOpp = teamMatches(o, m.away_team);
      return (homeIsTeam && awayIsOpp) || (awayIsTeam && homeIsOpp);
    });
  } else if (opts.opponent && !opts.team) {
    const o = normalizeTeam(opts.opponent);
    results = results.filter(
      (m) => teamMatches(o, m.home_team) || teamMatches(o, m.away_team)
    );
  }

  if (opts.season) {
    results = results.filter((m) => m.season === opts.season);
  }

  if (opts.competition) {
    const comp = normalizeStr(opts.competition);
    results = results.filter((m) =>
      normalizeStr(m.competition).includes(comp)
    );
  }

  if (opts.dateFrom) {
    results = results.filter((m) => m.date >= opts.dateFrom!);
  }
  if (opts.dateTo) {
    results = results.filter((m) => m.date <= opts.dateTo!);
  }

  // Sort by date descending
  results.sort((a, b) => b.date.localeCompare(a.date));

  if (opts.limit) {
    results = results.slice(0, opts.limit);
  }

  return results;
}

// --- Team stats ---

export function getTeamStats(
  db: Database,
  team: string,
  opts: { season?: number; competition?: string; homeOnly?: boolean; awayOnly?: boolean }
): TeamStats {
  const t = normalizeTeam(team);
  let matches = db.matches;

  if (opts.season) matches = matches.filter((m) => m.season === opts.season);
  if (opts.competition) {
    const comp = normalizeStr(opts.competition);
    matches = matches.filter((m) => normalizeStr(m.competition).includes(comp));
  }

  const stats: TeamStats = {
    team,
    matches: 0,
    wins: 0,
    draws: 0,
    losses: 0,
    goals_for: 0,
    goals_against: 0,
    goal_difference: 0,
    points: 0,
  };

  for (const m of matches) {
    const isHome = teamMatches(t, m.home_team);
    const isAway = teamMatches(t, m.away_team);

    if (!isHome && !isAway) continue;
    if (opts.homeOnly && !isHome) continue;
    if (opts.awayOnly && !isAway) continue;

    stats.matches++;
    const gf = isHome ? m.home_goal : m.away_goal;
    const ga = isHome ? m.away_goal : m.home_goal;
    stats.goals_for += gf;
    stats.goals_against += ga;

    if (gf > ga) {
      stats.wins++;
      stats.points += 3;
    } else if (gf === ga) {
      stats.draws++;
      stats.points += 1;
    } else {
      stats.losses++;
    }
  }

  stats.goal_difference = stats.goals_for - stats.goals_against;
  return stats;
}

// --- Head-to-head ---

export function headToHead(
  db: Database,
  team1: string,
  team2: string,
  opts: { season?: number; competition?: string; limit?: number }
): {
  matches: NormalizedMatch[];
  team1_wins: number;
  team2_wins: number;
  draws: number;
  team1_goals: number;
  team2_goals: number;
} {
  const t1 = normalizeTeam(team1);
  const t2 = normalizeTeam(team2);

  let matches = db.matches.filter((m) => {
    const t1Home = teamMatches(t1, m.home_team);
    const t1Away = teamMatches(t1, m.away_team);
    const t2Home = teamMatches(t2, m.home_team);
    const t2Away = teamMatches(t2, m.away_team);
    return (t1Home && t2Away) || (t1Away && t2Home);
  });

  if (opts.season) matches = matches.filter((m) => m.season === opts.season);
  if (opts.competition) {
    const comp = normalizeStr(opts.competition);
    matches = matches.filter((m) => normalizeStr(m.competition).includes(comp));
  }

  matches.sort((a, b) => b.date.localeCompare(a.date));

  let t1_wins = 0, t2_wins = 0, draws = 0;
  let t1_goals = 0, t2_goals = 0;

  for (const m of matches) {
    const t1IsHome = teamMatches(t1, m.home_team);
    const t1gf = t1IsHome ? m.home_goal : m.away_goal;
    const t2gf = t1IsHome ? m.away_goal : m.home_goal;
    t1_goals += t1gf;
    t2_goals += t2gf;
    if (t1gf > t2gf) t1_wins++;
    else if (t1gf < t2gf) t2_wins++;
    else draws++;
  }

  const limited = opts.limit ? matches.slice(0, opts.limit) : matches;
  return { matches: limited, team1_wins: t1_wins, team2_wins: t2_wins, draws, team1_goals: t1_goals, team2_goals: t2_goals };
}

// --- Standings ---

export function getStandings(
  db: Database,
  season: number,
  competition?: string
): TeamStats[] {
  const teamsMap = new Map<string, TeamStats>();

  let matches = db.matches.filter((m) => m.season === season);
  if (competition) {
    const comp = normalizeStr(competition);
    matches = matches.filter((m) => normalizeStr(m.competition).includes(comp));
  }

  function getOrCreate(name: string): TeamStats {
    const key = normalizeTeam(name);
    if (!teamsMap.has(key)) {
      teamsMap.set(key, {
        team: name,
        matches: 0, wins: 0, draws: 0, losses: 0,
        goals_for: 0, goals_against: 0, goal_difference: 0, points: 0,
      });
    }
    return teamsMap.get(key)!;
  }

  for (const m of matches) {
    const home = getOrCreate(m.home_team);
    const away = getOrCreate(m.away_team);

    home.matches++; away.matches++;
    home.goals_for += m.home_goal; home.goals_against += m.away_goal;
    away.goals_for += m.away_goal; away.goals_against += m.home_goal;

    if (m.home_goal > m.away_goal) {
      home.wins++; home.points += 3;
      away.losses++;
    } else if (m.home_goal < m.away_goal) {
      away.wins++; away.points += 3;
      home.losses++;
    } else {
      home.draws++; home.points += 1;
      away.draws++; away.points += 1;
    }
  }

  const standings = Array.from(teamsMap.values()).map((s) => ({
    ...s,
    goal_difference: s.goals_for - s.goals_against,
  }));

  // Sort by points, then goal difference, then goals for
  standings.sort((a, b) =>
    b.points - a.points ||
    b.goal_difference - a.goal_difference ||
    b.goals_for - a.goals_for
  );

  return standings;
}

// --- Player queries ---

export function searchPlayers(
  db: Database,
  opts: {
    name?: string;
    nationality?: string;
    club?: string;
    position?: string;
    minOverall?: number;
    maxAge?: number;
    limit?: number;
  }
): FifaPlayer[] {
  let players = db.players;

  if (opts.name) {
    const n = opts.name.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
    players = players.filter((p) =>
      p.Name.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").includes(n)
    );
  }

  if (opts.nationality) {
    const nat = opts.nationality.toLowerCase();
    players = players.filter((p) => p.Nationality.toLowerCase().includes(nat));
  }

  if (opts.club) {
    const club = opts.club.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
    players = players.filter((p) =>
      p.Club.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").includes(club)
    );
  }

  if (opts.position) {
    const pos = opts.position.toUpperCase();
    players = players.filter((p) => p.Position.toUpperCase().includes(pos));
  }

  if (opts.minOverall !== undefined) {
    players = players.filter((p) => p.Overall >= opts.minOverall!);
  }

  if (opts.maxAge !== undefined) {
    players = players.filter((p) => p.Age <= opts.maxAge!);
  }

  players.sort((a, b) => b.Overall - a.Overall);

  if (opts.limit) players = players.slice(0, opts.limit);

  return players;
}

// --- Statistics ---

export function getGlobalStats(db: Database, competition?: string): {
  total_matches: number;
  total_goals: number;
  avg_goals_per_match: number;
  home_wins: number;
  away_wins: number;
  draws: number;
  home_win_rate: number;
} {
  let matches = db.matches;
  if (competition) {
    const comp = normalizeStr(competition);
    matches = matches.filter((m) => normalizeStr(m.competition).includes(comp));
  }

  let total_goals = 0, home_wins = 0, away_wins = 0, draws = 0;
  for (const m of matches) {
    total_goals += m.home_goal + m.away_goal;
    if (m.home_goal > m.away_goal) home_wins++;
    else if (m.home_goal < m.away_goal) away_wins++;
    else draws++;
  }

  const total_matches = matches.length;
  return {
    total_matches,
    total_goals,
    avg_goals_per_match: total_matches > 0 ? +(total_goals / total_matches).toFixed(2) : 0,
    home_wins,
    away_wins,
    draws,
    home_win_rate: total_matches > 0 ? +((home_wins / total_matches) * 100).toFixed(1) : 0,
  };
}

export function getBiggestWins(
  db: Database,
  limit = 10,
  competition?: string
): Array<NormalizedMatch & { margin: number }> {
  let matches = db.matches;
  if (competition) {
    const comp = normalizeStr(competition);
    matches = matches.filter((m) => normalizeStr(m.competition).includes(comp));
  }

  const withMargin = matches.map((m) => ({
    ...m,
    margin: Math.abs(m.home_goal - m.away_goal),
  }));

  withMargin.sort((a, b) => b.margin - a.margin || b.home_goal + b.away_goal - (a.home_goal + a.away_goal));
  return withMargin.slice(0, limit);
}

export function getExtendedStats(
  db: Database,
  team: string,
  opts: { limit?: number } = {}
): ExtendedMatch[] {
  const t = normalizeTeam(team);
  let results = db.extended.filter(
    (m) => teamMatches(t, m.home) || teamMatches(t, m.away)
  );
  if (opts.limit) results = results.slice(0, opts.limit);
  return results;
}
