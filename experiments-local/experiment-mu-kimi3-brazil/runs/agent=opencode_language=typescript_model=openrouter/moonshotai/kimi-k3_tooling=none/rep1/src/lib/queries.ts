/**
 * Query engine: all retrieval operations over the unified dataset.
 * Pure functions — no MCP plumbing here, so they are trivially testable.
 */
import {
  Competition,
  Match,
  Player,
  Team,
  matchResult,
} from "./types.js";
import { Dataset } from "./dataset.js";
import { normalizeText } from "./text.js";
import { TeamResolution } from "./teams.js";

// ---------------------------------------------------------------------------
// Competition resolution
// ---------------------------------------------------------------------------

const COMPETITION_ALIASES: [RegExp, Competition][] = [
  [/libertadores/, Competition.Libertadores],
  [/copa do brasil|brazilian cup/, Competition.CopaDoBrasil],
  [/serie b/, Competition.SerieB],
  [/serie c/, Competition.SerieC],
  [/brasileirao|serie a|campeonato brasileiro|brazilian (league|championship|serie a)/, Competition.BrasileiraoSerieA],
];

/** Resolve a free-text competition name ("brasileirao", "Serie A", ...) to a Competition. */
export function resolveCompetition(query: string): Competition | null {
  const n = normalizeText(query);
  if (n.length === 0) return null;
  for (const [re, c] of COMPETITION_ALIASES) {
    if (re.test(n)) return c;
  }
  // Exact enum value match.
  for (const c of Object.values(Competition)) {
    if (normalizeText(c) === n) return c;
  }
  return null;
}

// ---------------------------------------------------------------------------
// Match queries
// ---------------------------------------------------------------------------

export interface MatchFilter {
  team?: Team | null;
  opponent?: Team | null;
  competition?: Competition | null;
  season?: number | null;
  dateFrom?: string | null; // ISO date
  dateTo?: string | null; // ISO date
  venue?: "home" | "away" | "any";
  /** Round or stage label ("1".."38", "8" = Copa do Brasil final, "final", ...). */
  round?: string | null;
  /** Only matches with a known final score. */
  playedOnly?: boolean;
}

export function findMatches(dataset: Dataset, filter: MatchFilter): Match[] {
  const venue = filter.venue ?? "any";
  const roundQ = filter.round ? filter.round.trim().toLowerCase() : null;
  return dataset.matches.filter((m) => {
    if (filter.competition && m.competition !== filter.competition) return false;
    if (filter.season != null && m.season !== filter.season) return false;
    if (roundQ && (m.round ?? "").toLowerCase() !== roundQ) return false;
    if (filter.dateFrom && (m.date === null || m.date < filter.dateFrom)) return false;
    if (filter.dateTo && (m.date === null || m.date > filter.dateTo)) return false;
    if (filter.playedOnly && (m.homeGoals === null || m.awayGoals === null)) return false;

    if (filter.team) {
      const isHome = m.homeTeam.key === filter.team.key;
      const isAway = m.awayTeam.key === filter.team.key;
      if (venue === "home" && !isHome) return false;
      if (venue === "away" && !isAway) return false;
      if (venue === "any" && !isHome && !isAway) return false;
      if (filter.opponent) {
        const oppHome = m.homeTeam.key === filter.opponent.key;
        const oppAway = m.awayTeam.key === filter.opponent.key;
        if (venue === "home" && !oppAway) return false;
        if (venue === "away" && !oppHome) return false;
        if (venue === "any" && !oppHome && !oppAway) return false;
      }
    } else if (filter.opponent) {
      const oppHome = m.homeTeam.key === filter.opponent.key;
      const oppAway = m.awayTeam.key === filter.opponent.key;
      if (!oppHome && !oppAway) return false;
    }
    return true;
  });
}

// ---------------------------------------------------------------------------
// Team statistics
// ---------------------------------------------------------------------------

export interface TeamRecord {
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  winRate: number; // 0..100, one decimal
}

export function teamRecord(matches: Match[], team: Team): TeamRecord {
  let wins = 0, draws = 0, losses = 0, gf = 0, ga = 0, played = 0;
  for (const m of matches) {
    const result = matchResult(m);
    if (result === null) continue;
    const isHome = m.homeTeam.key === team.key;
    played++;
    gf += isHome ? m.homeGoals! : m.awayGoals!;
    ga += isHome ? m.awayGoals! : m.homeGoals!;
    if (result === "draw") draws++;
    else if ((result === "home") === isHome) wins++;
    else losses++;
  }
  return {
    matches: played,
    wins,
    draws,
    losses,
    goalsFor: gf,
    goalsAgainst: ga,
    winRate: played > 0 ? Math.round((wins / played) * 1000) / 10 : 0,
  };
}

