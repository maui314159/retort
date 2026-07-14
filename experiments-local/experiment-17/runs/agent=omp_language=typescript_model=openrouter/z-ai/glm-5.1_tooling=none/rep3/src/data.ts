/**
 * Brazilian Soccer MCP Server - Unified Data Access Layer
 *
 * Provides query functions for all five required capability categories:
 *   1. Match Queries   - search_matches
 *   2. Team Queries    - get_team_stats
 *   3. Player Queries  - search_players
 *   4. Competition     - get_competition_standings
 *   5. Statistical     - get_aggregate_stats, get_head_to_head
 *
 * All functions operate on the SoccerData structure produced by the loader,
 * applying filters and computing derived statistics on demand.
 */

import type {
  MatchQuery,
  MatchRecord,
  PlayerQuery,
  PlayerRecord,
  StandingsQuery,
  StatsQuery,
  StandingEntry,
  TeamStats,
  HeadToHeadResult,
  AggregateStats,
  Competition,
} from "./types.js";
import { loadData } from "./loader.js";

// ── Helpers ──────────────────────────────────────────────────────────

function matchesTeam(match: MatchRecord, team: string): boolean {
  const t = team.toLowerCase();
  return match.homeTeam.toLowerCase().includes(t) || match.awayTeam.toLowerCase().includes(t);
}

function matchResult(match: MatchRecord, team: string): "win" | "draw" | "loss" {
  const t = team.toLowerCase();
  const isHome = match.homeTeam.toLowerCase().includes(t);
  if (match.homeGoals === match.awayGoals) return "draw";
  if (isHome) return match.homeGoals > match.awayGoals ? "win" : "loss";
  return match.awayGoals > match.homeGoals ? "win" : "loss";
}

function formatMatch(m: MatchRecord): string {
  const round = m.round ? ` Round ${m.round}` : "";
  const stage = m.stage ? ` ${m.stage}` : "";
  return `${m.date}: ${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam} (${m.competition}${round}${stage})`;
}

// ── 1. Match Queries ─────────────────────────────────────────────────

export function searchMatches(query: MatchQuery): MatchRecord[] {
  const { matches } = loadData();
  let results = matches;

  if (query.team) {
    const teamLower = query.team.toLowerCase();
    results = results.filter(
      (m) =>
        m.homeTeam.toLowerCase().includes(teamLower) ||
        m.awayTeam.toLowerCase().includes(teamLower),
    );
  }

  if (query.opponent) {
    const oppLower = query.opponent.toLowerCase();
    results = results.filter(
      (m) =>
        m.homeTeam.toLowerCase().includes(oppLower) ||
        m.awayTeam.toLowerCase().includes(oppLower),
    );
  }

  if (query.competition) {
    results = results.filter((m) => m.competition === query.competition);
  }

  if (query.season) {
    results = results.filter((m) => m.season === query.season);
  }

  if (query.startDate) {
    results = results.filter((m) => m.date >= query.startDate!);
  }

  if (query.endDate) {
    results = results.filter((m) => m.date <= query.endDate!);
  }

  results.sort((a, b) => b.date.localeCompare(a.date));

  if (query.limit && query.limit > 0) {
    results = results.slice(0, query.limit);
  }

  return results;
}

// ── 2. Team Queries ──────────────────────────────────────────────────

export function getTeamStats(
  team: string,
  season?: number,
  competition?: Competition,
  homeOnly?: boolean,
): TeamStats {
  const { matches } = loadData();
  const teamLower = team.toLowerCase();

  let teamMatches = matches.filter((m) => matchesTeam(m, team));

  if (season) {
    teamMatches = teamMatches.filter((m) => m.season === season);
  }

  if (competition) {
    teamMatches = teamMatches.filter((m) => m.competition === competition);
  }

  if (homeOnly !== undefined) {
    teamMatches = teamMatches.filter((m) =>
      homeOnly
        ? m.homeTeam.toLowerCase().includes(teamLower)
        : m.awayTeam.toLowerCase().includes(teamLower),
    );
  }

  let wins = 0, draws = 0, losses = 0, goalsFor = 0, goalsAgainst = 0;

  for (const m of teamMatches) {
    const isHome = m.homeTeam.toLowerCase().includes(teamLower);
    goalsFor += isHome ? m.homeGoals : m.awayGoals;
    goalsAgainst += isHome ? m.awayGoals : m.homeGoals;

    const result = matchResult(m, team);
    if (result === "win") wins++;
    else if (result === "draw") draws++;
    else losses++;
  }

  const total = wins + draws + losses;
  const winRate = total > 0 ? ((wins / total) * 100).toFixed(1) : "0.0";

  return { team, matches: total, wins, draws, losses, goalsFor, goalsAgainst, winRate: `${winRate}%` };
}

