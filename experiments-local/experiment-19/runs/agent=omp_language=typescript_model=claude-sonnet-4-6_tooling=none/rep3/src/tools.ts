import type { Tool } from "@modelcontextprotocol/sdk/types.js";
import {
  loadMatches,
  loadPlayers,
  normalizeTeam,
  teamMatchesQuery,
  matchesCompetition,
  type Match,
  type Player,
} from "./data.js";

// ---------------------------------------------------------------------------
// Tool definitions (schema exposed to the LLM)
// ---------------------------------------------------------------------------

export const toolDefinitions: Tool[] = [
  {
    name: "search_matches",
    description:
      "Search for soccer matches across all datasets. Filter by team, opponent, competition, season, or date range. Returns match list with scores and competition info.",
    inputSchema: {
      type: "object",
      properties: {
        team: { type: "string", description: "Team name (partial match, e.g. 'Flamengo', 'Palmeiras')" },
        opponent: { type: "string", description: "Opponent team name — finds head-to-head when combined with team" },
        competition: {
          type: "string",
          description: "Competition filter: 'brasileirao', 'copa_brasil', 'libertadores', 'extended', 'historical', 'all' (default: 'all')",
        },
        season: { type: "number", description: "Season year (e.g. 2019, 2022)" },
        date_from: { type: "string", description: "Start date YYYY-MM-DD" },
        date_to: { type: "string", description: "End date YYYY-MM-DD" },
        limit: { type: "number", description: "Max results to return (default 25, max 100)" },
      },
    },
  },
  {
    name: "get_head_to_head",
    description:
      "Get the complete head-to-head record between two teams, including all matches and a W/D/L summary.",
    inputSchema: {
      type: "object",
      required: ["team1", "team2"],
      properties: {
        team1: { type: "string", description: "First team name" },
        team2: { type: "string", description: "Second team name" },
        competition: { type: "string", description: "Filter by competition (optional, default: 'all')" },
        season: { type: "number", description: "Filter by season year (optional)" },
        limit: { type: "number", description: "Max matches to list (default 20)" },
      },
    },
  },
  {
    name: "get_team_stats",
    description:
      "Get win/draw/loss statistics, goals for/against, and win rate for a team. Can filter by competition, season, and home/away.",
    inputSchema: {
      type: "object",
      required: ["team"],
      properties: {
        team: { type: "string", description: "Team name" },
        competition: { type: "string", description: "Competition filter (default: 'all')" },
        season: { type: "number", description: "Season year (optional)" },
        venue: {
          type: "string",
          description: "Filter to 'home', 'away', or 'all' matches (default: 'all')",
        },
      },
    },
  },
  {
    name: "search_players",
    description:
      "Search the FIFA player database. Filter by name, nationality, club, position, and overall rating.",
    inputSchema: {
      type: "object",
      properties: {
        name: { type: "string", description: "Player name (partial match, e.g. 'Neymar', 'Gabriel')" },
        nationality: { type: "string", description: "Nationality (e.g. 'Brazil', 'Argentina')" },
        club: { type: "string", description: "Club name (partial match, e.g. 'Flamengo', 'Real Madrid')" },
        position: {
          type: "string",
          description: "Position: exact (GK, ST, CB…) or category (goalkeeper, forward, midfielder, defender)",
        },
        min_overall: { type: "number", description: "Minimum overall rating (0-99)" },
        max_overall: { type: "number", description: "Maximum overall rating (0-99)" },
        limit: { type: "number", description: "Max results (default 20, max 100)" },
      },
    },
  },
  {
    name: "get_standings",
    description:
      "Calculate the final league standings for a Brasileirão season (points, W/D/L, GF, GA, GD). Covers 2003-2023.",
    inputSchema: {
      type: "object",
      required: ["season"],
      properties: {
        season: { type: "number", description: "Season year (2003-2023)" },
        limit: { type: "number", description: "Teams to show (default 20 = full table)" },
      },
    },
  },
  {
    name: "get_biggest_wins",
    description:
      "List the biggest victories (by goal margin) across all competitions or a specific one.",
    inputSchema: {
      type: "object",
      properties: {
        competition: { type: "string", description: "Competition filter (default: 'all')" },
        season: { type: "number", description: "Season year (optional)" },
        limit: { type: "number", description: "Number of results (default 10)" },
      },
    },
  },
  {
    name: "get_league_overview",
    description:
      "Get aggregate statistics for a competition and/or season: total matches, goals, average goals per match, home win rate, top scorers if available.",
    inputSchema: {
      type: "object",
      properties: {
        competition: { type: "string", description: "Competition filter (default: 'all')" },
        season: { type: "number", description: "Season year (optional)" },
      },
    },
  },
  {
    name: "list_teams",
    description:
      "List all unique team names in the dataset, optionally filtered by competition.",
    inputSchema: {
      type: "object",
      properties: {
        competition: { type: "string", description: "Competition filter (default: 'all')" },
        search: { type: "string", description: "Filter teams by name substring" },
      },
    },
  },
];

