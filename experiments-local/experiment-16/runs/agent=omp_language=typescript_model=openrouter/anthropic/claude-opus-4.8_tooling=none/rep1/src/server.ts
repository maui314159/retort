/**
 * Context
 * -------
 * Builds the MCP server and registers the Brazilian-soccer tools. The server is
 * a thin adapter: each tool validates its input with zod, calls a pure function
 * from queries.ts, and returns both a formatted text block (for LLM clients)
 * and the structured result (for programmatic clients). Keeping the logic in
 * queries.ts means the BDD tests exercise the same code paths the tools expose.
 *
 * Tools
 * -----
 * - search_matches        : matches by team/opponent/competition/season/dates
 * - head_to_head          : two-team H2H record + meetings
 * - team_stats            : a team's W/D/L + goals (overall/home/away)
 * - standings             : computed league table for competition+season
 * - search_players        : FIFA players by name/nationality/club/position
 * - competition_stats     : goals-per-match / home-win-rate aggregates
 * - biggest_wins          : largest-margin results in a filtered set
 * - list_competitions     : competitions available in the loaded data
 *
 * Exports
 * -------
 * - buildServer(store): construct and return a configured McpServer.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import {
  biggestWins,
  findMatches,
  findPlayers,
  goalsSummary,
  headToHead,
  standings,
  teamStats,
  type MatchFilter,
} from "./queries.js";
import {
  formatGoalsSummary,
  formatHeadToHead,
  formatMatches,
  formatPlayers,
  formatStandings,
  formatTeamStats,
} from "./format.js";
import type { DataStore } from "./store.js";
import type { Competition } from "./types.js";

const COMPETITIONS = [
  "Brasileirão",
  "Copa do Brasil",
  "Libertadores",
  "Serie B",
  "Serie C",
] as const;

const competitionSchema = z.enum(COMPETITIONS);

/** Wrap a formatted text + structured payload into an MCP tool result. */
function result(text: string, structured: unknown) {
  return {
    content: [{ type: "text" as const, text }],
    structuredContent: { data: structured } as Record<string, unknown>,
  };
}

