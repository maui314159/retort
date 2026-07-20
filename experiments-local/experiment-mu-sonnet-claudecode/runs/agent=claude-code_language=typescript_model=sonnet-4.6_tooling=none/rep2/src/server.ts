import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import {
  searchMatches,
  getTeamStats,
  headToHead,
  searchPlayers,
  getStandings,
  getTopStats,
} from "./tools.js";

export function createServer(): McpServer {
  const server = new McpServer({
    name: "brazilian-soccer-mcp",
    version: "1.0.0",
  });

  server.tool(
    "search_matches",
    "Search for soccer matches by team, competition, season, or date range. Returns match results with scores.",
    {
      team: z.string().optional().describe("Team name to search for (home or away)"),
      team2: z.string().optional().describe("Second team name for head-to-head filtering"),
      competition: z
        .string()
        .optional()
        .describe("Competition name: Brasileirao, Copa do Brasil, Libertadores"),
      season: z.number().int().optional().describe("Season year (e.g. 2023)"),
      date_from: z.string().optional().describe("Start date filter (ISO format: YYYY-MM-DD)"),
      date_to: z.string().optional().describe("End date filter (ISO format: YYYY-MM-DD)"),
      limit: z
        .number()
        .int()
        .optional()
        .describe("Max results to return (default 20)"),
    },
    (args) => {
      const result = searchMatches(args);
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(result, null, 2),
          },
        ],
      };
    }
  );

  server.tool(
    "get_team_stats",
    "Get win/loss/draw statistics, goals, and points for a team, optionally filtered by competition and season.",
    {
      team: z.string().describe("Team name"),
      competition: z.string().optional().describe("Competition name (optional filter)"),
      season: z.number().int().optional().describe("Season year (optional filter)"),
    },
    (args) => {
      const result = getTeamStats(args);
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(result, null, 2),
          },
        ],
      };
    }
  );

  server.tool(
    "head_to_head",
    "Get head-to-head record and recent match history between two teams.",
    {
      team1: z.string().describe("First team name"),
      team2: z.string().describe("Second team name"),
      competition: z.string().optional().describe("Competition name (optional filter)"),
      season: z.number().int().optional().describe("Season year (optional filter)"),
      limit: z
        .number()
        .int()
        .optional()
        .describe("Number of recent matches to include (default 10)"),
    },
    (args) => {
      const result = headToHead(args);
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(result, null, 2),
          },
        ],
      };
    }
  );

  server.tool(
    "search_players",
    "Search for FIFA player data by name, nationality, club, or position.",
    {
      name: z.string().optional().describe("Player name (partial match)"),
      nationality: z.string().optional().describe("Player nationality (e.g. Brazilian)"),
      club: z.string().optional().describe("Club name (e.g. Flamengo)"),
      position: z.string().optional().describe("Playing position (e.g. ST, GK, CB)"),
      min_overall: z
        .number()
        .int()
        .optional()
        .describe("Minimum FIFA overall rating"),
      limit: z.number().int().optional().describe("Max results (default 20)"),
    },
    (args) => {
      const result = searchPlayers(args);
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(result, null, 2),
          },
        ],
      };
    }
  );

  server.tool(
    "get_standings",
    "Calculate competition standings (points table) from match results for a given season.",
    {
      competition: z
        .string()
        .describe("Competition name: Brasileirao, Copa do Brasil, Libertadores"),
      season: z.number().int().describe("Season year (e.g. 2019)"),
    },
    (args) => {
      const result = getStandings(args);
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(result, null, 2),
          },
        ],
      };
    }
  );

  server.tool(
    "get_top_stats",
    "Get aggregate statistics: biggest wins, most goals, home/away records, or overall averages.",
    {
      stat: z
        .enum(["biggest_wins", "most_goals", "home_record", "away_record", "averages"])
        .describe("Type of statistic to retrieve"),
      competition: z.string().optional().describe("Competition name (optional filter)"),
      season: z.number().int().optional().describe("Season year (optional filter)"),
      limit: z.number().int().optional().describe("Max results (default 10)"),
    },
    (args) => {
      const result = getTopStats(args);
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(result, null, 2),
          },
        ],
      };
    }
  );

  return server;
}