// ---------------------------------------------------------------------------
// Dispatch
// ---------------------------------------------------------------------------

export async function handleToolCall(
  name: string,
  args: Record<string, unknown>
): Promise<string> {
  switch (name) {
    case "search_matches":
      return searchMatches(args);
    case "get_head_to_head":
      return getHeadToHead(args);
    case "get_team_stats":
      return getTeamStats(args);
    case "search_players":
      return searchPlayers(args);
    case "get_standings":
      return getStandings(args);
    case "get_biggest_wins":
      return getBiggestWins(args);
    case "get_league_overview":
      return getLeagueOverview(args);
    case "list_teams":
      return listTeams(args);
    default:
      throw new Error(`Unknown tool: ${name}`);
  }
}

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

function competitionLabel(m: Match): string {
  switch (m.competition) {
    case "brasileirao":
      return `Brasileirão ${m.season}${m.round != null ? " R" + m.round : ""}`;
    case "historical":
      return `Brasileirão ${m.season}${m.round != null ? " R" + m.round : ""}`;
    case "copa_brasil":
      return `Copa do Brasil ${m.season}${m.round != null ? " R" + m.round : ""}`;
    case "libertadores":
      return `Copa Libertadores ${m.season}${m.stage ? " – " + m.stage : ""}`;
    case "extended":
      return `${m.tournament ?? "Match"} ${m.season}`;
  }
}

function matchLine(m: Match): string {
  return `${m.date}: ${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam} (${competitionLabel(m)})`;
}

function pct(num: number, denom: number): string {
  if (!denom) return "0.0%";
  return ((num / denom) * 100).toFixed(1) + "%";
}

// ---------------------------------------------------------------------------
// Tool: search_matches
// ---------------------------------------------------------------------------

function searchMatches(args: Record<string, unknown>): string {
  const team = typeof args.team === "string" ? args.team.trim() : "";
  const opponent = typeof args.opponent === "string" ? args.opponent.trim() : "";
  const competition = typeof args.competition === "string" ? args.competition : "all";
  const season = typeof args.season === "number" ? args.season : 0;
  const dateFrom = typeof args.date_from === "string" ? args.date_from : "";
  const dateTo = typeof args.date_to === "string" ? args.date_to : "";
  const limit = Math.min(typeof args.limit === "number" ? args.limit : 25, 100);

  let matches = loadMatches();

  if (competition !== "all") {
    matches = matches.filter((m) => matchesCompetition(m, competition));
  }
  if (season) {
    matches = matches.filter((m) => m.season === season);
  }
  if (dateFrom) {
    matches = matches.filter((m) => m.date >= dateFrom);
  }
  if (dateTo) {
    matches = matches.filter((m) => m.date <= dateTo);
  }
  if (team) {
    matches = matches.filter(
      (m) => teamMatchesQuery(m.homeTeam, team) || teamMatchesQuery(m.awayTeam, team)
    );
  }
  if (opponent) {
    matches = matches.filter(
      (m) => teamMatchesQuery(m.homeTeam, opponent) || teamMatchesQuery(m.awayTeam, opponent)
    );
  }

  if (!matches.length) {
    return "No matches found for the given criteria.";
  }

  // Sort by date descending
  matches.sort((a, b) => (a.date < b.date ? 1 : -1));

  const total = matches.length;
  const shown = matches.slice(0, limit);
  const lines = shown.map(matchLine);

  let result = `Found ${total} match${total !== 1 ? "es" : ""}`;
  if (total > limit) result += ` (showing most recent ${limit})`;
  result += ":\n\n" + lines.join("\n");
  return result;
}

// ---------------------------------------------------------------------------
// Tool: get_head_to_head
// ---------------------------------------------------------------------------

