/**
 * Context
 * -------
 * MCP server wiring for the Brazilian Soccer knowledge base. Builds an
 * `McpServer` (modelcontextprotocol SDK) and registers the tools that let an
 * LLM answer the natural-language questions from the spec:
 *
 *   search_matches      - matches by team/opponent/competition/season/dates
 *   head_to_head        - aggregated record between two clubs
 *   team_record         - W/D/L, goals, home/away split for a team
 *   league_standings    - table calculated from match results
 *   search_players      - FIFA players by name/nationality/club/position
 *   club_squads         - players grouped by club (e.g. Brazilians per club)
 *   competition_stats   - average goals, home/away win rates
 *   biggest_wins        - largest-margin victories in the data
 *   dataset_overview    - counts + available competitions/seasons
 *
 * `createServer` is deliberately transport-agnostic so tests can drive the
 * knowledge base directly and `index.ts` can attach a stdio transport. Each
 * tool returns formatted text (format.ts) plus a `structuredContent` payload so
 * callers can consume either representation.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import {
  formatAggregateStats,
  formatClubSquads,
  formatHeadToHead,
  formatMatchList,
  formatPlayerList,
  formatStandings,
  formatTeamRecord,
} from "./format.js";
import { SoccerKnowledgeBase } from "./queries.js";
import type { Competition, SoccerData } from "./types.js";

const COMPETITIONS = [
  "Brasileirão Série A",
  "Brasileirão Série B",
  "Brasileirão Série C",
  "Copa do Brasil",
  "Copa Libertadores",
  "Other",
] as const satisfies readonly Competition[];

const competitionSchema = z.enum(COMPETITIONS);

/** Wrap formatted text and structured data into an MCP tool result. */
function textResult(text: string, structured: Record<string, unknown>) {
  return {
    content: [{ type: "text" as const, text }],
    structuredContent: structured,
  };
}

/**
 * Build a fully-wired MCP server over the given knowledge base. Exposed
 * separately from transport setup so it can be unit-tested.
 */