// ── 3. Player Queries ────────────────────────────────────────────────

export function searchPlayers(query: PlayerQuery): PlayerRecord[] {
  const { players } = loadData();
  let results = players;

  if (query.name) {
    const nameLower = query.name.toLowerCase();
    results = results.filter((p) => p.name.toLowerCase().includes(nameLower));
  }

  if (query.nationality) {
    const natLower = query.nationality.toLowerCase();
    results = results.filter((p) => p.nationality.toLowerCase().includes(natLower));
  }

  if (query.club) {
    const clubLower = query.club.toLowerCase();
    results = results.filter((p) => p.club.toLowerCase().includes(clubLower));
  }

  if (query.position) {
    const posLower = query.position.toLowerCase();
    results = results.filter((p) => p.position.toLowerCase().includes(posLower));
  }

  if (query.minOverall !== undefined) {
    results = results.filter((p) => p.overall >= query.minOverall!);
  }

  if (query.maxOverall !== undefined) {
    results = results.filter((p) => p.overall <= query.maxOverall!);
  }

  results.sort((a, b) => b.overall - a.overall);

  if (query.limit && query.limit > 0) {
    results = results.slice(0, query.limit);
  }

  return results;
}

// ── 4. Competition / Standings ───────────────────────────────────────

export function getCompetitionStandings(query: StandingsQuery): StandingEntry[] {
  const { matches } = loadData();

  const compMatches = matches.filter(
    (m) => m.competition === query.competition && m.season === query.season,
  );

  const table = new Map<string, { wins: number; draws: number; losses: number; gf: number; ga: number }>();

  for (const m of compMatches) {
    const home = m.homeTeam;
    const away = m.awayTeam;

    if (!table.has(home)) table.set(home, { wins: 0, draws: 0, losses: 0, gf: 0, ga: 0 });
    if (!table.has(away)) table.set(away, { wins: 0, draws: 0, losses: 0, gf: 0, ga: 0 });

    const h = table.get(home)!;
    const a = table.get(away)!;

    h.gf += m.homeGoals;
    h.ga += m.awayGoals;
    a.gf += m.awayGoals;
    a.ga += m.homeGoals;

    if (m.homeGoals > m.awayGoals) { h.wins++; a.losses++; }
    else if (m.homeGoals < m.awayGoals) { a.wins++; h.losses++; }
    else { h.draws++; a.draws++; }
  }

  const standings: StandingEntry[] = [];
  for (const [team, s] of table) {
    standings.push({
      position: 0,
      team,
      points: s.wins * 3 + s.draws,
      wins: s.wins,
      draws: s.draws,
      losses: s.losses,
      goalsFor: s.gf,
      goalsAgainst: s.ga,
      goalDifference: s.gf - s.ga,
    });
  }

  standings.sort((a, b) => b.points - a.points || b.goalDifference - a.goalDifference || b.goalsFor - a.goalsFor);
  standings.forEach((e, i) => { e.position = i + 1; });

  return standings;
}

// ── 5. Statistical Analysis ──────────────────────────────────────────

export function getHeadToHead(teamA: string, teamB: string): HeadToHeadResult {
  const { matches } = loadData();
  const aLower = teamA.toLowerCase();
  const bLower = teamB.toLowerCase();

  const h2h = matches.filter((m) => {
    const home = m.homeTeam.toLowerCase();
    const away = m.awayTeam.toLowerCase();
    return (home.includes(aLower) && away.includes(bLower)) || (home.includes(bLower) && away.includes(aLower));
  });

  let aWins = 0, bWins = 0, draws = 0, aGoals = 0, bGoals = 0;

  for (const m of h2h) {
    const aIsHome = m.homeTeam.toLowerCase().includes(aLower);
    const aG = aIsHome ? m.homeGoals : m.awayGoals;
    const bG = aIsHome ? m.awayGoals : m.homeGoals;
    aGoals += aG;
    bGoals += bG;
    if (aG > bG) aWins++;
    else if (bG > aG) bWins++;
    else draws++;
  }

  const recentMatches = [...h2h].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 10);

  return { teamA, teamB, matches: h2h.length, teamAWins: aWins, teamBWins: bWins, draws, teamAGoals: aGoals, teamBGoals: bGoals, recentMatches };
}

