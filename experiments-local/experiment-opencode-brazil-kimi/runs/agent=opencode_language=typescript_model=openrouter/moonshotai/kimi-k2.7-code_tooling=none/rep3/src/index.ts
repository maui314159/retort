import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from "@modelcontextprotocol/sdk/types.js";
import { loadDataset } from "./data.js";
import { QueryEngine } from "./query.js";

const dataset = loadDataset();
const engine = new QueryEngine(dataset.matches, dataset.players);

const tools: Tool[] = [
  {
    name: "find_matches",
    description:
      "Find soccer matches by team, competition, season, date range, or round. Returns a list of matches with dates, scores, and competition.",
    inputSchema: {
      type: "object",
      properties: {
        team: { type: "string", description: "Team name (matches home or away)" },
        homeTeam: { type: "string", description: "Home team name" },
        awayTeam: { type: "string", description: "Away team name" },
        competition: { type: "string", description: "Competition such as Brasileirão, Copa do Brasil, Copa Libertadores" },
        season: { type: "number", description: "Season year" },
        startDate: { type: "string", description: "Start date ISO YYYY-MM-DD" },
        endDate: { type: "string", description: "End date ISO YYYY-MM-DD" },
        round: { type: "string", description: "Match round" },
        limit: { type: "number", description: "Maximum matches to return" },
      },
    },
  },
  {
    name: "head_to_head",
    description: "Get head-to-head record and recent matches between two teams.",
    inputSchema: {
      type: "object",
      properties: {
        teamA: { type: "string" },
        teamB: { type: "string" },
        limit: { type: "number" },
      },
      required: ["teamA", "teamB"],
    },
  },
  {
    name: "team_stats",
    description: "Get win/loss/draw record, goals, and win rate for a team, optionally filtered by season and competition.",
    inputSchema: {
      type: "object",
      properties: {
        team: { type: "string" },
        competition: { type: "string" },
        season: { type: "number" },
        homeOnly: { type: "boolean", description: "Only count home matches" },
        awayOnly: { type: "boolean", description: "Only count away matches" },
      },
      required: ["team"],
    },
  },
  {
    name: "find_players",
    description: "Search FIFA player data by name, nationality, club, position, or minimum overall rating.",
    inputSchema: {
      type: "object",
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
    name: "player_lookup",
    description: "Look up a specific player by name.",
    inputSchema: {
      type: "object",
      properties: {
        name: { type: "string" },
      },
      required: ["name"],
    },
  },
  {
    name: "standings",
    description: "Calculate league standings from match results for a competition and season.",
    inputSchema: {
      type: "object",
      properties: {
        competition: { type: "string" },
        season: { type: "number" },
      },
    },
  },
  {
    name: "top_scoring_teams",
    description: "Find teams with the most goals in a competition and season.",
    inputSchema: {
      type: "object",
      properties: {
        competition: { type: "string" },
        season: { type: "number" },
        limit: { type: "number" },
      },
    },
  },
  {
    name: "biggest_wins",
    description: "Find matches with the biggest goal differences.",
    inputSchema: {
      type: "object",
      properties: {
        competition: { type: "string" },
        limit: { type: "number" },
      },
    },
  },
  {
    name: "overall_stats",
    description: "Get aggregate stats such as average goals per match and home win rate.",
    inputSchema: {
      type: "object",
      properties: {
        competition: { type: "string" },
      },
    },
  },
  {
    name: "team_rankings",
    description: "Rank teams by performance and identify best home/away records.",
    inputSchema: {
      type: "object",
      properties: {},
    },
  },
  {
    name: "compare_teams",
    description: "Compare two teams including overall records and head-to-head.",
    inputSchema: {
      type: "object",
      properties: {
        teamA: { type: "string" },
        teamB: { type: "string" },
      },
      required: ["teamA", "teamB"],
    },
  },
];

function toResult(text: string) {
  return {
    content: [{ type: "text" as const, text }],
    isError: false,
  };
}

const server = new Server(
  { name: "brazilian-soccer-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools }));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args = {} } = request.params;
  try {
    switch (name) {
      case "find_matches": {
        const result = engine.findMatches(
          {
            team: args.team as string | undefined,
            homeTeam: args.homeTeam as string | undefined,
            awayTeam: args.awayTeam as string | undefined,
            competition: args.competition as string | undefined,
            season: args.season as number | undefined,
            startDate: args.startDate as string | undefined,
            endDate: args.endDate as string | undefined,
            round: args.round as string | undefined,
          },
          (args.limit as number) ?? 20
        );
        return toResult(result.text);
      }
      case "head_to_head": {
        const result = engine.findMatchesBetweenTeams(
          args.teamA as string,
          args.teamB as string,
          (args.limit as number) ?? 10
        );
        return toResult(result.text);
      }
      case "team_stats": {
        const base: Parameters<typeof engine.getTeamStats>[1] = {};
        if (args.competition) base.competition = args.competition as string;
        if (args.season) base.season = args.season as number;
        if (args.homeOnly) base.homeTeam = args.team as string;
        if (args.awayOnly) base.awayTeam = args.team as string;
        const result = engine.getTeamStats(args.team as string, base);
        return toResult(result.text);
      }
      case "find_players": {
        const result = engine.findPlayers({
          name: args.name as string | undefined,
          nationality: args.nationality as string | undefined,
          club: args.club as string | undefined,
          position: args.position as string | undefined,
          minOverall: args.minOverall as number | undefined,
          limit: (args.limit as number) ?? 20,
        });
        return toResult(result.text);
      }
      case "player_lookup": {
        const result = engine.getPlayerByName(args.name as string);
        return toResult(result.text);
      }
      case "standings": {
        const result = engine.getStandings(
          args.competition as string | undefined,
          args.season as number | undefined
        );
        return toResult(result.text);
      }
      case "top_scoring_teams": {
        const result = engine.getTopScoringTeams(
          args.competition as string | undefined,
          args.season as number | undefined,
          (args.limit as number) ?? 5
        );
        return toResult(result.text);
      }
      case "biggest_wins": {
        const result = engine.getBiggestWins(
          args.competition as string | undefined,
          (args.limit as number) ?? 5
        );
        return toResult(result.text);
      }
      case "overall_stats": {
        const result = engine.getOverallStats(args.competition as string | undefined);
        return toResult(result.text);
      }
      case "team_rankings": {
        const result = engine.getTeamRankings();
        return toResult(result.text);
      }
      case "compare_teams": {
        const result = engine.compareTeams(args.teamA as string, args.teamB as string);
        return toResult(result.text);
      }
      default:
        return toResult(`Unknown tool: ${name}`);
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return {
      content: [{ type: "text" as const, text: `Error: ${message}` }],
      isError: true,
    };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main();