function getHeadToHead(args: Record<string, unknown>): string {
  const team1 = String(args.team1 ?? "").trim();
  const team2 = String(args.team2 ?? "").trim();
  const competition = typeof args.competition === "string" ? args.competition : "all";
  const season = typeof args.season === "number" ? args.season : 0;
  const limit = Math.min(typeof args.limit === "number" ? args.limit : 20, 100);

  if (!team1 || !team2) return "Both team1 and team2 are required.";

  let matches = loadMatches();

  if (competition !== "all") {
    matches = matches.filter((m) => matchesCompetition(m, competition));
  }
  if (season) {
    matches = matches.filter((m) => m.season === season);
  }

  // Both teams must appear in the match
  matches = matches.filter(
    (m) =>
      (teamMatchesQuery(m.homeTeam, team1) && teamMatchesQuery(m.awayTeam, team2)) ||
      (teamMatchesQuery(m.homeTeam, team2) && teamMatchesQuery(m.awayTeam, team1))
  );

  if (!matches.length) {
    return `No head-to-head matches found between "${team1}" and "${team2}".`;
  }

  matches.sort((a, b) => (a.date < b.date ? 1 : -1));

  // Compute summary from team1's perspective
  let t1Wins = 0, t2Wins = 0, draws = 0;
  for (const m of matches) {
    const t1IsHome =
      teamMatchesQuery(m.homeTeam, team1) && teamMatchesQuery(m.awayTeam, team2);
    const t1Goals = t1IsHome ? m.homeGoals : m.awayGoals;
    const t2Goals = t1IsHome ? m.awayGoals : m.homeGoals;
    if (t1Goals > t2Goals) t1Wins++;
    else if (t2Goals > t1Goals) t2Wins++;
    else draws++;
  }

  const total = matches.length;
  const shown = matches.slice(0, limit);
  const lines = shown.map(matchLine);

  let result = `Head-to-head: ${team1} vs ${team2}\n`;
  result += `Total matches: ${total} | `;
  result += `${team1} wins: ${t1Wins} | ${team2} wins: ${t2Wins} | Draws: ${draws}\n\n`;
  if (total > limit) result += `(showing most recent ${limit})\n\n`;
  result += lines.join("\n");
  return result;
}

// ---------------------------------------------------------------------------
// Tool: get_team_stats
// ---------------------------------------------------------------------------

function getTeamStats(args: Record<string, unknown>): string {
  const team = String(args.team ?? "").trim();
  const competition = typeof args.competition === "string" ? args.competition : "all";
  const season = typeof args.season === "number" ? args.season : 0;
  const venue = typeof args.venue === "string" ? args.venue.toLowerCase() : "all";

  if (!team) return "team parameter is required.";

  let matches = loadMatches();

  if (competition !== "all") {
    matches = matches.filter((m) => matchesCompetition(m, competition));
  }
  if (season) {
    matches = matches.filter((m) => m.season === season);
  }

  // Matches where the team plays
  const teamMatches = matches.filter(
    (m) => teamMatchesQuery(m.homeTeam, team) || teamMatchesQuery(m.awayTeam, team)
  );

  if (!teamMatches.length) {
    return `No matches found for "${team}" with the given filters.`;
  }

  type Record_ = { w: number; d: number; l: number; gf: number; ga: number; matches: number };
  const empty = (): Record_ => ({ w: 0, d: 0, l: 0, gf: 0, ga: 0, matches: 0 });
  const home = empty(), away = empty(), overall = empty();

  for (const m of teamMatches) {
    const isHome = teamMatchesQuery(m.homeTeam, team);
    const gf = isHome ? m.homeGoals : m.awayGoals;
    const ga = isHome ? m.awayGoals : m.homeGoals;

    const rec = isHome ? home : away;
    if (venue === "all" || (venue === "home" && isHome) || (venue === "away" && !isHome)) {
      rec.matches++;
      rec.gf += gf;
      rec.ga += ga;
      if (gf > ga) rec.w++;
      else if (gf === ga) rec.d++;
      else rec.l++;
    }

    overall.matches++;
    overall.gf += gf;
    overall.ga += ga;
    if (gf > ga) overall.w++;
    else if (gf === ga) overall.d++;
    else overall.l++;
  }

  const seasonStr = season ? ` ${season}` : "";
  const compStr = competition !== "all" ? ` (${competition})` : "";
  let result = `${team} statistics${compStr}${seasonStr}\n\n`;

  const fmt = (label: string, r: Record_) => {
    if (!r.matches) return "";
    return (
      `${label}: ${r.matches} matches | ` +
      `${r.w}W ${r.d}D ${r.l}L | ` +
      `GF ${r.gf} GA ${r.ga} GD ${r.gf - r.ga} | ` +
      `Win rate: ${pct(r.w, r.matches)}\n`
    );
  };

  if (venue === "all") {
    result += fmt("Overall", overall);
    result += fmt("Home", home);
    result += fmt("Away", away);
  } else if (venue === "home") {
    result += fmt("Home", home);
  } else {
    result += fmt("Away", away);
  }

  return result.trim();
}