export function getAggregateStats(query: StatsQuery): AggregateStats {
  const { matches } = loadData();
  let data = matches;

  if (query.competition) data = data.filter((m) => m.competition === query.competition);
  if (query.season) data = data.filter((m) => m.season === query.season);
  if (query.team) data = data.filter((m) => matchesTeam(m, query.team!));

  let totalGoals = 0, homeWins = 0, awayWins = 0, draws = 0;
  const winMargins: { margin: number; date: string; winner: string; loser: string; homeGoals: number; awayGoals: number; competition: string }[] = [];

  for (const m of data) {
    totalGoals += m.homeGoals + m.awayGoals;
    if (m.homeGoals > m.awayGoals) {
      homeWins++;
      winMargins.push({ margin: m.homeGoals - m.awayGoals, date: m.date, winner: m.homeTeam, loser: m.awayTeam, homeGoals: m.homeGoals, awayGoals: m.awayGoals, competition: m.competition });
    } else if (m.awayGoals > m.homeGoals) {
      awayWins++;
      winMargins.push({ margin: m.awayGoals - m.homeGoals, date: m.date, winner: m.awayTeam, loser: m.homeTeam, homeGoals: m.homeGoals, awayGoals: m.awayGoals, competition: m.competition });
    } else {
      draws++;
    }
  }

  const total = data.length;
  const avgGoals = total > 0 ? (totalGoals / total).toFixed(2) : "0.00";
  const hwRate = total > 0 ? ((homeWins / total) * 100).toFixed(1) : "0.0";
  const awRate = total > 0 ? ((awayWins / total) * 100).toFixed(1) : "0.0";

  winMargins.sort((a, b) => b.margin - a.margin);
  const biggestWins = winMargins.slice(0, 10).map((w) => ({
    date: w.date, winner: w.winner, loser: w.loser, score: `${w.homeGoals}-${w.awayGoals}`, competition: w.competition,
  }));

  return {
    totalMatches: total, totalGoals, avgGoalsPerMatch: avgGoals,
    homeWins, awayWins, draws, homeWinRate: `${hwRate}%`, awayWinRate: `${awRate}%`, biggestWins,
  };
}

// ── Formatting helpers ───────────────────────────────────────────────

export function formatMatchList(matches: MatchRecord[]): string {
  if (matches.length === 0) return "No matches found.";
  return matches.map(formatMatch).join("\n");
}

export function formatTeamStats(stats: TeamStats): string {
  return [
    `${stats.team} record:`,
    `- Matches: ${stats.matches}`,
    `- Wins: ${stats.wins}, Draws: ${stats.draws}, Losses: ${stats.losses}`,
    `- Goals For: ${stats.goalsFor}, Goals Against: ${stats.goalsAgainst}`,
    `- Win rate: ${stats.winRate}`,
  ].join("\n");
}

export function formatPlayerList(players: PlayerRecord[]): string {
  if (players.length === 0) return "No players found.";
  return players
    .map((p, i) => `${i + 1}. ${p.name} - Overall: ${p.overall}, Position: ${p.position}, Club: ${p.club}`)
    .join("\n");
}

export function formatStandings(entries: StandingEntry[]): string {
  if (entries.length === 0) return "No standings data available.";
  const header = "Pos  Team                    Pts  W   D   L   GF  GA  GD";
  const lines = entries.map(
    (e) =>
      `${String(e.position).padStart(3)}  ${e.team.padEnd(23)} ${String(e.points).padStart(3)} ${String(e.wins).padStart(3)} ${String(e.draws).padStart(3)} ${String(e.losses).padStart(3)} ${String(e.goalsFor).padStart(3)} ${String(e.goalsAgainst).padStart(3)} ${String(e.goalDifference).padStart(4)}`,
  );
  return [header, ...lines].join("\n");
}

export function formatHeadToHead(h2h: HeadToHeadResult): string {
  const lines = [
    `Head-to-head: ${h2h.teamA} vs ${h2h.teamB}`,
    `Total matches: ${h2h.matches}`,
    `${h2h.teamA} wins: ${h2h.teamAWins}, ${h2h.teamB} wins: ${h2h.teamBWins}, Draws: ${h2h.draws}`,
    `${h2h.teamA} goals: ${h2h.teamAGoals}, ${h2h.teamB} goals: ${h2h.teamBGoals}`,
    "",
    "Recent matches:",
  ];
  for (const m of h2h.recentMatches) {
    lines.push(formatMatch(m));
  }
  return lines.join("\n");
}

export function formatAggregateStats(stats: AggregateStats): string {
  const lines = [
    `Total matches: ${stats.totalMatches}`,
    `Total goals: ${stats.totalGoals}`,
    `Average goals per match: ${stats.avgGoalsPerMatch}`,
    `Home wins: ${stats.homeWins} (${stats.homeWinRate})`,
    `Away wins: ${stats.awayWins} (${stats.awayWinRate})`,
    `Draws: ${stats.draws}`,
    "",
    "Biggest victories:",
  ];
  stats.biggestWins.forEach((w, i) => {
    lines.push(`${i + 1}. ${w.date}: ${w.winner} ${w.score} ${w.loser} (${w.competition})`);
  });
  return lines.join("\n");
}
