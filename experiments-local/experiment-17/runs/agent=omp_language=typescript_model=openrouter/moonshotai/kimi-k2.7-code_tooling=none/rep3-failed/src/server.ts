/**
 * Brazilian Soccer MCP server.
 *
 * Exposes the query engine through MCP tools. All tools return JSON text
 * content so LLM clients can consume the results directly.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { SoccerRepository } from "./loaders.js";
import { QueryEngine, type MatchFilters } from "./queries.js";

export interface ServerOptions {
  repository?: SoccerRepository;
}

const tools = [
  {
    name: "search_matches",
    description: "Search matches by team, competition, season, date range, round, or stage.",
    inputSchema: {
      type: "object" as const,
      properties: {
        team: { type: "string", description: "Team name (home or away)" },
        opponent: { type: "string", description: "Opponent name" },
        home: { type: "string", description: "Filter by home team" },
        away: { type: "string", description: "Filter by away team" },
        competition: { type: "string", description: "Competition name, e.g. Brasileirão" },
        season: { type: "number", description: "Season year" },
        startDate: { type: "string", description: "Start ISO date (YYYY-MM-DD)" },
        endDate: { type: "string", description: "End ISO date (YYYY-MM-DD)" },
        round: { type: ["string", "number"], description: "Match round" },
        stage: { type: "string", description: "Tournament stage" },
        limit: { type: "number", description: "Maximum number of results" },
      },
    },
  },
  {
    name: "get_team_stats",
    description: "Calculate win/draw/loss and goal statistics for a team.",
    inputSchema: {
      type: "object" as const,
      properties: {
        team: { type: "string", description: "Team name" },
        season: { type: "number", description: "Optional season year" },
        competition: { type: "string", description: "Optional competition filter" },
        venue: {
          type: "string",
          enum: ["home", "away", "both"],
          description: "Home, away, or both venues",
        },
      },
      required: ["team"],
    },
  },
  {
    name: "search_players",
    description: "Search the FIFA player dataset by name, nationality, club, or position.",
    inputSchema: {
      type: "object" as const,
      properties: {
        name: { type: "string" },
        nationality: { type: "string" },
        club: { type: "string" },
        position: { type: "string" },
        minOverall: { type: "number" },
        limit: { type: "number" },
      },
    },
  },
  {
    name: "get_standings",
    description: "Compute league standings for a season using 3-points-per-win.",
    inputSchema: {
      type: "object" as const,
      properties: {
        season: { type: "number", description: "Season year" },
        competition: { type: "string", description: "Optional competition filter" },
      },
      required: ["season"],
    },
  },
  {
    name: "get_head_to_head",
    description: "Return the head-to-head record and matches for two teams.",
    inputSchema: {
      type: "object" as const,
      properties: {
        teamA: { type: "string" },
        teamB: { type: "string" },
      },
      required: ["teamA", "teamB"],
    },
  },
  {
    name: "get_biggest_wins",
    description: "Return matches with the biggest goal margins.",
    inputSchema: {
      type: "object" as const,
      properties: {
        limit: { type: "number" },
        competition: { type: "string" },
      },
    },
  },
  {
    name: "get_average_goals",
    description: "Calculate average goals per match, optionally for one competition.",
    inputSchema: {
      type: "object" as const,
      properties: {
        competition: { type: "string" },
      },
    },
  },
  {
    name: "get_home_away_summary",
    description: "Return home win, away win, and draw rates.",
    inputSchema: {
      type: "object" as const,
      properties: {
        competition: { type: "string" },
      },
    },
  },
  {
    name: "list_competitions",
    description: "List all competitions in the dataset.",
    inputSchema: {
      type: "object" as const,
      properties: {},
    },
  },
  {
    name: "list_teams",
    description: "List all canonical team names in the dataset.",
    inputSchema: {
      type: "object" as const,
      properties: {},
    },
  },
];

export function createServer(options: ServerOptions = {}) {
  const repo = options.repository ?? SoccerRepository.load();
  const engine = new QueryEngine(repo);

  const server = new Server(
    { name: "brazilian-soccer-mcp", version: "1.0.0" },
    { capabilities: { tools: {} } },
  );

  server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools }));

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args = {} } = request.params;

    try {
      let result: unknown;

      switch (name) {
        case "search_matches": {
          const filters: MatchFilters = {};
          if (args.team) filters.team = String(args.team);
          if (args.opponent) filters.opponent = String(args.opponent);
          if (args.home) filters.home = String(args.home);
          if (args.away) filters.away = String(args.away);
          if (args.competition) filters.competition = String(args.competition);
          if (args.season) filters.season = Number(args.season);
          if (args.startDate) filters.startDate = String(args.startDate);
          if (args.endDate) filters.endDate = String(args.endDate);
          if (args.round !== undefined) filters.round = args.round as string | number;
          if (args.stage) filters.stage = String(args.stage);
          if (args.limit) filters.limit = Number(args.limit);
          result = engine.findMatches(filters);
          break;
        }
        case "get_team_stats":
          result = engine.teamStats({
            team: String(args.team),
            season: args.season !== undefined ? Number(args.season) : undefined,
            competition: args.competition !== undefined ? String(args.competition) : undefined,
            venue: args.venue === "home" || args.venue === "away" || args.venue === "both" ? args.venue : "both",
          });
          break;
        case "search_players":
          result = engine.searchPlayers({
            name: args.name !== undefined ? String(args.name) : undefined,
            nationality: args.nationality !== undefined ? String(args.nationality) : undefined,
            club: args.club !== undefined ? String(args.club) : undefined,
            position: args.position !== undefined ? String(args.position) : undefined,
            minOverall: args.minOverall !== undefined ? Number(args.minOverall) : undefined,
            limit: args.limit !== undefined ? Number(args.limit) : undefined,
          });
          break;
        case "get_standings":
          result = engine.standings({
            season: Number(args.season),
            competition: args.competition !== undefined ? String(args.competition) : undefined,
          });
          break;
        case "get_head_to_head":
          result = engine.headToHead(String(args.teamA), String(args.teamB));
          break;
        case "get_biggest_wins":
          result = engine.biggestWins(
            args.limit !== undefined ? Number(args.limit) : 10,
            args.competition !== undefined ? String(args.competition) : undefined,
          );
          break;
        case "get_average_goals":
          result = engine.averageGoals(
            args.competition !== undefined ? String(args.competition) : undefined,
          );
          break;
        case "get_home_away_summary":
          result = engine.homeAwaySummary(
            args.competition !== undefined ? String(args.competition) : undefined,
          );
          break;
        case "list_competitions":
          result = repo.allCompetitions();
          break;
        case "list_teams":
          result = repo.allTeams();
          break;
        default:
          throw new Error(`Unknown tool: ${name}`);
      }

      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return {
        content: [{ type: "text", text: JSON.stringify({ error: message }) }],
        isError: true,
      };
    }
  });

  return { server, engine };
}

export async function runServer(options: ServerOptions = {}) {
  const { server } = createServer(options);
  const transport = new StdioServerTransport();
  await server.connect(transport);
}
