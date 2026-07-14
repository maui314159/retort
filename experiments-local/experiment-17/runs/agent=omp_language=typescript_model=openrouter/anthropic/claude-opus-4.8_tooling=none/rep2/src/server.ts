/**
 * Context
 * -------
 * Defines the MCP server and its tools over a `SoccerGraph`. Tools map 1:1 onto
 * the spec's capability categories and return spec-shaped text content:
 *
 *   - find_matches        : matches by team/opponent/competition/season/dates
 *   - team_record         : W/D/L + goals + win rate (optionally home/away)
 *   - head_to_head        : aggregated rivalry record + recent matches
 *   - find_players        : FIFA players by name/nationality/club/position
 *   - standings           : league table computed from match results
 *   - competition_stats   : goals/match, home-win rate, totals
 *   - biggest_wins        : largest-margin victories
 *
 * `createServer(graph)` is exported so tests can build a server against a graph
 * loaded from a fixture directory without spawning a process.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

import {
  formatHeadToHead,
  formatMatchList,
  formatPlayers,
  formatStandings,
  formatStats,
  formatTeamRecord,
} from "./format.js";
import type { Competition } from "./models.js";
import { resolveCompetition, type SoccerGraph } from "./service.js";

const DEFAULT_MATCH_LIMIT = 25;
const DEFAULT_PLAYER_LIMIT = 20;

/** Wrap plain text into a CallToolResult content array. */
function text(body: string) {
  return { content: [{ type: "text" as const, text: body }] };
}

/** Resolve a competition string, returning either the label or an error result. */
function competitionOrError(value: string | undefined): { competition?: Competition; error?: string } {
  if (value === undefined) return {};
  const competition = resolveCompetition(value);
  if (!competition) {
    return {
      error: `Unknown competition "${value}". Try: Serie A / Brasileirão, Serie B, Serie C, Copa do Brasil, Libertadores.`,
    };
  }
  return { competition };
}

const competitionField = z
  .string()
  .optional()
  .describe('Competition name: "Serie A"/"Brasileirão", "Serie B", "Serie C", "Copa do Brasil", or "Libertadores".');

