/**
 * MCP server wiring.
 *
 * Exposes tools for match, team, player, competition, and statistical queries
 * over the loaded Brazilian soccer datasets.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import type { SoccerStore } from "./store.js";
import {
  formatAverageGoals,
  formatBiggestWins,
  formatHeadToHead,
  formatMatchList,
  formatPlayerList,
  formatStandings,
  formatTeamRecord,
} from "./formatters.js";

export function createSoccerServer(store: SoccerStore): McpServer {
  const server = new McpServer({
    name: "brazilian-soccer-mcp",
    version: "1.0.0",
  });

  server.registerTool(
    "search_matches",
    {
      description:
        "Find soccer matches by team, opponent, competition, season, date range, or round.",
      inputSchema: z.object({
        team: z.string().optional().describe("Team name to search for (home or away)"),
        opponent: z.string().optional().describe("Opponent team name"),
        competition: z.string().optional().describe("Competition name, e.g. Brasileirão"),
        season: z.number().int().optional().describe("Season year"),
        from: z.string().optional().describe("Start date (YYYY-MM-DD)"),
        to: z.string().optional().describe("End date (YYYY-MM-DD)"),
        round: z.string().optional().describe("Round or stage label"),
        limit: z.number().int().optional().describe("Maximum results to return"),
      }),
    },
    async (args) => {
      const matches = store.searchMatches({
        team: args.team,
        opponent: args.opponent,
        competition: args.competition,
        season: args.season,
        from: args.from,
        to: args.to,
        round: args.round,
        limit: args.limit,
      });
      const title = args.opponent
        ? `${args.team ?? "Team"} vs ${args.opponent}`
        : args.team
        ? `Matches for ${args.team}`
        : "Matches";
      return { content: [{ type: "text", text: formatMatchList(matches, title) }] };
    }
  );

  server.registerTool(
    "team_statistics",
    {
      description: "Compute win/loss/draw and goal statistics for a team.",
      inputSchema: z.object({
        team: z.string().describe("Team name"),
        season: z.number().int().optional().describe("Season year"),
        competition: z.string().optional().describe("Competition filter"),
        venue: z.enum(["home", "away", "all"]).optional().describe("Home, away, or all matches"),
      }),
    },
    async (args) => {
      const record = store.teamStatistics(args.team, {
        season: args.season,
        competition: args.competition,
        venue: args.venue,
      });
      const label = `${record.team} ${args.venue ?? "all"} record${
        args.season ? ` (${args.season}${args.competition ? " " + args.competition : ""})` : ""
      }:`;
      return { content: [{ type: "text", text: formatTeamRecord(record, label) }] };
    }
  );

  server.registerTool(
    "head_to_head",
    {
      description: "Compare two teams head-to-head across all loaded datasets.",
      inputSchema: z.object({
        teamA: z.string().describe("First team"),
        teamB: z.string().describe("Second team"),
        season: z.number().int().optional().describe("Season year"),
        competition: z.string().optional().describe("Competition filter"),
      }),
    },
    async (args) => {
      const h2h = store.headToHead(args.teamA, args.teamB, {
        season: args.season,
        competition: args.competition,
      });
      return { content: [{ type: "text", text: formatHeadToHead(h2h) }] };
    }
  );

  server.registerTool(
    "competition_standings",
    {
      description: "Calculate league standings for a competition and season.",
      inputSchema: z.object({
        competition: z.string().describe("Competition name"),
        season: z.number().int().describe("Season year"),
      }),
    },
    async (args) => {
      const standings = store.competitionStandings(args.competition, args.season);
      return {
        content: [
          {
            type: "text",
            text: formatStandings(standings, `${args.season} ${args.competition} Final Standings`),
          },
        ],
      };
    }
  );

  server.registerTool(
    "biggest_wins",
    {
      description: "Find the biggest victories by goal difference.",
      inputSchema: z.object({
        competition: z.string().optional().describe("Competition filter"),
        season: z.number().int().optional().describe("Season year"),
        limit: z.number().int().optional().describe("Maximum results"),
      }),
    },
    async (args) => {
      const matches = store.biggestWins({
        competition: args.competition,
        season: args.season,
        limit: args.limit,
      });
      return {
        content: [
          {
            type: "text",
            text: formatBiggestWins(matches, `Biggest victories${args.competition ? " in " + args.competition : ""}`),
          },
        ],
      };
    }
  );

  server.registerTool(
    "search_players",
    {
      description: "Search FIFA player data by name, nationality, club, or position.",
      inputSchema: z.object({
        name: z.string().optional().describe("Player name substring"),
        nationality: z.string().optional().describe("Nationality, e.g. Brazil"),
        club: z.string().optional().describe("Club name"),
        position: z.string().optional().describe("Position code, e.g. LW, GK, ST"),
        minOverall: z.number().int().optional().describe("Minimum overall rating"),
        limit: z.number().int().optional().describe("Maximum results"),
      }),
    },
    async (args) => {
      const players = store.searchPlayers({
        name: args.name,
        nationality: args.nationality,
        club: args.club,
        position: args.position,
        minOverall: args.minOverall,
        limit: args.limit,
      });
      return { content: [{ type: "text", text: formatPlayerList(players, "Players") }] };
    }
  );

  server.registerTool(
    "average_goals",
    {
      description: "Compute the average goals per match for a competition or season.",
      inputSchema: z.object({
        competition: z.string().optional().describe("Competition filter"),
        season: z.number().int().optional().describe("Season year"),
      }),
    },
    async (args) => {
      const avg = store.averageGoalsPerMatch({
        competition: args.competition,
        season: args.season,
      });
      return {
        content: [
          {
            type: "text",
            text: formatAverageGoals(
              avg,
              `Average goals per match${args.competition ? " in " + args.competition : ""}${
                args.season ? " " + args.season : ""
              }`
            ),
          },
        ],
      };
    }
  );

  return server;
}
