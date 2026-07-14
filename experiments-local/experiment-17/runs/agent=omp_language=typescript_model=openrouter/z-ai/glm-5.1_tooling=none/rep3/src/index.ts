/**
 * Brazilian Soccer MCP Server - Entry Point
 *
 * Implements an MCP (Model Context Protocol) server exposing six tools
 * for querying Brazilian soccer data loaded from CSV datasets:
 *
 *   search_matches           - Find matches by team, competition, season, date
 *   get_team_stats           - Win/loss/draw records and goals for a team
 *   search_players           - Search FIFA player data by name, club, nationality
 *   get_competition_standings - Calculated league table from match results
 *   get_head_to_head         - Head-to-head comparison between two teams
 *   get_statistics           - Aggregate stats (avg goals, biggest wins, home/away splits)
 *
 * The server communicates over stdio using the MCP SDK transport.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import {
  searchMatches,
  getTeamStats,
  searchPlayers,
  getCompetitionStandings,
  getHeadToHead,
  getAggregateStats,
  formatMatchList,
  formatTeamStats,
  formatPlayerList,
  formatStandings,
  formatHeadToHead,
  formatAggregateStats,
} from "./data.js";

const server = new McpServer({
  name: "brazilian-soccer-mcp",
  version: "1.0.0",
});

// ── Tool: search_matches ─────────────────────────────────────────────

server.tool(
  "search_matches",
  "Search Brazilian soccer matches by team, opponent, competition, season, or date range",
  {
    team: z.string().optional().describe("Team name (partial match, e.g. 'Flamengo')"),
    opponent: z.string().optional().describe("Opponent team name (partial match)"),
    competition: z
      .enum(["Brasileirão", "Copa do Brasil", "Libertadores", "Historical Brasileirão", "Other"])
      .optional()
      .describe("Competition filter"),
    season: z.number().optional().describe("Season year (e.g. 2023)"),
    startDate: z.string().optional().describe("Start date (YYYY-MM-DD)"),
    endDate: z.string().optional().describe("End date (YYYY-MM-DD)"),
    limit: z.number().optional().describe("Max results to return"),
  },
  async (params) => {
    const matches = searchMatches(params);
    const text = formatMatchList(matches);
    return { content: [{ type: "text", text }] };
  },
);

// ── Tool: get_team_stats ─────────────────────────────────────────────

server.tool(
  "get_team_stats",
  "Get team statistics including wins, losses, draws, and goals",
  {
    team: z.string().describe("Team name (e.g. 'Palmeiras')"),
    season: z.number().optional().describe("Filter by season year"),
    competition: z
      .enum(["Brasileirão", "Copa do Brasil", "Libertadores", "Historical Brasileirão", "Other"])
      .optional()
      .describe("Filter by competition"),
    homeOnly: z.boolean().optional().describe("If true, home matches only; if false, away only; omit for both"),
  },
  async (params) => {
    const stats = getTeamStats(params.team, params.season, params.competition, params.homeOnly);
    return { content: [{ type: "text", text: formatTeamStats(stats) }] };
  },
);

// ── Tool: search_players ─────────────────────────────────────────────

server.tool(
  "search_players",
  "Search FIFA player data by name, nationality, club, or position",
  {
    name: z.string().optional().describe("Player name (partial match)"),
    nationality: z.string().optional().describe("Nationality (e.g. 'Brazil')"),
    club: z.string().optional().describe("Club name (partial match, e.g. 'Flamengo')"),
    position: z.string().optional().describe("Position code (e.g. 'ST', 'LW', 'GK')"),
    minOverall: z.number().optional().describe("Minimum overall rating"),
    maxOverall: z.number().optional().describe("Maximum overall rating"),
    limit: z.number().optional().describe("Max results to return"),
  },
  async (params) => {
    const players = searchPlayers(params);
    return { content: [{ type: "text", text: formatPlayerList(players) }] };
  },
);

// ── Tool: get_competition_standings ──────────────────────────────────

server.tool(
  "get_competition_standings",
  "Calculate competition standings (league table) from match results for a given season",
  {
    competition: z
      .enum(["Brasileirão", "Copa do Brasil", "Libertadores", "Historical Brasileirão", "Other"])
      .describe("Competition name"),
    season: z.number().describe("Season year"),
  },
  async (params) => {
    const standings = getCompetitionStandings(params);
    return { content: [{ type: "text", text: formatStandings(standings) }] };
  },
);

// ── Tool: get_head_to_head ───────────────────────────────────────────

server.tool(
  "get_head_to_head",
  "Compare two teams head-to-head: wins, draws, goals, and recent matches",
  {
    teamA: z.string().describe("First team name"),
    teamB: z.string().describe("Second team name"),
  },
  async (params) => {
    const h2h = getHeadToHead(params.teamA, params.teamB);
    return { content: [{ type: "text", text: formatHeadToHead(h2h) }] };
  },
);

// ── Tool: get_statistics ─────────────────────────────────────────────

server.tool(
  "get_statistics",
  "Get aggregate statistics: average goals, home/away win rates, biggest victories",
  {
    competition: z
      .enum(["Brasileirão", "Copa do Brasil", "Libertadores", "Historical Brasileirão", "Other"])
      .optional()
      .describe("Filter by competition"),
    season: z.number().optional().describe("Filter by season year"),
    team: z.string().optional().describe("Filter by team name"),
  },
  async (params) => {
    const stats = getAggregateStats(params);
    return { content: [{ type: "text", text: formatAggregateStats(stats) }] };
  },
);

// ── Start ────────────────────────────────────────────────────────────

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  console.error("Fatal error starting MCP server:", err);
  process.exit(1);
});