export function createServer(data: SoccerData): McpServer {
  const kb = new SoccerKnowledgeBase(data);

  const server = new McpServer({
    name: "brazilian-soccer-mcp",
    version: "1.0.0",
  });

  server.registerTool(
    "search_matches",
    {
      title: "Search matches",
      description:
        "Find matches by team, opponent, competition, season, or date range. " +
        "Returns matches newest-first. Use `opponent` together with `team` for " +
        "fixtures between two clubs.",
      inputSchema: {
        team: z.string().optional().describe("Team name (any spelling/suffix)"),
        opponent: z.string().optional().describe("Second team to restrict to fixtures between both"),
        side: z.enum(["home", "away", "either"]).optional(),
        competition: competitionSchema.optional(),
        season: z.number().int().optional(),
        from: z.string().optional().describe("Inclusive ISO date lower bound YYYY-MM-DD"),
        to: z.string().optional().describe("Inclusive ISO date upper bound YYYY-MM-DD"),
        limit: z.number().int().positive().max(200).optional().describe("Max rows (default 25)"),
      },
    },
    async (args) => {
      const limit = args.limit ?? 25;
      const all = kb.findMatches({ ...args });
      const shown = all.slice(0, limit);
      const header =
        args.team && args.opponent
          ? `${args.team} vs ${args.opponent}:`
          : args.team
            ? `Matches for ${args.team}:`
            : "Matches:";
      return textResult(formatMatchList(shown, header, all.length), {
        total: all.length,
        matches: shown,
      });
    }
  );

  server.registerTool(
    "head_to_head",
    {
      title: "Head-to-head record",
      description: "Aggregated all-time record between two clubs, with recent matches.",
      inputSchema: {
        team_a: z.string(),
        team_b: z.string(),
        sample: z.number().int().positive().max(50).optional().describe("Recent matches to list (default 10)"),
      },
    },
    async (args) => {
      const h = kb.headToHead(args.team_a, args.team_b);
      return textResult(formatHeadToHead(h, args.sample ?? 10), { headToHead: h });
    }
  );

  server.registerTool(
    "team_record",
    {
      title: "Team record",
      description:
        "Win/draw/loss record, goals for/against and win rate for a team, " +
        "optionally filtered by season, competition, and home/away side.",
      inputSchema: {
        team: z.string(),
        season: z.number().int().optional(),
        competition: competitionSchema.optional(),
        side: z.enum(["home", "away", "either"]).optional(),
      },
    },
    async (args) => {
      const rec = kb.teamRecord(args.team, {
        season: args.season,
        competition: args.competition,
        side: args.side,
      });
      const scope = [
        args.season !== undefined ? String(args.season) : undefined,
        args.competition,
        args.side && args.side !== "either" ? `${args.side} only` : undefined,
      ]
        .filter(Boolean)
        .join(" ");
      const label = `${rec.team} record${scope ? ` (${scope})` : ""}:`;
      return textResult(formatTeamRecord(rec, label), { record: rec });
    }
  );

  server.registerTool(
    "league_standings",
    {
      title: "League standings",
      description:
        "Final standings for a competition and season, calculated from match " +
        "results (3 points per win, 1 per draw).",
      inputSchema: {
        competition: competitionSchema,
        season: z.number().int(),
        limit: z.number().int().positive().max(100).optional(),
      },
    },
    async (args) => {
      const rows = kb.standings(args.competition, args.season);
      const header = `${args.season} ${args.competition} standings (calculated from matches):`;
      return textResult(formatStandings(rows, header, args.limit), {
        standings: args.limit ? rows.slice(0, args.limit) : rows,
      });
    }
  );

  server.registerTool(
    "search_players",
    {
      title: "Search players",
      description:
        "Search the FIFA player database by name, nationality, club or " +
        "position. Results are sorted by overall rating descending.",
      inputSchema: {
        name: z.string().optional(),
        nationality: z.string().optional().describe('e.g. "Brazil"'),
        club: z.string().optional(),
        position: z.string().optional().describe('e.g. "LW", "GK"'),
        min_overall: z.number().int().optional(),
        limit: z.number().int().positive().max(200).optional().describe("Max rows (default 25)"),
      },
    },
    async (args) => {
      const limit = args.limit ?? 25;
      const all = kb.findPlayers({
        name: args.name,
        nationality: args.nationality,
        club: args.club,
        position: args.position,
        minOverall: args.min_overall,
      });
      const shown = all.slice(0, limit);
      return textResult(formatPlayerList(shown, "Players:", all.length), {
        total: all.length,
        players: shown,
      });
    }
  );

  server.registerTool(
    "club_squads",
    {
      title: "Club squads",
      description:
        "Players grouped by club with squad size and average rating. Filter by " +
        'nationality (e.g. "Brazil") to see Brazilian players per club.',
      inputSchema: {
        nationality: z.string().optional(),
        limit: z.number().int().positive().max(100).optional().describe("Max clubs (default 20)"),
      },
    },
    async (args) => {
      const rows = kb.clubSquads({ nationality: args.nationality, limit: args.limit ?? 20 });
      const header = args.nationality
        ? `${args.nationality} players by club:`
        : "Players by club:";
      return textResult(formatClubSquads(rows, header), { squads: rows });
    }
  );

  server.registerTool(
    "competition_stats",
    {
      title: "Competition statistics",
      description:
        "Aggregate statistics (average goals per match, home/away/draw rates) " +
        "for a competition/season, a team, or the whole dataset.",
      inputSchema: {
        competition: competitionSchema.optional(),
        season: z.number().int().optional(),
        team: z.string().optional(),
      },
    },
    async (args) => {
      const stats = kb.aggregateStats({
        competition: args.competition,
        season: args.season,
        team: args.team,
      });
      const scope = [args.team, args.season !== undefined ? String(args.season) : undefined, args.competition]
        .filter(Boolean)
        .join(" ");
      const header = `Statistics${scope ? ` (${scope})` : " (all data)"}:`;
      return textResult(formatAggregateStats(stats, header), { stats });
    }
  );

  server.registerTool(
    "biggest_wins",
    {
      title: "Biggest wins",
      description: "Largest-margin victories, optionally filtered by competition/season/team.",
      inputSchema: {
        competition: competitionSchema.optional(),
        season: z.number().int().optional(),
        team: z.string().optional(),
        limit: z.number().int().positive().max(50).optional().describe("Default 10"),
      },
    },
    async (args) => {
      const limit = args.limit ?? 10;
      const matches = kb.biggestWins(
        { competition: args.competition, season: args.season, team: args.team },
        limit
      );
      return textResult(formatMatchList(matches, "Biggest victories:"), { matches });
    }
  );

  server.registerTool(
    "dataset_overview",
    {
      title: "Dataset overview",
      description: "Summary of loaded data: match/player counts and available seasons per competition.",
      inputSchema: {},
    },
    async () => {
      const competitions = COMPETITIONS.filter((c) => c !== "Other").map((c) => ({
        competition: c,
        seasons: kb.seasonsFor(c),
      }));
      const lines = [
        `Loaded ${kb.matchCount} matches and ${kb.playerCount} players.`,
        "Competitions and seasons:",
        ...competitions.map((c) => {
          const s = c.seasons;
          const range = s.length ? `${s[0]}–${s[s.length - 1]} (${s.length} seasons)` : "none";
          return `- ${c.competition}: ${range}`;
        }),
      ];
      return textResult(lines.join("\n"), {
        matchCount: kb.matchCount,
        playerCount: kb.playerCount,
        competitions,
      });
    }
  );

  return server;
}