export interface HeadToHead {
  matches: Match[];
  winsA: number;
  winsB: number;
  draws: number;
  goalsA: number;
  goalsB: number;
}

export function headToHead(dataset: Dataset, a: Team, b: Team, filter: Omit<MatchFilter, "team" | "opponent"> = {}): HeadToHead {
  const matches = findMatches(dataset, { ...filter, team: a, opponent: b });
  let winsA = 0, winsB = 0, draws = 0, goalsA = 0, goalsB = 0;
  for (const m of matches) {
    const result = matchResult(m);
    if (result === null) continue;
    const aHome = m.homeTeam.key === a.key;
    goalsA += aHome ? m.homeGoals! : m.awayGoals!;
    goalsB += aHome ? m.awayGoals! : m.homeGoals!;
    if (result === "draw") draws++;
    else if ((result === "home") === aHome) winsA++;
    else winsB++;
  }
  return { matches, winsA, winsB, draws, goalsA, goalsB };
}

// ---------------------------------------------------------------------------
// Standings
// ---------------------------------------------------------------------------

export interface StandingRow {
  team: Team;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  points: number;
}

/** League points table calculated from match results (3/1/0). */
export function computeStandings(dataset: Dataset, competition: Competition, season: number): StandingRow[] {
  const matches = findMatches(dataset, { competition, season, playedOnly: true });
  const table = new Map<string, StandingRow>();
  const rowFor = (t: Team): StandingRow => {
    let row = table.get(t.key);
    if (!row) {
      row = {
        team: t, played: 0, wins: 0, draws: 0, losses: 0,
        goalsFor: 0, goalsAgainst: 0, goalDifference: 0, points: 0,
      };
      table.set(t.key, row);
    }
    return row;
  };
  for (const m of matches) {
    const result = matchResult(m);
    if (result === null) continue;
    const home = rowFor(m.homeTeam);
    const away = rowFor(m.awayTeam);
    home.played++; away.played++;
    home.goalsFor += m.homeGoals!; home.goalsAgainst += m.awayGoals!;
    away.goalsFor += m.awayGoals!; away.goalsAgainst += m.homeGoals!;
    if (result === "draw") {
      home.draws++; away.draws++;
      home.points += 1; away.points += 1;
    } else if (result === "home") {
      home.wins++; away.losses++; home.points += 3;
    } else {
      away.wins++; home.losses++; away.points += 3;
    }
  }
  const rows = [...table.values()];
  for (const r of rows) r.goalDifference = r.goalsFor - r.goalsAgainst;
  // Brazilian league tiebreakers: points, wins, goal difference, goals for.
  rows.sort(
    (a, b) =>
      b.points - a.points ||
      b.wins - a.wins ||
      b.goalDifference - a.goalDifference ||
      b.goalsFor - a.goalsFor ||
      a.team.name.localeCompare(b.team.name),
  );
  return rows;
}

// ---------------------------------------------------------------------------
// Player queries
// ---------------------------------------------------------------------------

export interface PlayerFilter {
  name?: string | null;
  nationality?: string | null;
  club?: string | null;
  /** Resolved Brazilian team key (cross-file queries). */
  teamKey?: string | null;
  position?: string | null;
  minOverall?: number | null;
  limit?: number;
}

/** Position groups: "forward" -> ST/CF/LW/RW..., "midfielder" -> CAM/CM..., etc. */
const POSITION_GROUPS: Record<string, string[]> = {
  forward: ["ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"],
  winger: ["LW", "RW", "LM", "RM"],
  midfielder: ["CM", "CAM", "CDM", "LM", "RM", "LAM", "RAM", "LCM", "RCM", "LDM", "RDM"],
  defender: ["CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"],
  fullback: ["LB", "RB", "LWB", "RWB"],
  goalkeeper: ["GK"],
};

export function searchPlayers(dataset: Dataset, filter: PlayerFilter): Player[] {
  const nameQ = filter.name ? normalizeText(filter.name) : null;
  const natQ = filter.nationality ? normalizeText(filter.nationality) : null;
  const clubQ = filter.club ? normalizeText(filter.club) : null;
  const posQ = filter.position ? filter.position.trim() : null;

  let results = dataset.players.filter((p) => {
    if (nameQ && !normalizeText(p.name).includes(nameQ)) return false;
    if (natQ && normalizeText(p.nationality) !== natQ) return false;
    if (clubQ && !(p.club && normalizeText(p.club).includes(clubQ))) return false;
    if (filter.teamKey && p.teamKey !== filter.teamKey) return false;
    if (posQ) {
      const pos = p.position?.toUpperCase() ?? "";
      const group = POSITION_GROUPS[normalizeText(posQ)];
      if (group) {
        if (!group.includes(pos)) return false;
      } else if (pos !== posQ.toUpperCase()) {
        return false;
      }
    }
    if (filter.minOverall != null && (p.overall === null || p.overall < filter.minOverall)) return false;
    return true;
  });

  // Default ordering: highest overall first; name search keeps rating order too.
  results = [...results].sort(
    (a, b) => (b.overall ?? 0) - (a.overall ?? 0) || a.name.localeCompare(b.name),
  );
  const limit = filter.limit ?? 25;
  return results.slice(0, Math.max(1, limit));
}

