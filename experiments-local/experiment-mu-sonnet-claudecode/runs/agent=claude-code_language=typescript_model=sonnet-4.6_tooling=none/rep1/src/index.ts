import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

import {
  loadBrasileiraoMatches,
  loadCupMatches,
  loadLibertadoresMatches,
  loadExtendedMatches,
  loadHistoricalMatches,
  loadFifaPlayers,
  buildNormalizedMatches,
} from "./data-loader.js";

import {
  searchMatches,
  getTeamStats,
  headToHead,
  getStandings,
  searchPlayers,
  getGlobalStats,
  getBiggestWins,
  getExtendedStats,
} from "./query-engine.js";

import type { Database } from "./query-engine.js";
import type { NormalizedMatch, FifaPlayer, TeamStats } from "./types.js";

// Load all data at startup
console.error("Loading Brazilian soccer data...");
const brasileirao = loadBrasileiraoMatches();
const cup = loadCupMatches();
const libertadores = loadLibertadoresMatches();
const extended = loadExtendedMatches();
const historical = loadHistoricalMatches();
const players = loadFifaPlayers();
const matches = buildNormalizedMatches(brasileirao, cup, libertadores, historical);

const db: Database = { matches, extended, players };
console.error(
  `Loaded: ${matches.length} matches, ${players.length} players, ${extended.length} extended records`
);

// Formatters
function formatMatch(m: NormalizedMatch): string {
  const score = `${m.home_goal}-${m.away_goal}`;
  const comp = m.stage ? `${m.competition} (${m.stage})` : m.competition;
  const round = m.round ? ` Round ${m.round}` : "";
  return `${m.date}: ${m.home_team} ${score} ${m.away_team} [${comp}${round}]`;
}

function formatPlayer(p: FifaPlayer): string {
  return `${p.Name} | ${p.Nationality} | ${p.Position} | Overall: ${p.Overall} | Club: ${p.Club} | Age: ${p.Age}`;
}

function formatStats(s: TeamStats): string {
  const winRate = s.matches > 0 ? ((s.wins / s.matches) * 100).toFixed(1) : "0.0";
  return [
    `Team: ${s.team}`,
    `Matches: ${s.matches} | W: ${s.wins} D: ${s.draws} L: ${s.losses}`,
    `Goals: ${s.goals_for} for, ${s.goals_against} against (GD: ${s.goal_difference > 0 ? "+" : ""}${s.goal_difference})`,
    `Points: ${s.points} | Win rate: ${winRate}%`,
  ].join("\n");
}

