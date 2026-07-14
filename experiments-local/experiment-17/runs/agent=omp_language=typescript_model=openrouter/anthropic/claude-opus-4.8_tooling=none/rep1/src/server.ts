#!/usr/bin/env node
/**
 * Context
 * =======
 * MCP server entry point for Brazilian soccer data.
 *
 * Exposes the DataStore query engine (store.ts) as MCP tools over stdio so an
 * LLM client can answer natural-language questions about matches, teams,
 * players, competitions, and statistics. Tools accept loosely-typed, normalized
 * arguments (team/competition spellings are canonicalized inside the store) and
 * return human-readable text built by format.ts.
 *
 * The corpus is loaded once at startup from data/kaggle/ (override with the
 * SOCCER_DATA_DIR env var) and held in memory for sub-second queries. Startup
 * progress is logged to stderr to keep stdout clean for the MCP JSON-RPC stream.
 *
 * Tools:
 *   search_matches      — find matches by team/opponent/competition/season/date
 *   team_record         — W/D/L + goals for a team (filterable by venue/season)
 *   head_to_head        — meeting history + tally between two teams
 *   standings           — computed league table for a competition + season
 *   search_players      — FIFA players by name/nationality/club/position/rating
 *   club_roster         — players whose FIFA club matches a (Brazilian) club
 *   league_stats        — aggregate goals/win-rate stats over a filtered set
 *   biggest_wins        — largest-margin victories over a filtered set
 *   list_competitions   — competitions available in the loaded data
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { DataStore } from './store.js';
import {
  formatBiggestWins,
  formatHeadToHead,
  formatLeagueStats,
  formatMatches,
  formatPlayers,
  formatStandings,
  formatTeamRecord,
} from './format.js';

const DATA_DIR = process.env.SOCCER_DATA_DIR ?? 'data/kaggle';

const text = (body: string) => ({ content: [{ type: 'text' as const, text: body }] });

/**
 * Register all query tools on `server` backed by `store`. Exported so tests can
 * exercise registration against an in-memory store without spawning a process.
 */
