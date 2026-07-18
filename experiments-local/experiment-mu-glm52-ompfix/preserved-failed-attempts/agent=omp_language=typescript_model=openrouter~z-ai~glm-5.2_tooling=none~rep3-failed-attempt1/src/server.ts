/**
 * brazilian-soccer-mcp — MCP server wiring.
 *
 * Context: This module instantiates an `McpServer` from the official TypeScript
 * SDK and registers one tool per query category from the TASK.md spec
 * (matches, teams, head-to-head, players, competitions, statistics). Each tool
 * delegates to the pure query engine in `query.ts` and returns its result as
 * `content: [{ type: "text", text: <JSON> }]`, which is the canonical shape MCP
 * clients consume.
 *
 * The dataset is loaded once when the server is constructed and shared across
 * every tool call.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { loadDatasets, type Store } from "./loader.js";
import * as Q from "./query.js";

/** Build the MCP server with all soccer tools registered. */
export function buildServer(store: Store): McpServer {
  const server = new McpServer({
    name: "brazilian-soccer-mcp",
    version: "1.0.0",
  });

  // ----- search_matches -----
  server.registerTool(
    "search_matches",
    {
      description:
        "Search Brazilian soccer matches by team, opponent, competition, season, or date range. Returns normalized match summaries (date, teams, score, competition).",
      inputSchema: {
        team: z
          .string()
          .optional()
          .describe("Team name (home, away, or either)"),
        opponent: z
          .string()
          .optional()
          .describe("Opponent team name (use with team for head-to-head)"),
        competition: z
          .string()
          .optional()
          .describe("Competition, e.g. 'Brasileirão Serie A', 'Copa do Brasil', 'Libertadores'"),
        season: z
          .number()
          .int()
          .optional()
          .describe("Season year, e.g. 2023"),
        from: z
          .string()
          .optional()
          .describe("Start date (ISO YYYY-MM-DD)"),
        to: z
          .string()
          .optional()
          .describe("End date (ISO YYYY-MM-DD)"),
        limit: z
          .number()
          .int()
          .optional()
          .describe("Max results (default 50)"),
      },
    },
    async (args) => ({
      content: [
        {
          type: "text",
          text: JSON.stringify(
            Q.queryMatches(store, args as Q.MatchQueryOptions),
            null,
            2,
          ),
        },
      ],
    }),
  );

  // ----- last_match_between -----
  server.registerTool(
    "last_match_between",
    {
      description:
        "Return the most recent match between two teams, including the score.",
      inputSchema: {
        team_a: z.string().describe("First team name"),
        team_b: z.string().describe("Second team name"),
      },
    },
    async ({ team_a, team_b }) => ({
      content: [
        {
          type: "text",
          text: JSON.stringify(
            Q.lastMatchBetween(store, team_a, team_b),
            null,
            2,
          ),
        },
      ],
    }),
  );

  // ----- team_stats -----
  server.registerTool(
    "team_stats",
    {
      description:
        "Calculate win/loss/draw record and goals for a team, optionally filtered by season, competition, and venue.",
      inputSchema: {
        team: z.string().describe("Team name"),
        season: z.number().int().optional().describe("Season year"),
        competition: z
          .string()
          .optional()
          .describe("Competition filter"),
        venue: z
          .enum(["home", "away", "all"])
          .optional()
          .describe("Venue filter"),
      },
    },
    async ({ team, season, competition, venue }) => ({
      content: [
        {
          type: "text",
          text: JSON.stringify(
            Q.teamRecord(store, team, { season, competition, venue }),
            null,
            2,
          ),
        },
      ],
    }),
  );

  // ----- compare_teams -----
  server.registerTool(
    "compare_teams",
    {
      description:
        "Compare two teams head-to-head: wins, draws, goals each across all matches in the dataset.",
      inputSchema: {
        team_a: z.string().describe("First team name"),
        team_b: z.string().describe("Second team name"),
      },
    },
    async ({ team_a, team_b }) => ({
      content: [
        {
          type: "text",
          text: JSON.stringify(
            Q.headToHead(store, team_a, team_b),
            null,
            2,
          ),
        },
      ],
    }),
  );

  // ----- search_players -----
  server.registerTool(
    "search_players",
    {
      description:
        "Search the FIFA player database by name, nationality, club, position, or minimum overall rating. Sorted by rating by default.",
      inputSchema: {
        name: z.string().optional().describe("Substring of player name"),
        nationality: z
          .string()
          .optional()
          .describe('Country, e.g. "Brazil"'),
        club: z.string().optional().describe("Club name"),
        position: z
          .string()
          .optional()
          .describe('Position code, e.g. "ST", "GK", "CDM"'),
        min_overall: z
          .number()
          .int()
          .optional()
          .describe("Minimum overall rating"),
        limit: z.number().int().optional().describe("Max results (default 20)"),
        sort: z
          .enum(["overall", "potential", "name"])
          .optional()
          .describe("Sort key (default overall)"),
      },
    },
    async (args) => {
      const opts: Q.PlayerQueryOptions = {
        name: args.name,
        nationality: args.nationality,
        club: args.club,
        position: args.position,
        minOverall: args.min_overall,
        limit: args.limit,
        sort: args.sort,
      };
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(Q.queryPlayers(store, opts), null, 2),
          },
        ],
      };
    },
  );

  // ----- top_players_at_club -----
  server.registerTool(
    "top_players_at_club",
    {
      description: "Return the highest-rated players at a given club.",
      inputSchema: {
        club: z.string().describe("Club name"),
        limit: z
          .number()
          .int()
          .optional()
          .describe("Max results (default 10)"),
      },
    },
    async ({ club, limit }) => ({
      content: [
        {
          type: "text",
          text: JSON.stringify(
            Q.topPlayersAtClub(store, club, limit ?? 10),
            null,
            2,
          ),
        },
      ],
    }),
  );

  // ----- brazilian_players_by_club -----
  server.registerTool(
    "brazilian_players_by_club",
    {
      description:
        "Summarize Brazilian players per club: count and average FIFA rating, sorted by count.",
      inputSchema: {
        limit: z
          .number()
          .int()
          .optional()
          .describe("Max clubs (default 20)"),
      },
    },
    async ({ limit }) => ({
      content: [
        {
          type: "text",
          text: JSON.stringify(
            Q.brazilianPlayersByClub(store, limit ?? 20),
            null,
            2,
          ),
        },
      ],
    }),
  );

  // ----- standings -----
  server.registerTool(
    "standings",
    {
      description:
        "Calculate standings for a competition+season from match results, with champion flagged. Default competition is Brasileirão Serie A.",
      inputSchema: {
        season: z.number().int().describe("Season year"),
        competition: z
          .string()
          .optional()
          .describe("Competition (default Brasileirão Serie A)"),
        top: z
          .number()
          .int()
          .optional()
          .describe("Limit to top N teams"),
      },
    },
    async ({ season, competition, top }) => ({
      content: [
        {
          type: "text",
          text: JSON.stringify(
            Q.standings(store, { season, competition, top }),
            null,
            2,
          ),
        },
      ],
    }),
  );

  // ----- champion -----
  server.registerTool(
    "champion",
    {
      description:
        "Return the champion (top of standings) for a competition+season.",
      inputSchema: {
        season: z.number().int().describe("Season year"),
        competition: z
          .string()
          .optional()
          .describe("Competition (default Brasileirão Serie A)"),
      },
    },
    async ({ season, competition }) => ({
      content: [
        {
          type: "text",
          text: JSON.stringify(
            Q.champion(store, { season, competition }),
            null,
            2,
          ),
        },
      ],
    }),
  );

  // ----- relegated -----
  server.registerTool(
    "relegated",
    {
      description:
        "Return the bottom N teams of a competition+season (relegation zone).",
      inputSchema: {
        season: z.number().int().describe("Season year"),
        competition: z
          .string()
          .optional()
          .describe("Competition (default Brasileirão Serie A)"),
        count: z
          .number()
          .int()
          .optional()
          .describe("Number of bottom teams (default 4)"),
      },
    },
    async ({ season, competition, count }) => ({
      content: [
        {
          type: "text",
          text: JSON.stringify(
            Q.relegated(store, { season, competition, count }),
            null,
            2,
          ),
        },
      ],
    }),
  );

  // ----- goals_average -----
  server.registerTool(
    "goals_average",
    {
      description:
        "Compute goals-per-match average and home/away/draw win rates for a competition (optionally a season).",
      inputSchema: {
        competition: z.string().optional().describe("Competition filter"),
        season: z.number().int().optional().describe("Season filter"),
      },
    },
    async ({ competition, season }) => ({
      content: [
        {
          type: "text",
          text: JSON.stringify(
            Q.goalsAverage(store, { competition, season }),
            null,
            2,
          ),
        },
      ],
    }),
  );

  // ----- biggest_wins -----
  server.registerTool(
    "biggest_wins",
    {
      description: "Return the biggest victory margins in the dataset.",
      inputSchema: {
        competition: z.string().optional().describe("Competition filter"),
        limit: z
          .number()
          .int()
          .optional()
          .describe("Max results (default 10)"),
      },
    },
    async ({ competition, limit }) => ({
      content: [
        {
          type: "text",
          text: JSON.stringify(
            Q.biggestWins(store, { competition, limit }),
            null,
            2,
          ),
        },
      ],
    }),
  );

  // ----- best_away_record -----
  server.registerTool(
    "best_away_record",
    {
      description:
        "Return the teams with the best away record for a competition+season.",
      inputSchema: {
        competition: z.string().optional().describe("Competition filter"),
        season: z.number().int().optional().describe("Season filter"),
        limit: z
          .number()
          .int()
          .optional()
          .describe("Max results (default 5)"),
      },
    },
    async ({ competition, season, limit }) => ({
      content: [
        {
          type: "text",
          text: JSON.stringify(
            Q.bestAwayRecord(store, { competition, season, limit }),
            null,
            2,
          ),
        },
      ],
    }),
  );

  // ----- list_teams -----
  server.registerTool(
    "list_teams",
    {
      description: "List all known team display names in the dataset.",
      inputSchema: {},
    },
    async () => ({
      content: [
        {
          type: "text",
          text: JSON.stringify(Q.allTeams(store), null, 2),
        },
      ],
    }),
  );

  // ----- list_competitions -----
  server.registerTool(
    "list_competitions",
    {
      description: "List all competitions present in the dataset.",
      inputSchema: {},
    },
    async () => ({
      content: [
        {
          type: "text",
          text: JSON.stringify(Q.allCompetitions(store), null, 2),
        },
      ],
    }),
  );

  // ----- list_seasons -----
  server.registerTool(
    "list_seasons",
    {
      description: "List all seasons present, optionally for one competition.",
      inputSchema: {
        competition: z.string().optional().describe("Competition filter"),
      },
    },
    async ({ competition }) => ({
      content: [
        {
          type: "text",
          text: JSON.stringify(Q.seasonsFor(store, competition), null, 2),
        },
      ],
    }),
  );

  return server;
}

/** Load datasets from `dataDir` and start an MCP stdio server. */
export async function runServer(dataDir: string): Promise<void> {
  const store = loadDatasets(dataDir);
  const server = buildServer(store);
  const transport = new StdioServerTransport();
  await server.connect(transport);
}
