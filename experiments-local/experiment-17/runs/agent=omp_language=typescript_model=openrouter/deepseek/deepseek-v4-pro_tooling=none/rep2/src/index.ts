#!/usr/bin/env node
/**
 * Brazilian Soccer MCP Server
 *
 * Provides a knowledge-graph interface for Brazilian soccer data
 * through the Model Context Protocol. Loads 6 CSV datasets on startup
 * and exposes tools for match queries, player searches, team statistics,
 * head-to-head comparisons, competition standings, and statistical analysis.
 *
 * Data sources:
 * - Brasileirao_Matches.csv (CC BY 4.0)
 * - Brazilian_Cup_Matches.csv (CC BY 4.0)
 * - Libertadores_Matches.csv (CC BY 4.0)
 * - BR-Football-Dataset.csv (CC0 Public Domain)
 * - novo_campeonato_brasileiro.csv (CC BY 4.0)
 * - fifa_data.csv (Apache 2.0)
 */
import { McpServer, StdioServerTransport } from "@modelcontextprotocol/server";
import * as z from "zod/v4";

import { loadAllData } from "./loader.js";
import {
  searchMatches,
  searchPlayers,
  getTeamStats,
  headToHead,
  competitionStandings,
  biggestWins,
  goalsPerMatch,
  topTeams,
  bestRecord,
} from "./tools.js";

const data = loadAllData();

const server = new McpServer({
  name: "brazilian-soccer-mcp",
  version: "1.0.0",
});

// ─── search_matches ─────────────────────────────────────────────────────────

server.registerTool(
  "search_matches",
  {
    description:
      "Search Brazilian soccer matches by team, opponent, competition, season, or date range. Returns match dates, scores, and competition details.",
    inputSchema: z.object({
      team: z.string().optional().describe("Team name (e.g., 'Flamengo', 'Palmeiras')"),
      opponent: z.string().optional().describe("Opponent team name for head-to-head filtering"),
      competition: z.string().optional().describe("Competition name (e.g., 'Brasileirão', 'Copa do Brasil', 'Copa Libertadores')"),
      season: z.number().int().optional().describe("Season year (e.g., 2023)"),
      dateFrom: z.string().optional().describe("Start date in YYYY-MM-DD format"),
      dateTo: z.string().optional().describe("End date in YYYY-MM-DD format"),
      limit: z.number().int().default(50).describe("Maximum number of results to return"),
    }),
  },
  async (args) => searchMatches(data, args),
);

// ─── search_players ─────────────────────────────────────────────────────────

server.registerTool(
  "search_players",
  {
    description:
      "Search FIFA player data by name, nationality, club, position, or overall rating range.",
    inputSchema: z.object({
      name: z.string().optional().describe("Player name (e.g., 'Neymar', 'Gabriel Barbosa')"),
      nationality: z.string().optional().describe("Nationality (e.g., 'Brazil', 'Argentina')"),
      club: z.string().optional().describe("Club name (e.g., 'Flamengo', 'Real Madrid')"),
      position: z.string().optional().describe("Playing position (e.g., 'ST', 'LW', 'GK', 'CDM')"),
      minOverall: z.number().int().optional().describe("Minimum overall rating"),
      maxOverall: z.number().int().optional().describe("Maximum overall rating"),
      limit: z.number().int().default(50).describe("Maximum number of results to return"),
    }),
  },
  async (args) => searchPlayers(data, args),
);

// ─── get_team_stats ─────────────────────────────────────────────────────────

server.registerTool(
  "get_team_stats",
  {
    description:
      "Get win/loss/draw records, goals scored, and win rate for a team. Optionally filter by competition, season, or home-only matches.",
    inputSchema: z.object({
      team: z.string().describe("Team name (e.g., 'Corinthians', 'São Paulo')"),
      competition: z.string().optional().describe("Filter by competition"),
      season: z.number().int().optional().describe("Filter by season year"),
      homeOnly: z.boolean().optional().describe("If true, only include home matches"),
    }),
  },
  async (args) => getTeamStats(data, args),
);

// ─── head_to_head ────────────────────────────────────────────────────────────

server.registerTool(
  "head_to_head",
  {
    description:
      "Compare two teams head-to-head: shows all matches between them and win/loss/draw records.",
    inputSchema: z.object({
      teamA: z.string().describe("First team name"),
      teamB: z.string().describe("Second team name"),
    }),
  },
  async (args) => headToHead(data, args),
);

// ─── competition_standings ──────────────────────────────────────────────────

server.registerTool(
  "competition_standings",
  {
    description:
      "Calculate competition standings for a given season from match results. Returns positions, points, and statistics.",
    inputSchema: z.object({
      competition: z.string().describe("Competition name (e.g., 'Brasileirão', 'Copa do Brasil')"),
      season: z.number().int().describe("Season year"),
    }),
  },
  async (args) => competitionStandings(data, args),
);

// ─── biggest_wins ────────────────────────────────────────────────────────────

server.registerTool(
  "biggest_wins",
  {
    description:
      "Find the biggest victories by goal difference. Optionally filter by competition.",
    inputSchema: z.object({
      competition: z.string().optional().describe("Filter by competition"),
      limit: z.number().int().default(20).describe("Maximum number of results"),
    }),
  },
  async (args) => biggestWins(data, args),
);

// ─── goals_per_match ────────────────────────────────────────────────────────

server.registerTool(
  "goals_per_match",
  {
    description:
      "Calculate average goals per match, home/away win rates, and draw rates. Optionally filter by competition and season.",
    inputSchema: z.object({
      competition: z.string().optional().describe("Filter by competition"),
      season: z.number().int().optional().describe("Filter by season year"),
    }),
  },
  async (args) => goalsPerMatch(data, args),
);

// ─── top_teams ───────────────────────────────────────────────────────────────

server.registerTool(
  "top_teams",
  {
    description:
      "Rank teams by a metric: wins, goals for, goals against, or win rate. Optionally filter by competition and season.",
    inputSchema: z.object({
      competition: z.string().optional().describe("Filter by competition"),
      season: z.number().int().optional().describe("Filter by season year"),
      metric: z.enum(["wins", "goalsFor", "goalsAgainst", "winRate"]).default("wins")
        .describe("Ranking metric"),
      limit: z.number().int().default(10).describe("Maximum number of teams"),
    }),
  },
  async (args) => topTeams(data, args),
);

// ─── best_record ─────────────────────────────────────────────────────────────

server.registerTool(
  "best_record",
  {
    description:
      "Find teams with the best home or away record based on win rate.",
    inputSchema: z.object({
      venue: z.enum(["home", "away"]).describe("'home' or 'away'"),
      competition: z.string().optional().describe("Filter by competition"),
      season: z.number().int().optional().describe("Filter by season year"),
      limit: z.number().int().default(10).describe("Maximum number of teams"),
    }),
  },
  async (args) => bestRecord(data, args),
);

// ─── Start ───────────────────────────────────────────────────────────────────

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  console.error("Failed to start MCP server:", err);
  process.exit(1);
});