/** Per-club summary of Brazilian players at Brazilian clubs. */
export function brazilianPlayersByClub(dataset: Dataset): { team: Team; count: number; avgOverall: number }[] {
  const byTeam = new Map<string, Player[]>();
  for (const p of dataset.players) {
    if (normalizeText(p.nationality) !== "brazil" || !p.teamKey) continue;
    if (!byTeam.has(p.teamKey)) byTeam.set(p.teamKey, []);
    byTeam.get(p.teamKey)!.push(p);
  }
  const rows = [...byTeam.entries()].map(([key, players]) => {
    const rated = players.filter((p) => p.overall !== null);
    const avg = rated.length > 0
      ? Math.round((rated.reduce((s, p) => s + p.overall!, 0) / rated.length) * 10) / 10
      : 0;
    return { team: dataset.teams.get(key)!, count: players.length, avgOverall: avg };
  });
  rows.sort((a, b) => b.count - a.count || b.avgOverall - a.avgOverall);
  return rows;
}

// ---------------------------------------------------------------------------
// Statistical analysis
// ---------------------------------------------------------------------------

export interface CompetitionStats {
  competition: Competition | "all";
  season: number | null;
  matches: number;
  totalGoals: number;
  avgGoalsPerMatch: number;
  homeWinRate: number;
  drawRate: number;
  awayWinRate: number;
  topScoringTeam: { team: Team; goals: number } | null;
}

export function competitionStats(dataset: Dataset, competition: Competition | null, season: number | null): CompetitionStats {
  const matches = findMatches(dataset, {
    competition: competition ?? undefined,
    season: season ?? undefined,
    playedOnly: true,
  });
  let goals = 0, homeWins = 0, awayWins = 0, draws = 0;
  const goalsByTeam = new Map<string, { team: Team; goals: number }>();
  for (const m of matches) {
    const result = matchResult(m);
    if (result === null) continue;
    goals += m.homeGoals! + m.awayGoals!;
    if (result === "home") homeWins++;
    else if (result === "away") awayWins++;
    else draws++;
    for (const [t, g] of [
      [m.homeTeam, m.homeGoals!],
      [m.awayTeam, m.awayGoals!],
    ] as const) {
      const entry = goalsByTeam.get(t.key) ?? { team: t, goals: 0 };
      entry.goals += g;
      goalsByTeam.set(t.key, entry);
    }
  }
  const n = matches.length;
  let top: { team: Team; goals: number } | null = null;
  for (const entry of goalsByTeam.values()) {
    if (!top || entry.goals > top.goals) top = entry;
  }
  const pct = (x: number) => (n > 0 ? Math.round((x / n) * 1000) / 10 : 0);
  return {
    competition: competition ?? "all",
    season,
    matches: n,
    totalGoals: goals,
    avgGoalsPerMatch: n > 0 ? Math.round((goals / n) * 100) / 100 : 0,
    homeWinRate: pct(homeWins),
    drawRate: pct(draws),
    awayWinRate: pct(awayWins),
    topScoringTeam: top,
  };
}

export interface BigWin {
  match: Match;
  margin: number;
  totalGoals: number;
}

export function biggestWins(dataset: Dataset, competition: Competition | null, season: number | null, limit = 10): BigWin[] {
  const matches = findMatches(dataset, {
    competition: competition ?? undefined,
    season: season ?? undefined,
    playedOnly: true,
  });
  const wins = matches.map((m) => ({
    match: m,
    margin: Math.abs(m.homeGoals! - m.awayGoals!),
    totalGoals: m.homeGoals! + m.awayGoals!,
  }));
  wins.sort((a, b) => b.margin - a.margin || b.totalGoals - a.totalGoals || (a.match.date ?? "").localeCompare(b.match.date ?? ""));
  return wins.slice(0, Math.max(1, limit));
}

/** Resolve a team query string, returning either a team or a useful error. */
export function resolveTeamOrError(dataset: Dataset, query: string): { team?: Team; error?: string } {
  const res: TeamResolution = dataset.teams.resolve(query);
  if (res.team) return { team: res.team };
  if (res.ambiguous.length > 0) {
    const options = res.ambiguous
      .map((t) => `${t.name}${t.uf ? ` (${t.uf})` : ""}`)
      .join(", ");
    return { error: `"${query}" is ambiguous. Did you mean: ${options}?` };
  }
  return { error: `Team not found: "${query}". Try a different spelling (e.g. with or without state suffix like "-SP").` };
}
