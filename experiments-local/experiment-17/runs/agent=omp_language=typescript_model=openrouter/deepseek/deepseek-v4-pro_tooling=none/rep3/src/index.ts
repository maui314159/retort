#!/usr/bin/env node

/**
 * Brazilian Soccer MCP Server
 *
 * MCP server providing knowledge graph interface for Brazilian soccer data.
 * Supports queries about matches, teams, players, competitions, and statistics
 * across 6 CSV datasets from data/kaggle/.
 *
 * Tools exposed:
 *   - search_matches: Find matches by team, season, competition, date range, round
 *   - get_team_stats: Get comprehensive statistics for a team
 *   - get_head_to_head: Compare two teams head-to-head
 *   - get_standings: Compute league standings for a season
 *   - get_biggest_wins: Find biggest victories
 *   - get_goal_averages: Get goal/match averages
 *   - get_home_away_stats: Home vs away performance for a team
 *   - search_players: Search FIFA player data by name, nationality, club, position, rating
 *   - get_player_details: Get detailed info for a specific player
 *   - get_top_players: Get top-rated players, optionally filtered
 *   - get_club_summaries: Get player counts and avg ratings by club
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import {
  searchMatches,
  getTeamStats,
  getHeadToHead,
  getStandings,
  getBiggestWins,
  getGoalAverages,
  getHomeAwayStats,
} from "./match-db.js";
import {
  searchPlayers,
  getPlayerDetails,
  getTopPlayers,
  getClubSummaries,
  formatPlayer,
  formatPlayerCompact,
} from "./player-db.js";

// --- Create Server ---

const server = new McpServer({
  name: "brazilian-soccer-mcp",
  version: "1.0.0",
  description: "MCP server providing knowledge graph interface for Brazilian soccer data",
});

// ============================================================================
// MATCH TOOLS
// ============================================================================

server.registerTool(
  "search_matches",
  {
    description:
      "Search for soccer matches by team, season, competition, date range, or round. " +
      "Returns matches sorted by date (most recent first). " +
      "You can filter by team (either home or away), home team only, away team only, " +
      "season, competition (Brasileirão, Copa do Brasil, Libertadores), date range, and round/stage.",
    inputSchema: {
      team: z.string().optional().describe("Team name to search for (home or away, partial match supported)"),
      home_team: z.string().optional().describe("Filter to matches where this team was at home"),
      away_team: z.string().optional().describe("Filter to matches where this team was away"),
      season: z.number().optional().describe("Season year (e.g. 2023)"),
      competition: z.string().optional().describe("Competition name (e.g. Brasileirão, Copa do Brasil, Libertadores)"),
      date_from: z.string().optional().describe("Earliest date (YYYY-MM-DD format)"),
      date_to: z.string().optional().describe("Latest date (YYYY-MM-DD format)"),
      round: z.string().optional().describe("Round or stage (e.g. final, semifinals, 1)"),
      limit: z.number().optional().default(50).describe("Maximum number of matches to return"),
    },
  },
  async ({ team, home_team, away_team, season, competition, date_from, date_to, round, limit }) => {
    const matches = searchMatches({
      team,
      homeTeam: home_team,
      awayTeam: away_team,
      season,
      competition,
      dateFrom: date_from,
      dateTo: date_to,
      round,
      limit,
    });

    if (matches.length === 0) {
      return {
        content: [{ type: "text", text: "No matches found matching your criteria." }],
      };
    }

    const lines: string[] = [`Found ${matches.length} match(es):\n`];

    for (const m of matches) {
      const roundStr = m.round ? ` (${m.competition} ${typeof m.round === "string" ? capitalize(m.round) : `Round ${m.round}`})` : ` (${m.competition})`;
      lines.push(
        `${m.date}: ${m.home_team} ${m.home_goal}-${m.away_goal} ${m.away_team}${roundStr}`,
      );
    }

    return {
      content: [{ type: "text", text: lines.join("\n") }],
    };
  },
);

server.registerTool(
  "get_team_stats",
  {
    description:
      "Get comprehensive statistics for a team including wins, losses, draws, goals, win rate, " +
      "and competitions played. Optionally filter by season and competition.",
    inputSchema: {
      team: z.string().describe("Team name (e.g. Flamengo, Palmeiras, Corinthians)"),
      season: z.number().optional().describe("Filter to a specific season year"),
      competition: z.string().optional().describe("Filter to a specific competition"),
    },
  },
  async ({ team, season, competition }) => {
    const stats = getTeamStats(team, season, competition);

    if (stats.matches === 0) {
      return {
        content: [{ type: "text", text: `No matches found for team "${team}". Try a different name.` }],
      };
    }

    const lines: string[] = [];
    lines.push(`${stats.team} Statistics:`);
    if (season) lines.push(`Season: ${season}`);
    if (competition) lines.push(`Competition: ${competition}`);
    lines.push("");
    lines.push(`  Matches: ${stats.matches}`);
    lines.push(`  Wins: ${stats.wins} | Draws: ${stats.draws} | Losses: ${stats.losses}`);
    lines.push(`  Goals For: ${stats.goalsFor} | Goals Against: ${stats.goalsAgainst} | GD: ${stats.goalDiff >= 0 ? "+" : ""}${stats.goalDiff}`);
    lines.push(`  Win Rate: ${(stats.winRate * 100).toFixed(1)}%`);
    lines.push(`  Competitions: ${stats.competitions.join(", ")}`);
    lines.push(`  Seasons: ${stats.seasons.join(", ")}`);

    return {
      content: [{ type: "text", text: lines.join("\n") }],
    };
  },
);

server.registerTool(
  "get_head_to_head",
  {
    description:
      "Compare two teams head-to-head. Returns the win/loss/draw record and a list of all matches between them.",
    inputSchema: {
      team1: z.string().describe("First team name"),
      team2: z.string().describe("Second team name"),
      limit: z.number().optional().default(20).describe("Maximum recent matches to show"),
    },
  },
  async ({ team1, team2, limit }) => {
    const h2h = getHeadToHead(team1, team2);

    if (h2h.totalMatches === 0) {
      return {
        content: [{ type: "text", text: `No matches found between "${team1}" and "${team2}". Try different names.` }],
      };
    }

    const lines: string[] = [];
    lines.push(`${h2h.team1} vs ${h2h.team2} - Head to Head:`);
    lines.push("");
    lines.push(`  Total matches: ${h2h.totalMatches}`);
    lines.push(`  ${h2h.team1} wins: ${h2h.team1Wins}`);
    lines.push(`  ${h2h.team2} wins: ${h2h.team2Wins}`);
    lines.push(`  Draws: ${h2h.draws}`);
    lines.push("");

    const recentMatches = h2h.matches.slice(0, limit);
    lines.push("Recent matches:");
    for (const m of recentMatches) {
      const comp = `${m.competition}${m.round ? ` ${typeof m.round === "string" ? capitalize(m.round) : `R${m.round}`}` : ""}`;
      lines.push(`  ${m.date}: ${m.home_team} ${m.home_goal}-${m.away_goal} ${m.away_team} (${comp})`);
    }

    return {
      content: [{ type: "text", text: lines.join("\n") }],
    };
  },
);

server.registerTool(
  "get_standings",
  {
    description:
      "Compute the league standings for a given season by processing match results. " +
      "Uses 3 points for a win, 1 for a draw. Sorted by points, then wins, then goal difference.",
    inputSchema: {
      season: z.number().describe("Season year (e.g. 2019, 2023)"),
      competition: z.string().optional().describe("Competition (defaults to Brasileirão if not specified)"),
    },
  },
  async ({ season, competition }) => {
    const standings = getStandings(season, competition);

    if (standings.length === 0) {
      return {
        content: [{ type: "text", text: `No standings found for season ${season}${competition ? ` in ${competition}` : ""}.` }],
      };
    }

    const lines: string[] = [];
    const compName = competition || "Brasileirão";
    lines.push(`${season} ${compName} Standings:`);
    lines.push("");
    lines.push(`${"#".padEnd(3)} ${"Team".padEnd(20)} ${"Pts".padEnd(4)} ${"P".padEnd(3)} ${"W".padEnd(3)} ${"D".padEnd(3)} ${"L".padEnd(3)} ${"GF".padEnd(4)} ${"GA".padEnd(4)} ${"GD".padEnd(4)}`);
    lines.push("-".repeat(65));

    for (const s of standings) {
      const gd = s.goalDiff >= 0 ? `+${s.goalDiff}` : `${s.goalDiff}`;
      lines.push(
        `${String(s.position).padEnd(3)} ${s.team.substring(0, 19).padEnd(20)} ${String(s.points).padEnd(4)} ${String(s.played).padEnd(3)} ${String(s.wins).padEnd(3)} ${String(s.draws).padEnd(3)} ${String(s.losses).padEnd(3)} ${String(s.goalsFor).padEnd(4)} ${String(s.goalsAgainst).padEnd(4)} ${gd.padEnd(4)}`,
      );
    }

    // Highlight champion and relegation zone (4 teams for Brasileirão)
    if (standings.length >= 4) {
      lines.push("");
      lines.push(`Champion: ${standings[0].team} (${standings[0].points} pts)`);
      const relegation = standings.slice(-4).reverse();
      lines.push(`Relegated: ${relegation.map((s) => s.team).join(", ")}`);
    }

    return {
      content: [{ type: "text", text: lines.join("\n") }],
    };
  },
);

server.registerTool(
  "get_biggest_wins",
  {
    description: "Find the biggest victories in the dataset (goal difference >= 5).",
    inputSchema: {
      limit: z.number().optional().default(10).describe("Number of results to return"),
      competition: z.string().optional().describe("Filter to a specific competition"),
    },
  },
  async ({ limit, competition }) => {
    let wins = getBiggestWins(limit);

    if (competition) {
      const c = competition.toLowerCase();
      wins = wins.filter((m) => m.competition.toLowerCase().includes(c));
      wins = wins.slice(0, limit);
    }

    if (wins.length === 0) {
      return {
        content: [{ type: "text", text: "No big wins found." }],
      };
    }

    const lines: string[] = ["Biggest Victories:"];
    lines.push("");

    for (let i = 0; i < wins.length; i++) {
      const m = wins[i];
      const diff = Math.abs(m.home_goal - m.away_goal);
      const winner = m.home_goal > m.away_goal ? m.home_team : m.away_team;
      const loser = m.home_goal > m.away_goal ? m.away_team : m.home_team;
      const winnerGoals = m.home_goal > m.away_goal ? m.home_goal : m.away_goal;
      const loserGoals = m.home_goal > m.away_goal ? m.away_goal : m.home_goal;
      lines.push(
        `${i + 1}. ${m.date}: ${winner} ${winnerGoals}-${loserGoals} ${loser} (${m.competition}, GD ${diff})`,
      );
    }

    return {
      content: [{ type: "text", text: lines.join("\n") }],
    };
  },
);

server.registerTool(
  "get_goal_averages",
  {
    description: "Get goal-per-match averages, home win rate, draw rate, and away win rate.",
    inputSchema: {
      competition: z.string().optional().describe("Filter to a specific competition"),
    },
  },
  async ({ competition }) => {
    const stats = getGoalAverages(competition);

    const lines: string[] = [];
    lines.push(`Match Statistics${competition ? ` for ${competition}` : ""}:`);
    lines.push("");
    lines.push(`  Total matches: ${stats.totalMatches}`);
    lines.push(`  Average goals per match: ${stats.avgGoalsPerMatch.toFixed(2)}`);
    lines.push(`  Home win rate: ${(stats.homeWinRate * 100).toFixed(1)}%`);
    lines.push(`  Draw rate: ${(stats.drawRate * 100).toFixed(1)}%`);
    lines.push(`  Away win rate: ${(stats.awayWinRate * 100).toFixed(1)}%`);

    return {
      content: [{ type: "text", text: lines.join("\n") }],
    };
  },
);

server.registerTool(
  "get_home_away_stats",
  {
    description: "Compare a team's home vs away performance. Returns separate stats for home matches, away matches, and overall.",
    inputSchema: {
      team: z.string().describe("Team name"),
      season: z.number().optional().describe("Filter to a specific season"),
      competition: z.string().optional().describe("Filter to a specific competition"),
    },
  },
  async ({ team, season, competition }) => {
    const stats = getHomeAwayStats(team, season, competition);

    if (stats.overall.matches === 0) {
      return {
        content: [{ type: "text", text: `No matches found for team "${team}".` }],
      };
    }

    const lines: string[] = [];
    lines.push(`${stats.overall.team} - Home vs Away Performance:`);
    if (season) lines.push(`Season: ${season}`);
    if (competition) lines.push(`Competition: ${competition}`);
    lines.push("");

    const fmt = (s: typeof stats.home) =>
      `  M: ${s.matches} | W: ${s.wins} | D: ${s.draws} | L: ${s.losses} | GF: ${s.goalsFor} | GA: ${s.goalsAgainst} | Win%: ${(s.winRate * 100).toFixed(1)}%`;

    lines.push("HOME:");
    lines.push(fmt(stats.home));
    lines.push("");
    lines.push("AWAY:");
    lines.push(fmt(stats.away));
    lines.push("");
    lines.push("OVERALL:");
    lines.push(fmt(stats.overall));

    return {
      content: [{ type: "text", text: lines.join("\n") }],
    };
  },
);

// ============================================================================
// PLAYER TOOLS
// ============================================================================

server.registerTool(
  "search_players",
  {
    description:
      "Search FIFA player database by name, nationality, club, position, and rating range. " +
      "Returns players sorted by overall rating (descending).",
    inputSchema: {
      name: z.string().optional().describe("Player name (partial match)"),
      nationality: z.string().optional().describe("Nationality (e.g. Brazil, Argentina)"),
      club: z.string().optional().describe("Club name (partial match, e.g. Flamengo, Real Madrid)"),
      position: z.string().optional().describe("Position (e.g. ST, GK, LW, CDM)"),
      min_overall: z.number().optional().describe("Minimum overall rating (0-99)"),
      max_overall: z.number().optional().describe("Maximum overall rating (0-99)"),
      sort_by: z.enum(["overall", "potential", "age", "name"]).optional().default("overall").describe("Sort field"),
      limit: z.number().optional().default(20).describe("Maximum number of players to return"),
    },
  },
  async ({ name, nationality, club, position, min_overall, max_overall, sort_by, limit }) => {
    const players = searchPlayers({
      name,
      nationality,
      club,
      position,
      minOverall: min_overall,
      maxOverall: max_overall,
      sortBy: sort_by,
      sortDir: "desc",
      limit,
    });

    if (players.length === 0) {
      return {
        content: [{ type: "text", text: "No players found matching your criteria." }],
      };
    }

    const lines: string[] = [`Found ${players.length} player(s):\n`];

    for (let i = 0; i < players.length; i++) {
      const p = players[i];
      lines.push(`${i + 1}. ${formatPlayerCompact(p)}`);
    }

    return {
      content: [{ type: "text", text: lines.join("\n") }],
    };
  },
);

server.registerTool(
  "get_player_details",
  {
    description:
      "Get detailed information about a specific player including ratings, attributes, and career info.",
    inputSchema: {
      name: z.string().describe("Player name to search for (e.g. Neymar Jr, Gabriel Barbosa)"),
    },
  },
  async ({ name }) => {
    const player = getPlayerDetails(name);

    if (!player) {
      return {
        content: [{ type: "text", text: `No player found matching "${name}".` }],
      };
    }

    return {
      content: [{ type: "text", text: formatPlayer(player) }],
    };
  },
);

server.registerTool(
  "get_top_players",
  {
    description:
      "Get the top-rated players, optionally filtered by nationality or club.",
    inputSchema: {
      limit: z.number().optional().default(10).describe("Number of players to return"),
      nationality: z.string().optional().describe("Filter by nationality (e.g. Brazil)"),
      club: z.string().optional().describe("Filter by club"),
    },
  },
  async ({ limit, nationality, club }) => {
    const players = getTopPlayers(limit, nationality, club);

    const lines: string[] = [];
    lines.push(`Top ${players.length} players${nationality ? ` (${nationality})` : ""}${club ? ` at ${club}` : ""}:`);
    lines.push("");

    for (let i = 0; i < players.length; i++) {
      const p = players[i];
      lines.push(`${i + 1}. ${p.name} - Overall: ${p.overall}, Position: ${p.position}, Club: ${p.club}, Nationality: ${p.nationality}`);
    }

    return {
      content: [{ type: "text", text: lines.join("\n") }],
    };
  },
);

server.registerTool(
  "get_club_summaries",
  {
    description:
      "Get player counts and average ratings for clubs in the FIFA database. " +
      "Optionally filter by partial club name.",
    inputSchema: {
      club_filter: z.string().optional().describe("Partial club name to filter by (e.g. Flamengo, Real)"),
    },
  },
  async ({ club_filter }) => {
    const summaries = getClubSummaries(club_filter);

    if (summaries.length === 0) {
      return {
        content: [{ type: "text", text: "No clubs found matching the filter." }],
      };
    }

    const lines: string[] = [`Club summaries (${summaries.length} clubs found):\n`];

    for (const s of summaries.slice(0, 50)) {
      lines.push(
        `${s.club}: ${s.playerCount} players, Avg Rating: ${s.avgRating}, Top: ${s.topPlayer} (${s.topRating})`,
      );
    }

    if (summaries.length > 50) {
      lines.push(`\n... and ${summaries.length - 50} more clubs. Use club_filter to narrow results.`);
    }

    return {
      content: [{ type: "text", text: lines.join("\n") }],
    };
  },
);

// ============================================================================
// STARTUP
// ============================================================================

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

async function main() {
  // Pre-load data to avoid lazy loading during first query
  console.error("Brazilian Soccer MCP Server starting...");
  console.error("Loading match data...");
  const { getAllMatches } = await import("./match-db.js");
  const { getAllPlayers } = await import("./player-db.js");

  const matchCount = getAllMatches().length;
  const playerCount = getAllPlayers().length;
  console.error(`Loaded ${matchCount} matches and ${playerCount} players.`);

  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Brazilian Soccer MCP Server ready on stdio");
}

main().catch((error) => {
  console.error("Fatal error in main():", error);
  process.exit(1);
});