/** Build a configured MCP server bound to the given data store. */
export function buildServer(store: DataStore): McpServer {
  const server = new McpServer(
    { name: "brazilian-soccer-mcp", version: "1.0.0" },
    {
      capabilities: { tools: {} },
      instructions:
        "Query Brazilian soccer match and player data: matches, head-to-head, " +
        "team stats, league standings, players, and aggregate statistics.",
    },
  );

  server.registerTool(
    "search_matches",
    {
      title: "Search matches",
      description:
        "Find matches by team, opponent, competition, season, and/or date range. " +
        "Returns matches most-recent first.",
      inputSchema: {
        team: z.string().optional().describe("Team name (any naming variation)"),
        opponent: z.string().optional().describe("Second team for fixtures/derbies"),
        side: z.enum(["home", "away", "either"]).optional(),
        competition: competitionSchema.optional(),
        season: z.number().int().optional(),
        from: z.string().optional().describe("Inclusive start date YYYY-MM-DD"),
        to: z.string().optional().describe("Inclusive end date YYYY-MM-DD"),
        limit: z.number().int().positive().max(200).optional(),
      },
    },
    async (args) => {
      const filter: MatchFilter = {
        team: args.team,
        opponent: args.opponent,
        side: args.side,
        competition: args.competition as Competition | undefined,
        season: args.season,
        from: args.from,
        to: args.to,
      };
      const matches = findMatches(store, filter);
      const limit = args.limit ?? 20;
      return result(formatMatches(matches, limit), {
        count: matches.length,
        matches: matches.slice(0, limit),
      });
    },
  );

  server.registerTool(
    "head_to_head",
    {
      title: "Head-to-head record",
      description: "Compute the head-to-head record between two teams.",
      inputSchema: {
        teamA: z.string(),
        teamB: z.string(),
        competition: competitionSchema.optional(),
        season: z.number().int().optional(),
        limit: z.number().int().positive().max(100).optional(),
      },
    },
    async (args) => {
      const h = headToHead(store, args.teamA, args.teamB, {
        competition: args.competition as Competition | undefined,
        season: args.season,
      });
      return result(formatHeadToHead(h, args.limit ?? 10), {
        teamA: h.teamA,
        teamB: h.teamB,
        aWins: h.aWins,
        bWins: h.bWins,
        draws: h.draws,
        aGoals: h.aGoals,
        bGoals: h.bGoals,
        count: h.matches.length,
        matches: h.matches.slice(0, args.limit ?? 10),
      });
    },
  );

  server.registerTool(
    "team_stats",
    {
      title: "Team statistics",
      description:
        "Aggregate a team's wins/draws/losses and goals, with home/away split, " +
        "optionally scoped to a competition and/or season.",
      inputSchema: {
        team: z.string(),
        competition: competitionSchema.optional(),
        season: z.number().int().optional(),
      },
    },
    async (args) => {
      const stats = teamStats(store, args.team, {
        competition: args.competition as Competition | undefined,
        season: args.season,
      });
      const scopeParts = [
        args.season != null ? String(args.season) : null,
        args.competition ?? null,
      ].filter(Boolean);
      const scope = scopeParts.length ? scopeParts.join(" ") : "all data";
      return result(formatTeamStats(stats, scope), stats);
    },
  );

  server.registerTool(
    "standings",
    {
      title: "League standings",
      description:
        "Compute a league table (3-1-0 points) for a competition and season " +
        "from match results.",
      inputSchema: {
        competition: competitionSchema,
        season: z.number().int(),
        limit: z.number().int().positive().max(40).optional(),
      },
    },
    async (args) => {
      const table = standings(store, args.competition as Competition, args.season);
      const title = `${args.season} ${args.competition} standings (calculated from matches):`;
      return result(formatStandings(table, title, args.limit ?? 30), {
        competition: args.competition,
        season: args.season,
        table,
      });
    },
  );

  server.registerTool(
    "search_players",
    {
      title: "Search players",
      description:
        "Search the FIFA player database by name, nationality (e.g. Brazil), " +
        "club, and/or position. Results sorted by Overall rating.",
      inputSchema: {
        name: z.string().optional(),
        nationality: z.string().optional(),
        club: z.string().optional(),
        position: z.string().optional(),
        minOverall: z.number().int().optional(),
        limit: z.number().int().positive().max(200).optional(),
      },
    },
    async (args) => {
      const players = findPlayers(store, {
        name: args.name,
        nationality: args.nationality,
        club: args.club,
        position: args.position,
        minOverall: args.minOverall,
      });
      const limit = args.limit ?? 25;
      return result(formatPlayers(players, limit), {
        count: players.length,
        players: players.slice(0, limit),
      });
    },
  );

  server.registerTool(
    "competition_stats",
    {
      title: "Competition statistics",
      description:
        "Aggregate goals-per-match, total goals, and home/away/draw rates over " +
        "a filtered set of matches (by competition, season, and/or team).",
      inputSchema: {
        competition: competitionSchema.optional(),
        season: z.number().int().optional(),
        team: z.string().optional(),
      },
    },
    async (args) => {
      const summary = goalsSummary(store, {
        competition: args.competition as Competition | undefined,
        season: args.season,
        team: args.team,
      });
      const scopeParts = [
        args.team ?? null,
        args.season != null ? String(args.season) : null,
        args.competition ?? null,
      ].filter(Boolean);
      const scope = scopeParts.length ? scopeParts.join(" ") : "all data";
      return result(formatGoalsSummary(summary, scope), summary);
    },
  );

  server.registerTool(
    "biggest_wins",
    {
      title: "Biggest wins",
      description: "Largest goal-margin results in a filtered set of matches.",
      inputSchema: {
        competition: competitionSchema.optional(),
        season: z.number().int().optional(),
        team: z.string().optional(),
        limit: z.number().int().positive().max(50).optional(),
      },
    },
    async (args) => {
      const matches = biggestWins(
        store,
        {
          competition: args.competition as Competition | undefined,
          season: args.season,
          team: args.team,
        },
        args.limit ?? 10,
      );
      return result(formatMatches(matches, matches.length), {
        count: matches.length,
        matches,
      });
    },
  );

  server.registerTool(
    "list_competitions",
    {
      title: "List competitions",
      description: "List the competitions available in the loaded data.",
      inputSchema: {},
    },
    async () => {
      const comps = store.competitions();
      return result(
        `Competitions in dataset:\n${comps.map((c) => `- ${c}`).join("\n")}`,
        { competitions: comps },
      );
    },
  );

  return server;
}