export function createServer(graph: SoccerGraph): McpServer {
  const server = new McpServer(
    { name: "brazilian-soccer-mcp", version: "1.0.0" },
    {
      instructions:
        "Knowledge graph over Brazilian soccer datasets (matches across Brasileirão Série A/B/C, " +
        "Copa do Brasil, and Copa Libertadores, plus FIFA player data). Use the tools to answer " +
        "questions about matches, team records, head-to-head rivalries, players, league standings, " +
        "and aggregate statistics. Team names are normalized, so 'Flamengo', 'Flamengo-RJ' all match.",
    },
  );

  server.registerTool(
    "find_matches",
    {
      title: "Find matches",
      description:
        "Search matches by team, opponent, competition, season, and/or date range. " +
        "Returns a chronological list (newest first) with scores and competition context.",
      inputSchema: {
        team: z.string().optional().describe("Team on either side (home or away), e.g. 'Flamengo'."),
        opponent: z.string().optional().describe("Restrict to matches that also involve this team (head-to-head)."),
        homeTeam: z.string().optional().describe("Require this specific home team."),
        awayTeam: z.string().optional().describe("Require this specific away team."),
        competition: competitionField,
        season: z.number().int().optional().describe("Season year, e.g. 2019."),
        from: z.string().optional().describe("Inclusive start date, ISO 'YYYY-MM-DD'."),
        to: z.string().optional().describe("Inclusive end date, ISO 'YYYY-MM-DD'."),
        limit: z.number().int().positive().optional().describe(`Max matches to show (default ${DEFAULT_MATCH_LIMIT}).`),
      },
    },
    async (args) => {
      const { competition, error } = competitionOrError(args.competition);
      if (error) return text(error);

      const all = graph.findMatches({
        team: args.team,
        opponent: args.opponent,
        homeTeam: args.homeTeam,
        awayTeam: args.awayTeam,
        competition,
        season: args.season,
        from: args.from,
        to: args.to,
      });
      const limit = args.limit ?? DEFAULT_MATCH_LIMIT;
      const shown = all.slice(0, limit);

      const parts: string[] = [];
      const titleBits = [args.team, args.opponent && `vs ${args.opponent}`, competition, args.season]
        .filter(Boolean)
        .join(" ");
      parts.push(formatMatchList(titleBits ? `Matches: ${titleBits}` : "Matches", all, shown));

      if (args.team && args.opponent) {
        const h2h = graph.headToHead(args.team, args.opponent, { competition, season: args.season });
        parts.push("", formatHeadToHead(args.team, args.opponent, h2h));
      }
      return text(parts.join("\n"));
    },
  );

  server.registerTool(
    "team_record",
    {
      title: "Team record",
      description:
        "Win/draw/loss record, goals for/against, and win rate for a team, " +
        "optionally scoped by competition, season, and venue (home/away).",
      inputSchema: {
        team: z.string().describe("Team name, e.g. 'Corinthians'."),
        competition: competitionField,
        season: z.number().int().optional().describe("Season year, e.g. 2022."),
        venue: z.enum(["home", "away", "all"]).optional().describe("Restrict to home or away matches (default all)."),
      },
    },
    async (args) => {
      const { competition, error } = competitionOrError(args.competition);
      if (error) return text(error);

      const record = graph.teamRecord(args.team, { competition, season: args.season, venue: args.venue });
      const scope = [
        args.team,
        args.venue && args.venue !== "all" ? `${args.venue} record` : "record",
        competition,
        args.season,
      ]
        .filter(Boolean)
        .join(" ");
      return text(formatTeamRecord(scope, record));
    },
  );

  server.registerTool(
    "head_to_head",
    {
      title: "Head-to-head",
      description: "Aggregated rivalry record between two teams, plus the most recent matches.",
      inputSchema: {
        teamA: z.string().describe("First team."),
        teamB: z.string().describe("Second team."),
        competition: competitionField,
        season: z.number().int().optional().describe("Season year to restrict to."),
        limit: z.number().int().positive().optional().describe(`Recent matches to list (default ${DEFAULT_MATCH_LIMIT}).`),
      },
    },
    async (args) => {
      const { competition, error } = competitionOrError(args.competition);
      if (error) return text(error);

      const h2h = graph.headToHead(args.teamA, args.teamB, { competition, season: args.season });
      const limit = args.limit ?? DEFAULT_MATCH_LIMIT;
      const list = formatMatchList(
        `${args.teamA} vs ${args.teamB}`,
        h2h.matches,
        h2h.matches.slice(0, limit),
      );
      return text(`${list}\n\n${formatHeadToHead(args.teamA, args.teamB, h2h)}`);
    },
  );

  server.registerTool(
    "find_players",
    {
      title: "Find players",
      description:
        "Search FIFA player data by name, nationality, club, and/or position. " +
        "Results are ranked by overall rating (highest first).",
      inputSchema: {
        name: z.string().optional().describe("Player name substring, e.g. 'Gabriel Barbosa'."),
        nationality: z.string().optional().describe("Exact nationality, e.g. 'Brazil'."),
        club: z.string().optional().describe("Club name substring, e.g. 'Flamengo'."),
        position: z.string().optional().describe("Exact position code, e.g. 'GK', 'ST', 'LW'."),
        minOverall: z.number().int().optional().describe("Minimum FIFA overall rating."),
        limit: z.number().int().positive().optional().describe(`Max players to show (default ${DEFAULT_PLAYER_LIMIT}).`),
      },
    },
    async (args) => {
      const all = graph.findPlayers({
        name: args.name,
        nationality: args.nationality,
        club: args.club,
        position: args.position,
        minOverall: args.minOverall,
      });
      const limit = args.limit ?? DEFAULT_PLAYER_LIMIT;
      const titleBits = [args.position, args.nationality && `${args.nationality} players`, args.club && `at ${args.club}`, args.name && `matching '${args.name}'`]
        .filter(Boolean)
        .join(" ");
      return text(formatPlayers(titleBits ? `Players: ${titleBits}` : "Players", all.slice(0, limit), all.length));
    },
  );

  server.registerTool(
    "standings",
    {
      title: "League standings",
      description:
        "Final league table for a competition + season, computed from match results " +
        "(3 pts win / 1 draw), sorted by points then goal difference.",
      inputSchema: {
        competition: z
          .string()
          .describe('Competition name, e.g. "Serie A"/"Brasileirão", "Serie B", "Copa do Brasil".'),
        season: z.number().int().describe("Season year, e.g. 2019."),
        limit: z.number().int().positive().optional().describe("Top N rows to show (default: full table)."),
      },
    },
    async (args) => {
      const { competition, error } = competitionOrError(args.competition);
      if (error || !competition) return text(error ?? "Unknown competition.");

      const rows = graph.standings(competition, args.season);
      const shown = args.limit && args.limit > 0 ? rows.slice(0, args.limit) : rows;
      return text(formatStandings(`${competition} ${args.season} standings (calculated from matches)`, shown));
    },
  );

  server.registerTool(
    "competition_stats",
    {
      title: "Competition statistics",
      description:
        "Aggregate statistics for a competition (optionally a single season): match count, " +
        "total goals, goals per match, home/away win counts, and home win rate.",
      inputSchema: {
        competition: z.string().describe('Competition name, e.g. "Serie A"/"Brasileirão", "Libertadores".'),
        season: z.number().int().optional().describe("Season year; omit for all seasons."),
      },
    },
    async (args) => {
      const { competition, error } = competitionOrError(args.competition);
      if (error || !competition) return text(error ?? "Unknown competition.");
      return text(formatStats(graph.competitionStats(competition, args.season)));
    },
  );

  server.registerTool(
    "biggest_wins",
    {
      title: "Biggest wins",
      description: "Largest goal-margin victories in the dataset, optionally scoped by competition and season.",
      inputSchema: {
        competition: competitionField,
        season: z.number().int().optional().describe("Season year to restrict to."),
        limit: z.number().int().positive().optional().describe("Number of matches to list (default 10)."),
      },
    },
    async (args) => {
      const { competition, error } = competitionOrError(args.competition);
      if (error) return text(error);

      const limit = args.limit ?? 10;
      const matches = graph.biggestWins({ competition, season: args.season, limit });
      const scope = [competition, args.season].filter(Boolean).join(" ");
      return text(formatMatchList(scope ? `Biggest wins: ${scope}` : "Biggest wins", matches, matches));
    },
  );

  return server;
}
