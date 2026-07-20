import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { getDataStore } from "./data-loader.js";
import { searchMatches, getHeadToHead, getBiggestWins } from "./tools/match-tools.js";
import { getTeamStats, getStandings, compareTeams, getBestHomeRecord } from "./tools/team-tools.js";
import { searchPlayers, getPlayerDetails, getBrazilianPlayersAtBrazilianClubs, getTopPlayers } from "./tools/player-tools.js";
import { getAggregateStats, getSeasonComparison, getMostGoals } from "./tools/stats-tools.js";

const server = new Server(
  { name: "brazilian-soccer-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "search_matches",
      description:
        "Search for soccer matches by team, competition, season, or date range. " +
        "Covers Brasileirão Serie A, Copa do Brasil, Copa Libertadores, and historical data.",
      inputSchema: {
        type: "object",
        properties: {
          team: { type: "string", description: "Team name (home or away)" },
          homeTeam: { type: "string", description: "Home team name" },
          awayTeam: { type: "string", description: "Away team name" },
          team2: { type: "string", description: "Second team for head-to-head search" },
          competition: {
            type: "string",
            description: "Competition: 'brasileirao', 'copa do brasil', 'libertadores'",
          },
          season: { type: "number", description: "Season year (e.g. 2023)" },
          dateFrom: { type: "string", description: "Start date (YYYY-MM-DD)" },
          dateTo: { type: "string", description: "End date (YYYY-MM-DD)" },
          limit: { type: "number", description: "Max results (default 50)" },
        },
      },
    },
    {
      name: "head_to_head",
      description: "Get head-to-head record and match history between two teams.",
      inputSchema: {
        type: "object",
        properties: {
          team1: { type: "string", description: "First team name" },
          team2: { type: "string", description: "Second team name" },
          competition: { type: "string", description: "Filter by competition" },
          season: { type: "number", description: "Filter by season year" },
        },
        required: ["team1", "team2"],
      },
    },
    {
      name: "get_team_stats",
      description: "Get win/loss/draw record, goals, and performance stats for a team.",
      inputSchema: {
        type: "object",
        properties: {
          team: { type: "string", description: "Team name" },
          competition: { type: "string", description: "Filter by competition" },
          season: { type: "number", description: "Filter by season year" },
          homeOnly: { type: "boolean", description: "Only home matches" },
          awayOnly: { type: "boolean", description: "Only away matches" },
        },
        required: ["team"],
      },
    },
    {
      name: "get_standings",
      description: "Get league standings calculated from match results for a given season.",
      inputSchema: {
        type: "object",
        properties: {
          season: { type: "number", description: "Season year" },
          competition: { type: "string", description: "Competition name (default: Brasileirão)" },
        },
        required: ["season"],
      },
    },
    {
      name: "compare_teams",
      description: "Compare overall statistics between two teams.",
      inputSchema: {
        type: "object",
        properties: {
          team1: { type: "string", description: "First team name" },
          team2: { type: "string", description: "Second team name" },
          season: { type: "number", description: "Filter by season year" },
        },
        required: ["team1", "team2"],
      },
    },
    {
      name: "get_best_home_record",
      description: "Find teams with the best home win records.",
      inputSchema: {
        type: "object",
        properties: {
          season: { type: "number", description: "Filter by season year" },
          competition: { type: "string", description: "Filter by competition" },
          limit: { type: "number", description: "Max teams to return (default 10)" },
        },
      },
    },
    {
      name: "search_players",
      description:
        "Search FIFA player database by name, nationality, club, position, or rating.",
      inputSchema: {
        type: "object",
        properties: {
          name: { type: "string", description: "Player name (partial match)" },
          nationality: { type: "string", description: "Player nationality (e.g. 'Brazil')" },
          club: { type: "string", description: "Club name (partial match)" },
          position: { type: "string", description: "Position (e.g. 'ST', 'GK', 'CB')" },
          minOverall: { type: "number", description: "Minimum overall rating" },
          maxAge: { type: "number", description: "Maximum age" },
          limit: { type: "number", description: "Max results (default 20)" },
        },
      },
    },
    {
      name: "get_player_details",
      description: "Get full details for a specific player including all attributes.",
      inputSchema: {
        type: "object",
        properties: {
          name: { type: "string", description: "Player name" },
        },
        required: ["name"],
      },
    },
    {
      name: "get_top_players",
      description: "Get top-rated players filtered by nationality, position, or club.",
      inputSchema: {
        type: "object",
        properties: {
          nationality: { type: "string", description: "Filter by nationality" },
          position: { type: "string", description: "Filter by position" },
          club: { type: "string", description: "Filter by club" },
          limit: { type: "number", description: "Max results (default 20)" },
        },
      },
    },
    {
      name: "get_brazilian_players",
      description: "Get Brazilian players at Brazilian clubs, grouped by club with ratings.",
      inputSchema: {
        type: "object",
        properties: {
          limit: { type: "number", description: "Max results (default 50)" },
        },
      },
    },
    {
      name: "get_biggest_wins",
      description: "Find matches with the largest goal margin (biggest victories).",
      inputSchema: {
        type: "object",
        properties: {
          competition: { type: "string", description: "Filter by competition" },
          season: { type: "number", description: "Filter by season year" },
          limit: { type: "number", description: "Max results (default 10)" },
        },
      },
    },
    {
      name: "get_aggregate_stats",
      description: "Get aggregate statistics: goals per match, home win rate, etc.",
      inputSchema: {
        type: "object",
        properties: {
          competition: { type: "string", description: "Filter by competition" },
          season: { type: "number", description: "Filter by season year" },
        },
      },
    },
    {
      name: "compare_seasons",
      description: "Compare statistics between two seasons.",
      inputSchema: {
        type: "object",
        properties: {
          season1: { type: "number", description: "First season year" },
          season2: { type: "number", description: "Second season year" },
          competition: { type: "string", description: "Competition (default: Brasileirão)" },
        },
        required: ["season1", "season2"],
      },
    },
    {
      name: "get_most_goals",
      description: "Get teams that scored the most goals in a competition/season.",
      inputSchema: {
        type: "object",
        properties: {
          competition: { type: "string", description: "Filter by competition" },
          season: { type: "number", description: "Filter by season year" },
          limit: { type: "number", description: "Max teams (default 10)" },
        },
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  const params = (args ?? {}) as Record<string, unknown>;

  try {
    let result: string;

    switch (name) {
      case "search_matches":
        result = searchMatches({
          team: params.team as string | undefined,
          homeTeam: params.homeTeam as string | undefined,
          awayTeam: params.awayTeam as string | undefined,
          team2: params.team2 as string | undefined,
          competition: params.competition as string | undefined,
          season: params.season as number | undefined,
          dateFrom: params.dateFrom as string | undefined,
          dateTo: params.dateTo as string | undefined,
          limit: params.limit as number | undefined,
        });
        break;

      case "head_to_head":
        result = getHeadToHead({
          team1: params.team1 as string,
          team2: params.team2 as string,
          competition: params.competition as string | undefined,
          season: params.season as number | undefined,
        });
        break;

      case "get_team_stats":
        result = getTeamStats({
          team: params.team as string,
          competition: params.competition as string | undefined,
          season: params.season as number | undefined,
          homeOnly: params.homeOnly as boolean | undefined,
          awayOnly: params.awayOnly as boolean | undefined,
        });
        break;

      case "get_standings":
        result = getStandings({
          season: params.season as number,
          competition: params.competition as string | undefined,
        });
        break;

      case "compare_teams":
        result = compareTeams({
          team1: params.team1 as string,
          team2: params.team2 as string,
          season: params.season as number | undefined,
        });
        break;

      case "get_best_home_record":
        result = getBestHomeRecord({
          season: params.season as number | undefined,
          competition: params.competition as string | undefined,
          limit: params.limit as number | undefined,
        });
        break;

      case "search_players":
        result = searchPlayers({
          name: params.name as string | undefined,
          nationality: params.nationality as string | undefined,
          club: params.club as string | undefined,
          position: params.position as string | undefined,
          minOverall: params.minOverall as number | undefined,
          maxAge: params.maxAge as number | undefined,
          limit: params.limit as number | undefined,
        });
        break;

      case "get_player_details":
        result = getPlayerDetails({ name: params.name as string });
        break;

      case "get_top_players":
        result = getTopPlayers({
          nationality: params.nationality as string | undefined,
          position: params.position as string | undefined,
          club: params.club as string | undefined,
          limit: params.limit as number | undefined,
        });
        break;

      case "get_brazilian_players":
        result = getBrazilianPlayersAtBrazilianClubs({
          limit: params.limit as number | undefined,
        });
        break;

      case "get_biggest_wins":
        result = getBiggestWins({
          competition: params.competition as string | undefined,
          season: params.season as number | undefined,
          limit: params.limit as number | undefined,
        });
        break;

      case "get_aggregate_stats":
        result = getAggregateStats({
          competition: params.competition as string | undefined,
          season: params.season as number | undefined,
        });
        break;

      case "compare_seasons":
        result = getSeasonComparison({
          season1: params.season1 as number,
          season2: params.season2 as number,
          competition: params.competition as string | undefined,
        });
        break;

      case "get_most_goals":
        result = getMostGoals({
          competition: params.competition as string | undefined,
          season: params.season as number | undefined,
          limit: params.limit as number | undefined,
        });
        break;

      default:
        result = `Unknown tool: ${name}`;
    }

    return {
      content: [{ type: "text", text: result }],
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      content: [{ type: "text", text: `Error: ${message}` }],
      isError: true,
    };
  }
});

async function main() {
  // Pre-load data on startup
  getDataStore();

  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch(console.error);