// ---------------------------------------------------------------------------
// Tool: search_players
// ---------------------------------------------------------------------------

function positionMatchesQuery(pos: string, query: string): boolean {
  const p = pos.toUpperCase();
  const q = query.toUpperCase();
  if (p === q) return true;
  // Category matching
  const FORWARDS = ["ST", "CF", "LF", "RF", "LS", "RS", "LW", "RW"];
  const MIDFIELDERS = ["CM", "CAM", "CDM", "LM", "RM", "LCM", "RCM", "LAM", "RAM", "LDM", "RDM"];
  const DEFENDERS = ["CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB"];
  if (["FORWARD", "STRIKER", "ATTACK", "ATTACKER", "WINGER"].includes(q) && FORWARDS.includes(p))
    return true;
  if (["MIDFIELDER", "MID", "MIDFIELD"].includes(q) && MIDFIELDERS.includes(p)) return true;
  if (["DEFENDER", "DEF", "DEFENSE", "BACK"].includes(q) && DEFENDERS.includes(p)) return true;
  if (["GOALKEEPER", "KEEPER", "GK"].includes(q) && p === "GK") return true;
  return false;
}

function searchPlayers(args: Record<string, unknown>): string {
  const nameQ = typeof args.name === "string" ? args.name.toLowerCase().trim() : "";
  const nationalityQ =
    typeof args.nationality === "string" ? args.nationality.toLowerCase().trim() : "";
  const clubQ = typeof args.club === "string" ? args.club.toLowerCase().trim() : "";
  const positionQ = typeof args.position === "string" ? args.position.trim() : "";
  const minOverall = typeof args.min_overall === "number" ? args.min_overall : 0;
  const maxOverall = typeof args.max_overall === "number" ? args.max_overall : 99;
  const limit = Math.min(typeof args.limit === "number" ? args.limit : 20, 100);

  let players = loadPlayers();

  if (nameQ) {
    players = players.filter((p) => p.name.toLowerCase().includes(nameQ));
  }
  if (nationalityQ) {
    players = players.filter((p) => p.nationality.toLowerCase().includes(nationalityQ));
  }
  if (clubQ) {
    players = players.filter((p) => p.club.toLowerCase().includes(clubQ));
  }
  if (positionQ) {
    players = players.filter((p) => positionMatchesQuery(p.position, positionQ));
  }
  if (minOverall > 0) {
    players = players.filter((p) => p.overall >= minOverall);
  }
  if (maxOverall < 99) {
    players = players.filter((p) => p.overall <= maxOverall);
  }

  if (!players.length) return "No players found for the given criteria.";

  // Sort by overall desc
  players.sort((a, b) => b.overall - a.overall);

  const total = players.length;
  const shown = players.slice(0, limit);

  const lines = shown.map(
    (p, i) =>
      `${i + 1}. ${p.name} | Overall: ${p.overall} | Potential: ${p.potential} | ` +
      `Pos: ${p.position} | Club: ${p.club} | Nationality: ${p.nationality}` +
      (p.age ? ` | Age: ${p.age}` : "") +
      (p.value ? ` | Value: ${p.value}` : "")
  );

  let result = `Found ${total} player${total !== 1 ? "s" : ""}`;
  if (total > limit) result += ` (showing top ${limit} by overall rating)`;
  result += ":\n\n" + lines.join("\n");
  return result;
}

// ---------------------------------------------------------------------------
// Tool: get_standings
// ---------------------------------------------------------------------------

interface Standing {
  team: string; // display name (raw)
  teamNorm: string; // normalized (for dedup)
  p: number; // played
  w: number;
  d: number;
  l: number;
  gf: number;
  ga: number;
  pts: number;
}

