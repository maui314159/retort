/**
 * brazilian-soccer-mcp / src/server.ts
 *
 * MCP server construction and tool registration.
 *
 * Context block:
 * Builds an `McpServer` (from @modelcontextprotocol/sdk) that exposes the
 * Brazilian soccer datasets as eight MCP tools covering the five required
 * capability categories from TASK.md: match queries (`search_matches`,
 * `head_to_head`), team queries (`team_stats`), player queries
 * (`search_players`, `brazilian_clubs_summary`), competition queries
 * (`standings`), and statistical analysis (`aggregate_stats`,
 * `biggest_wins`). Each tool loads the normalized datasets once (cached in
 * data-loader), runs the appropriate query function, and returns the
 * formatter's human-readable text as the tool result content. Tool argument
 * schemas are declared with zod raw shapes so the SDK validates inputs.
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { loadMatches, loadPlayers } from './data-loader.js';
import {
  findMatches, headToHead, headToHeadMatches, teamStats, aggregateStats,
  biggestWins, standings, findPlayers, brazilianClubsSummary,
} from './queries.js';
import {
  formatMatchList, formatHeadToHead, formatTeamStats, formatStandings,
  formatBiggestWins, formatAggregateStats, formatPlayerList,
  formatBrazilianClubsSummary,
} from './formatter.js';

/** Number of matches to include by default in match-list tool results. */
const DEFAULT_MATCH_LIMIT = 50;

function textResult(text: string) {
  return { content: [{ type: 'text' as const, text }] };
}

/**
 * Build the configured MCP server. Kept separate from the entrypoint so tests
 * can construct the server without binding stdio.
 */