// MCP server setup
const server = new Server(
  { name: "brazilian-soccer-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "search_matches",
      description:
        "Search for matches by team, date range, competition, or season. Returns match results with scores.",
      inputSchema: {
        type: "object",
        properties: {
          team: { type: "string", description: "Team name (searches both home and away)" },
          home_team: { type: "string", description: "Specific home team" },
          away_team: { type: "string", description: "Specific away team" },
          opponent: { type: "string", description: "Opponent team (use with team for H2H)" },
          season: { type: "number", description: "Season year (e.g. 2023)" },
          competition: {
            type: "string",
            description: "Competition: 'Brasileirao', 'Copa do Brasil', 'Libertadores', or partial match",
          },
          date_from: { type: "string", description: "Start date YYYY-MM-DD" },
          date_to: { type: "string", description: "End date YYYY-MM-DD" },
          limit: { type: "number", description: "Max results (default 20)" },
        },
      },
    },
    {
      name: "get_team_stats",
      description:
        "Get win/loss/draw statistics, goals, and points for a team. Optionally filter by season or competition.",
      inputSchema: {
        type: "object",
        properties: {
          team: { type: "string", description: "Team name" },
          season: { type: "number", description: "Season year" },
          competition: { type: "string", description: "Competition name or partial match" },
          home_only: { type: "boolean", description: "Only count home matches" },
          away_only: { type: "boolean", description: "Only count away matches" },
        },
        required: ["team"],
      },
    },
    {
      name: "head_to_head",
      description: "Compare two teams head-to-head: all matches, wins, draws, goals.",
      inputSchema: {
        type: "object",
        properties: {
          team1: { type: "string", description: "First team" },
          team2: { type: "string", description: "Second team" },
          season: { type: "number", description: "Filter by season" },
          competition: { type: "string", description: "Filter by competition" },
          limit: { type: "number", description: "Max matches to show (default 20)" },
        },
        required: ["team1", "team2"],
      },
    },
    {
      name: "get_standings",
      description:
        "Calculate league standings for a given season and competition based on match results.",
      inputSchema: {
        type: "object",
        properties: {
          season: { type: "number", description: "Season year (e.g. 2019)" },
          competition: { type: "string", description: "Competition filter (default: Brasileirao)" },
        },
        required: ["season"],
      },
    },
    {
      name: "search_players",
      description:
        "Search FIFA player database by name, nationality, club, or position. Returns ratings and attributes.",
      inputSchema: {
        type: "object",
        properties: {
          name: { type: "string", description: "Player name (partial match)" },
          nationality: { type: "string", description: "Nationality (e.g. 'Brazilian')" },
          club: { type: "string", description: "Club name (partial match)" },
          position: { type: "string", description: "Position (e.g. 'ST', 'GK', 'CB')" },
          min_overall: { type: "number", description: "Minimum overall rating" },
          max_age: { type: "number", description: "Maximum age" },
          limit: { type: "number", description: "Max results (default 20)" },
        },
      },
    },
    {
      name: "get_global_stats",
      description: "Get global statistics: total matches, average goals, home win rates.",
      inputSchema: {
        type: "object",
        properties: {
          competition: { type: "string", description: "Filter by competition" },
        },
      },
    },
    {
      name: "get_biggest_wins",
      description: "Get the biggest wins (largest goal margins) across all matches.",
      inputSchema: {
        type: "object",
        properties: {
          limit: { type: "number", description: "Number of results (default 10)" },
          competition: { type: "string", description: "Filter by competition" },
        },
      },
    },
    {
      name: "get_extended_match_stats",
      description:
        "Get extended match statistics (corners, shots, attacks) for a team from the BR-Football dataset.",
      inputSchema: {
        type: "object",
        properties: {
          team: { type: "string", description: "Team name" },
          limit: { type: "number", description: "Max results (default 10)" },
        },
        required: ["team"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args = {} } = request.params;

  try {
    switch (name) {
      case "search_matches": {
        const limit = (args.limit as number | undefined) ?? 20;
        const results = searchMatches(db, {
          team: args.team as string | undefined,
          homeTeam: args.home_team as string | undefined,
          awayTeam: args.away_team as string | undefined,
          opponent: args.opponent as string | undefined,
          season: args.season as number | undefined,
          competition: args.competition as string | undefined,
          dateFrom: args.date_from as string | undefined,
          dateTo: args.date_to as string | undefined,
          limit,
        });

        if (results.length === 0) {
          return { content: [{ type: "text", text: "No matches found matching the criteria." }] };
        }

        const total = db.matches.filter((m) => {
          // Quick recount without limit
          if (args.team && !searchMatches(db, { team: args.team as string }).some((r) => r === m)) return false;
          return true;
        }).length;

        const text = [
          `Found ${results.length} match${results.length !== 1 ? "es" : ""}${results.length < limit ? "" : ` (showing top ${limit})`}:`,
          ...results.map(formatMatch),
        ].join("\n");

        return { content: [{ type: "text", text }] };
      }

      case "get_team_stats": {
        const team = args.team as string;
        const stats = getTeamStats(db, team, {
          season: args.season as number | undefined,
          competition: args.competition as string | undefined,
          homeOnly: args.home_only as boolean | undefined,
          awayOnly: args.away_only as boolean | undefined,
        });

        if (stats.matches === 0) {
          return { content: [{ type: "text", text: `No matches found for team "${team}".` }] };
        }

        return { content: [{ type: "text", text: formatStats(stats) }] };
      }

      case "head_to_head": {
        const team1 = args.team1 as string;
        const team2 = args.team2 as string;
        const limit = (args.limit as number | undefined) ?? 20;
        const result = headToHead(db, team1, team2, {
          season: args.season as number | undefined,
          competition: args.competition as string | undefined,
          limit,
        });

        if (result.matches.length === 0) {
          return {
            content: [{ type: "text", text: `No head-to-head matches found between "${team1}" and "${team2}".` }],
          };
        }

        const total_matches = result.team1_wins + result.team2_wins + result.draws;
        const text = [
          `Head-to-Head: ${team1} vs ${team2}`,
          `Total matches: ${total_matches}`,
          `${team1} wins: ${result.team1_wins} | ${team2} wins: ${result.team2_wins} | Draws: ${result.draws}`,
          `Goals: ${team1} ${result.team1_goals} - ${result.team2_goals} ${team2}`,
          "",
          `Recent matches (${result.matches.length} shown):`,
          ...result.matches.map(formatMatch),
        ].join("\n");

        return { content: [{ type: "text", text }] };
      }

      case "get_standings": {
        const season = args.season as number;
        const competition = (args.competition as string | undefined) ?? "Brasileirao";
        const standings = getStandings(db, season, competition);

        if (standings.length === 0) {
          return {
            content: [{ type: "text", text: `No standings data found for season ${season}.` }],
          };
        }

        const rows = standings.map((s, i) => {
          const gd = s.goal_difference >= 0 ? `+${s.goal_difference}` : `${s.goal_difference}`;
          return `${String(i + 1).padStart(2)}. ${s.team.padEnd(30)} ${String(s.points).padStart(3)}pts  ${s.wins}W ${s.draws}D ${s.losses}L  GD: ${gd}`;
        });

        const text = [
          `${season} Standings (${competition}):`,
          "Pos  Team                           Pts  Record        GD",
          ...rows,
        ].join("\n");

        return { content: [{ type: "text", text }] };
      }

      case "search_players": {
        const limit = (args.limit as number | undefined) ?? 20;
        const results = searchPlayers(db, {
          name: args.name as string | undefined,
          nationality: args.nationality as string | undefined,
          club: args.club as string | undefined,
          position: args.position as string | undefined,
          minOverall: args.min_overall as number | undefined,
          maxAge: args.max_age as number | undefined,
          limit,
        });

        if (results.length === 0) {
          return { content: [{ type: "text", text: "No players found matching the criteria." }] };
        }

        const text = [
          `Found ${results.length} player${results.length !== 1 ? "s" : ""}:`,
          ...results.map(formatPlayer),
        ].join("\n");

        return { content: [{ type: "text", text }] };
      }

      case "get_global_stats": {
        const competition = args.competition as string | undefined;
        const stats = getGlobalStats(db, competition);

        const text = [
          competition ? `Global stats for ${competition}:` : "Global stats (all competitions):",
          `Total matches: ${stats.total_matches.toLocaleString()}`,
          `Total goals: ${stats.total_goals.toLocaleString()}`,
          `Average goals/match: ${stats.avg_goals_per_match}`,
          `Home wins: ${stats.home_wins} (${stats.home_win_rate}%)`,
          `Away wins: ${stats.away_wins}`,
          `Draws: ${stats.draws}`,
        ].join("\n");

        return { content: [{ type: "text", text }] };
      }

      case "get_biggest_wins": {
        const limit = (args.limit as number | undefined) ?? 10;
        const competition = args.competition as string | undefined;
        const wins = getBiggestWins(db, limit, competition);

        if (wins.length === 0) {
          return { content: [{ type: "text", text: "No match data found." }] };
        }

        const text = [
          "Biggest wins by goal margin:",
          ...wins.map(
            (m, i) =>
              `${i + 1}. ${formatMatch(m)} (margin: ${m.margin})`
          ),
        ].join("\n");

        return { content: [{ type: "text", text }] };
      }

      case "get_extended_match_stats": {
        const team = args.team as string;
        const limit = (args.limit as number | undefined) ?? 10;
        const results = getExtendedStats(db, team, { limit });

        if (results.length === 0) {
          return { content: [{ type: "text", text: `No extended stats found for "${team}".` }] };
        }

        const text = [
          `Extended match stats for ${team} (${results.length} matches):`,
          ...results.map(
            (m) =>
              `${m.date} [${m.tournament}]: ${m.home} ${m.home_goal}-${m.away_goal} ${m.away} | Shots: ${m.home_shots}-${m.away_shots} | Corners: ${m.home_corner}-${m.away_corner}`
          ),
        ].join("\n");

        return { content: [{ type: "text", text }] };
      }

      default:
        return { content: [{ type: "text", text: `Unknown tool: ${name}` }] };
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return { content: [{ type: "text", text: `Error: ${message}` }] };
  }
});

// Start server
const transport = new StdioServerTransport();
await server.connect(transport);
console.error("Brazilian Soccer MCP server running on stdio");