function getStandings(args: Record<string, unknown>): string {
  const season = typeof args.season === "number" ? args.season : 0;
  const limit = typeof args.limit === "number" ? Math.min(args.limit, 30) : 20;

  if (!season) return "season year is required.";

  // Prefer 'brasileirao' data for 2012+, 'historical' for pre-2012
  const comp = season >= 2012 ? "brasileirao" : "historical";
  const matches = loadMatches().filter(
    (m) => m.season === season && (m.competition === "brasileirao" || m.competition === "historical")
  );

  if (!matches.length) {
    return `No Brasileirão data found for season ${season}.`;
  }

  const table = new Map<string, Standing>();

  for (const m of matches) {
    // Only include main-season source for the year
    if (
      (season >= 2012 && m.competition !== "brasileirao") ||
      (season < 2012 && m.competition !== "historical")
    ) {
      continue;
    }

    const updateTeam = (rawName: string, gf: number, ga: number) => {
      // Use raw name as key — within a single season/source, names are consistent.
      // Normalizing would merge distinct clubs like "Atletico-MG" and "Atletico-PR".
      const key = rawName;
      if (!table.has(key)) {
        table.set(key, { team: rawName, teamNorm: normalizeTeam(rawName), p: 0, w: 0, d: 0, l: 0, gf: 0, ga: 0, pts: 0 });
      }
      const row = table.get(key)!;
      row.p++;
      row.gf += gf;
      row.ga += ga;
      if (gf > ga) { row.w++; row.pts += 3; }
      else if (gf === ga) { row.d++; row.pts += 1; }
      else row.l++;
    };

    updateTeam(m.homeTeam, m.homeGoals, m.awayGoals);
    updateTeam(m.awayTeam, m.awayGoals, m.homeGoals);
  }

  const rows = [...table.values()].sort((a, b) => {
    if (b.pts !== a.pts) return b.pts - a.pts;
    if (b.w !== a.w) return b.w - a.w;
    const gdA = a.gf - a.ga, gdB = b.gf - b.ga;
    if (gdB !== gdA) return gdB - gdA;
    return b.gf - a.gf;
  });

  const display = rows.slice(0, limit);

  let result = `${season} Brasileirão Série A Standings (${comp} data)\n`;
  result += `(Calculated from ${matches.filter(
    (m) =>
      (season >= 2012 && m.competition === "brasileirao") ||
      (season < 2012 && m.competition === "historical")
  ).length} matches)\n\n`;
  result += "Pos  Team                          P   W   D   L   GF  GA  GD  Pts\n";
  result += "─────────────────────────────────────────────────────────────────────\n";

  display.forEach((row, i) => {
    const gd = row.gf - row.ga;
    const gdStr = gd >= 0 ? "+" + gd : String(gd);
    result +=
      `${String(i + 1).padStart(3)}  ` +
      `${row.team.padEnd(30).slice(0, 30)}  ` +
      `${String(row.p).padStart(2)}  ${String(row.w).padStart(2)}  ` +
      `${String(row.d).padStart(2)}  ${String(row.l).padStart(2)}  ` +
      `${String(row.gf).padStart(3)} ${String(row.ga).padStart(3)} ` +
      `${gdStr.padStart(4)}  ${String(row.pts).padStart(3)}\n`;
  });

  if (display.length > 0) {
    result += `\nChampion: ${display[0].team} (${display[0].pts} pts)`;
    if (display.length >= 20) {
      const relegated = display.slice(-4).map((r) => r.team).join(", ");
      result += `\nRelegated: ${relegated}`;
    }
  }

  return result;
}

// ---------------------------------------------------------------------------
// Tool: get_biggest_wins
// ---------------------------------------------------------------------------

function getBiggestWins(args: Record<string, unknown>): string {
  const competition = typeof args.competition === "string" ? args.competition : "all";
  const season = typeof args.season === "number" ? args.season : 0;
  const limit = typeof args.limit === "number" ? Math.min(args.limit, 50) : 10;

  let matches = loadMatches();

  if (competition !== "all") {
    matches = matches.filter((m) => matchesCompetition(m, competition));
  }
  if (season) {
    matches = matches.filter((m) => m.season === season);
  }

  // Sort by goal margin desc
  matches.sort((a, b) => {
    const mA = Math.abs(a.homeGoals - a.awayGoals);
    const mB = Math.abs(b.homeGoals - b.awayGoals);
    if (mB !== mA) return mB - mA;
    return a.date > b.date ? -1 : 1;
  });

  const shown = matches.slice(0, limit);
  if (!shown.length) return "No matches found for the given criteria.";

  const lines = shown.map((m, i) => {
    const margin = Math.abs(m.homeGoals - m.awayGoals);
    const winner = m.homeGoals > m.awayGoals ? m.homeTeam : m.awayTeam;
    return `${i + 1}. ${matchLine(m)} (margin: ${margin}, winner: ${winner})`;
  });

  return `Biggest wins${competition !== "all" ? " in " + competition : ""}${season ? " " + season : ""}:\n\n` + lines.join("\n");
}