export function registerTools(server: McpServer, store: DataStore): void {
  server.registerTool(
    'search_matches',
    {
      title: 'Search matches',
      description:
        'Find matches by team, opponent, competition, season, or date range. Team and competition names are matched flexibly (accents and state suffixes like "-SP" are ignored).',
      inputSchema: {
        team: z.string().optional().describe('Team name (matches home or away unless restricted).'),
        opponent: z.string().optional().describe('Restrict to matches against this opponent.'),
        venue: z.enum(['home', 'away', 'any']).optional().describe('Restrict the team to home/away matches.'),
        competition: z
          .string()
          .optional()
          .describe('Brasileirão, Copa do Brasil, or Libertadores.'),
        season: z.number().int().optional().describe('Season year, e.g. 2019.'),
        dateFrom: z.string().optional().describe('Inclusive ISO date lower bound (YYYY-MM-DD).'),
        dateTo: z.string().optional().describe('Inclusive ISO date upper bound (YYYY-MM-DD).'),
        limit: z.number().int().min(1).max(500).optional().describe('Max results (default 50).'),
      },
    },
    async (args) => {
      const all = store.findMatches({
        team: args.team,
        opponent: args.opponent,
        homeOnly: args.venue === 'home',
        awayOnly: args.venue === 'away',
        competition: args.competition,
        season: args.season,
        dateFrom: args.dateFrom,
        dateTo: args.dateTo,
        limit: 100000,
      });
      const limit = args.limit ?? 50;
      return text(formatMatches(all.slice(0, limit), all.length));
    },
  );

  server.registerTool(
    'team_record',
    {
      title: 'Team record',
      description:
        'Win/draw/loss record and goals for a team, optionally filtered by competition, season, and venue (home/away).',
      inputSchema: {
        team: z.string().describe('Team name.'),
        competition: z.string().optional(),
        season: z.number().int().optional(),
        venue: z.enum(['home', 'away', 'all']).optional().describe('Default all.'),
      },
    },
    async (args) => {
      const rec = store.teamRecord(args.team, {
        competition: args.competition,
        season: args.season,
        venue: args.venue,
      });
      const scopeParts: string[] = [];
      if (args.venue && args.venue !== 'all') scopeParts.push(`${args.venue} only`);
      if (args.competition) scopeParts.push(args.competition);
      if (args.season !== undefined) scopeParts.push(String(args.season));
      return text(formatTeamRecord(args.team, rec, scopeParts.join(', ')));
    },
  );

  server.registerTool(
    'head_to_head',
    {
      title: 'Head to head',
      description: 'Compare two teams head-to-head: meeting history and win/draw tally.',
      inputSchema: {
        teamA: z.string(),
        teamB: z.string(),
        competition: z.string().optional(),
        limit: z.number().int().min(1).max(200).optional().describe('Max meetings listed (default 20).'),
      },
    },
    async (args) => {
      const h2h = store.headToHead(args.teamA, args.teamB, {
        competition: args.competition,
        limit: args.limit ?? 20,
      });
      return text(formatHeadToHead(h2h));
    },
  );

  server.registerTool(
    'standings',
    {
      title: 'League standings',
      description:
        'Compute a league table for a competition and season from match results (3 pts win, 1 draw).',
      inputSchema: {
        competition: z.string().describe('Brasileirão, Copa do Brasil, or Libertadores.'),
        season: z.number().int().describe('Season year.'),
        limit: z.number().int().min(1).max(30).optional().describe('Rows shown (default 20).'),
      },
    },
    async (args) => {
      const rows = store.standings(args.competition, args.season);
      return text(formatStandings(args.competition, args.season, rows, args.limit ?? 20));
    },
  );

  server.registerTool(
    'search_players',
    {
      title: 'Search players',
      description:
        'Search the FIFA player database by name, nationality, club, position, and minimum overall rating. Results sorted by rating.',
      inputSchema: {
        name: z.string().optional().describe('Substring of the player name.'),
        nationality: z.string().optional().describe('e.g. Brazil.'),
        club: z.string().optional().describe('Club name (matched flexibly).'),
        position: z.string().optional().describe('e.g. ST, GK, LW.'),
        minOverall: z.number().int().optional().describe('Minimum FIFA overall rating.'),
        limit: z.number().int().min(1).max(200).optional().describe('Max results (default 25).'),
      },
    },
    async (args) => {
      const all = store.findPlayers({
        name: args.name,
        nationality: args.nationality,
        club: args.club,
        position: args.position,
        minOverall: args.minOverall,
        limit: 100000,
      });
      const limit = args.limit ?? 25;
      return text(formatPlayers(all.slice(0, limit), all.length));
    },
  );

  server.registerTool(
    'club_roster',
    {
      title: 'Club roster',
      description: 'List FIFA players at a given club, highest-rated first.',
      inputSchema: {
        club: z.string().describe('Club name (matched flexibly).'),
        limit: z.number().int().min(1).max(100).optional().describe('Max players (default 30).'),
      },
    },
    async (args) => {
      const all = store.findPlayers({ club: args.club, limit: 100000 });
      const limit = args.limit ?? 30;
      return text(formatPlayers(all.slice(0, limit), all.length));
    },
  );

  server.registerTool(
    'league_stats',
    {
      title: 'League statistics',
      description:
        'Aggregate statistics (match count, total/average goals, home/away/draw win rates) over an optionally filtered set.',
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
      },
    },
    async (args) => {
      const stats = store.leagueStats({ competition: args.competition, season: args.season });
      const scopeParts: string[] = [];
      if (args.competition) scopeParts.push(args.competition);
      if (args.season !== undefined) scopeParts.push(String(args.season));
      return text(formatLeagueStats(scopeParts.join(' '), stats));
    },
  );

  server.registerTool(
    'biggest_wins',
    {
      title: 'Biggest wins',
      description: 'Largest-margin victories over an optionally filtered set of matches.',
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
        limit: z.number().int().min(1).max(50).optional().describe('Max results (default 10).'),
      },
    },
    async (args) => {
      const matches = store.biggestWins({
        competition: args.competition,
        season: args.season,
        limit: args.limit ?? 10,
      });
      const scopeParts: string[] = [];
      if (args.competition) scopeParts.push(args.competition);
      if (args.season !== undefined) scopeParts.push(String(args.season));
      return text(formatBiggestWins(matches, scopeParts.join(' ')));
    },
  );

  server.registerTool(
    'list_competitions',
    {
      title: 'List competitions',
      description: 'List the competitions available in the loaded dataset.',
      inputSchema: {},
    },
    async () => text(`Available competitions:\n${store.competitions().map((c) => `- ${c}`).join('\n')}`),
  );
}

async function main(): Promise<void> {
  process.stderr.write(`[brazilian-soccer-mcp] loading data from ${DATA_DIR} ...\n`);
  const store = DataStore.fromDataDir(DATA_DIR);
  process.stderr.write(
    `[brazilian-soccer-mcp] loaded ${store.matches.length} matches, ${store.players.length} players\n`,
  );

  const server = new McpServer({ name: 'brazilian-soccer-mcp', version: '1.0.0' });
  registerTools(server, store);

  const transport = new StdioServerTransport();
  await server.connect(transport);
  process.stderr.write('[brazilian-soccer-mcp] ready on stdio\n');
}

main().catch((err) => {
  process.stderr.write(`[brazilian-soccer-mcp] fatal: ${err instanceof Error ? err.stack : String(err)}\n`);
  process.exit(1);
});