export function createServer(): McpServer {
  const server = new McpServer(
    { name: 'brazilian-soccer-mcp', version: '1.0.0' },
    { capabilities: { tools: {}, prompts: {}, resources: {} } },
  );

  server.registerTool(
    'search_matches',
    {
      description:
        'Search Brazilian soccer matches by team, opponent, competition, season, or date range. ' +
        'Team names are normalized, so "Palmeiras", "Palmeiras-SP" all match. ' +
        'Returns a formatted list of matches (date, score, competition).',
      inputSchema: {
        team: z.string().optional().describe('Team name (home, away, or either).'),
        opponent: z.string().optional().describe('Opponent team name; pairs with "team".'),
        homeTeam: z.string().optional().describe('Specifically the home team.'),
        awayTeam: z.string().optional().describe('Specifically the away team.'),
        competition: z.string().optional().describe('Competition, e.g. "Brasileirão", "Copa do Brasil", "Libertadores", "Serie A".'),
        season: z.number().int().optional().describe('Season year, e.g. 2023.'),
        seasonFrom: z.number().int().optional().describe('Inclusive start season.'),
        seasonTo: z.number().int().optional().describe('Inclusive end season.'),
        dateFrom: z.string().optional().describe('Inclusive start date (YYYY-MM-DD).'),
        dateTo: z.string().optional().describe('Inclusive end date (YYYY-MM-DD).'),
        venue: z.enum(['home', 'away', 'either']).optional().describe('Restrict the "team" filter to a venue.'),
        limit: z.number().int().optional().describe('Max matches to return (default 50).'),
      },
    },
    async (args) => {
      const matches = loadMatches();
      const { limit = DEFAULT_MATCH_LIMIT, ...filter } = args;
      const found = findMatches(matches, filter);
      const heading = `Found ${found.length} matches`;
      return textResult(formatMatchList(found.slice(0, limit), heading));
    },
  );

  server.registerTool(
    'head_to_head',
    {
      description:
        'Compare two teams head-to-head across all match datasets. Returns the win/draw/loss tally and the recent match list.',
      inputSchema: {
        teamA: z.string().describe('First team name.'),
        teamB: z.string().describe('Second team name.'),
      },
    },
    async (args) => {
      const matches = loadMatches();
      const games = headToHeadMatches(matches, args.teamA, args.teamB);
      const summary = headToHead(matches, args.teamA, args.teamB);
      return textResult(formatHeadToHead(summary, games.slice(0, DEFAULT_MATCH_LIMIT)));
    },
  );

  server.registerTool(
    'team_stats',
    {
      description:
        'Calculate aggregate statistics (wins, draws, losses, goals, points, win rate) for a team, optionally filtered by competition, season, and venue.',
      inputSchema: {
        team: z.string().describe('Team name.'),
        competition: z.string().optional(),
        season: z.number().int().optional(),
        venue: z.enum(['home', 'away', 'either']).optional(),
      },
    },
    async (args) => {
      const matches = loadMatches();
      const { team, ...filter } = args;
      const stats = teamStats(matches, team, filter);
      const venueLabel = filter.venue ? filter.venue : undefined;
      return textResult(formatTeamStats(stats, venueLabel));
    },
  );

  server.registerTool(
    'standings',
    {
      description:
        'Compute the standings table for a competition season from match results (3 points for a win, 1 for a draw). The champion (position 1) is labeled.',
      inputSchema: {
        competition: z.string().describe('Competition name, e.g. "Brasileirão" or "Serie A".'),
        season: z.number().int().describe('Season year.'),
      },
    },
    async (args) => {
      const matches = loadMatches();
      const rows = standings(matches, args.competition, args.season);
      return textResult(formatStandings(rows, args.competition, args.season));
    },
  );

  server.registerTool(
    'aggregate_stats',
    {
      description:
        'Compute aggregate statistics (average goals, home/away/draw rates) over a set of matches filtered by competition and/or season.',
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
        team: z.string().optional(),
      },
    },
    async (args) => {
      const matches = loadMatches();
      const { team, ...rest } = args;
      const scoped = findMatches(matches, team ? { team, ...rest } : rest);
      const stats = aggregateStats(scoped);
      const label = [
        args.competition,
        args.season ? String(args.season) : null,
        args.team,
      ].filter(Boolean).join(' ') + ' aggregate stats';
      return textResult(formatAggregateStats(stats, label));
    },
  );

  server.registerTool(
    'biggest_wins',
    {
      description:
        'List the biggest victories (by goal difference) across the match datasets, optionally filtered by competition and/or season.',
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
        limit: z.number().int().optional().describe('Number of results (default 10).'),
      },
    },
    async (args) => {
      const matches = loadMatches();
      const { limit = 10, ...filter } = args;
      const scoped = findMatches(matches, filter);
      const top = biggestWins(scoped, limit);
      return textResult(formatBiggestWins(top));
    },
  );

  server.registerTool(
    'search_players',
    {
      description:
        'Search the FIFA player database by name substring, nationality, club, position, and/or minimum overall rating. Results are ranked by overall rating.',
      inputSchema: {
        name: z.string().optional().describe('Name substring (accent-insensitive).'),
        nationality: z.string().optional().describe('Nationality, e.g. "Brazil".'),
        club: z.string().optional().describe('Club name substring.'),
        position: z.string().optional().describe('Position code, e.g. "ST", "LW", "GK".'),
        minOverall: z.number().int().optional().describe('Minimum overall rating.'),
        limit: z.number().int().optional().describe('Max players to return (default 25).'),
      },
    },
    async (args) => {
      const players = loadPlayers();
      const { limit = 25, ...filter } = args;
      const found = findPlayers(players, { ...filter, limit });
      return textResult(formatPlayerList(found, `Found ${found.length} players`));
    },
  );

  server.registerTool(
    'brazilian_clubs_summary',
    {
      description:
        'Summarize Brazilian players playing at Brazilian clubs in the FIFA dataset: player counts and average overall ratings per club.',
      inputSchema: {},
    },
    async () => {
      const players = loadPlayers();
      const summary = brazilianClubsSummary(players);
      return textResult(formatBrazilianClubsSummary(summary));
    },
  );

  return server;
}