// ---------------------------------------------------------------------------
// Tool: get_league_overview
// ---------------------------------------------------------------------------

function getLeagueOverview(args: Record<string, unknown>): string {
  const competition = typeof args.competition === "string" ? args.competition : "all";
  const season = typeof args.season === "number" ? args.season : 0;

  let matches = loadMatches();

  if (competition !== "all") {
    matches = matches.filter((m) => matchesCompetition(m, competition));
  }
  if (season) {
    matches = matches.filter((m) => m.season === season);
  }

  if (!matches.length) return "No matches found for the given criteria.";

  const total = matches.length;
  const totalGoals = matches.reduce((s, m) => s + m.homeGoals + m.awayGoals, 0);
  const homeWins = matches.filter((m) => m.homeGoals > m.awayGoals).length;
  const awayWins = matches.filter((m) => m.awayGoals > m.homeGoals).length;
  const draws = matches.filter((m) => m.homeGoals === m.awayGoals).length;

  // Seasons covered
  const seasons = [...new Set(matches.map((m) => m.season))].sort();
  const seasonsStr =
    seasons.length > 5 ? `${seasons[0]}–${seasons[seasons.length - 1]}` : seasons.join(", ");

  // Top scoring matches
  const topScoring = [...matches]
    .sort((a, b) => b.homeGoals + b.awayGoals - (a.homeGoals + a.awayGoals))
    .slice(0, 3)
    .map((m) => `  ${matchLine(m)} (${m.homeGoals + m.awayGoals} goals)`)
    .join("\n");

  const compLabel = competition !== "all" ? competition : "All competitions";
  const seasonLabel = season ? ` (${season})` : ` (${seasonsStr})`;

  let result = `${compLabel}${seasonLabel} Overview\n`;
  result += `${"─".repeat(50)}\n`;
  result += `Total matches:     ${total}\n`;
  result += `Total goals:       ${totalGoals}\n`;
  result += `Avg goals/match:   ${(totalGoals / total).toFixed(2)}\n`;
  result += `Home wins:         ${homeWins} (${pct(homeWins, total)})\n`;
  result += `Away wins:         ${awayWins} (${pct(awayWins, total)})\n`;
  result += `Draws:             ${draws} (${pct(draws, total)})\n`;

  if (competition !== "all" || season) {
    result += `\nHighest-scoring matches:\n${topScoring}`;
  }

  return result;
}

// ---------------------------------------------------------------------------
// Tool: list_teams
// ---------------------------------------------------------------------------

function listTeams(args: Record<string, unknown>): string {
  const competition = typeof args.competition === "string" ? args.competition : "all";
  const search = typeof args.search === "string" ? args.search.toLowerCase().trim() : "";

  let matches = loadMatches();

  if (competition !== "all") {
    matches = matches.filter((m) => matchesCompetition(m, competition));
  }

  // Collect unique normalized team names, keeping a canonical raw display name
  const teamMap = new Map<string, string>();
  for (const m of matches) {
    for (const raw of [m.homeTeam, m.awayTeam]) {
      if (!raw) continue;
      const key = normalizeTeam(raw);
      if (!teamMap.has(key)) teamMap.set(key, raw);
    }
  }

  let teams = [...teamMap.entries()].sort((a, b) => a[0].localeCompare(b[0]));

  if (search) {
    teams = teams.filter(([key]) => key.includes(search));
  }

  if (!teams.length) return "No teams found.";

  const total = teams.length;
  const displayTeams = teams.slice(0, 200); // hard cap for readability

  const compStr = competition !== "all" ? ` in ${competition}` : "";
  let result = `${total} unique team${total !== 1 ? "s" : ""}${compStr}`;
  if (search) result += ` matching "${search}"`;
  result += ":\n\n" + displayTeams.map(([, raw]) => raw).join("\n");
  if (total > 200) result += `\n... and ${total - 200} more`;
  return result;
}
