#!/usr/bin/env node
/**
 * Brazilian Soccer MCP server entry point.
 *
 * Exposes tools that answer natural-language questions about Brazilian
 * soccer over the bundled Kaggle datasets:
 *
 *   - `brazilian_soccer.find_matches`
 *   - `brazilian_soccer.head_to_head`
 *   - `brazilian_soccer.team_record`
 *   - `brazilian_soccer.standings`
 *   - `brazilian_soccer.find_players`
 *   - `brazilian_soccer.club_roster`
 *   - `brazilian_soccer.brazilian_players_by_club`
 *   - `brazilian_soccer.competition_stats`
 *   - `brazilian_soccer.biggest_wins`
 *   - `brazilian_soccer.best_home_record`
 *   - `brazilian_soccer.last_match`
 *
 * The server is a stdio MCP transport. Run with `node dist/index.js`
 * (after `npm run build`) and connect from any MCP-aware client.
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';

import { loadDataset } from './data/loader.js';
import type { Competition, DatasetSnapshot } from './data/types.js';
import { findMatches, mostRecentMatch, type MatchQuery } from './queries/matches.js';
import { headToHead, standings, teamRecord } from './queries/teams.js';
import type { TeamQuery } from './queries/teams.js';
import { findPlayers, clubRoster, clubsByNationality, type PlayerQuery } from './queries/players.js';
import { biggestWins, bestHomeRecord, goalsStats } from './queries/statistics.js';

const COMPETITION_VALUES = [
  'brasileirao',
  'copa_do_brasil',
  'libertadores',
  'brasileirao_historical',
  'br_football'
] as const;

const competitionSchema = z.union([z.enum(COMPETITION_VALUES), z.array(z.enum(COMPETITION_VALUES))]).optional();
const seasonSchema = z.union([z.number().int(), z.tuple([z.number().int(), z.number().int()])]).optional();
const dateSchema = z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'YYYY-MM-DD').optional();

/** Convert a tool argument bag into a {@link MatchQuery}. */
function toMatchQuery(args: { competition?: Competition | Competition[]; season?: number | [number, number]; from?: string; to?: string }): MatchQuery {
  const q: MatchQuery = {};
  if (args.competition !== undefined) q.competition = args.competition;
  if (args.season !== undefined) q.season = args.season;
  if (args.from || args.to) q.dateRange = [args.from ?? '0000-00-00', args.to ?? '9999-12-31'];
  return q;
}

function toPlayerQuery(args: { name?: string; nationality?: string; club?: string; position?: string; minOverall?: number; limit?: number }): PlayerQuery {
  const q: PlayerQuery = {};
  if (args.name !== undefined) q.name = args.name;
  if (args.nationality !== undefined) q.nationality = args.nationality;
  if (args.club !== undefined) q.club = args.club;
  if (args.position !== undefined) q.position = args.position;
  if (args.minOverall !== undefined) q.minOverall = args.minOverall;
  if (args.limit !== undefined) q.limit = args.limit;
  return q;
}

function jsonResult(value: unknown) {
  return { content: [{ type: 'text' as const, text: JSON.stringify(value, null, 2) }] };
}

export function buildServer(snap: DatasetSnapshot): McpServer {
  const server = new McpServer(
    { name: 'brazilian-soccer-mcp', version: '0.1.0' },
    { capabilities: { tools: {} } }
  );

  server.registerTool(
    'brazilian_soccer.find_matches',
    {
      title: 'Find matches',
      description:
        'Find matches by team (and optional second team), competition, season and date range. Team names are matched fuzzily across the supplied datasets.',
      inputSchema: {
        team: z.string().describe('Team name. Can be canonical ("Flamengo") or any source variant ("Flamengo-RJ", "Sao Paulo").'),
        team2: z.string().optional().describe('Optional second team; when supplied returns only matches between the two sides.'),
        competition: competitionSchema,
        season: seasonSchema,
        from: dateSchema,
        to: dateSchema,
        limit: z.number().int().min(1).max(500).optional(),
        includeUnknownScores: z.boolean().optional()
      }
    },
    args => {
      const q = toMatchQuery(args);
      q.team = args.team;
      if (args.team2 !== undefined) q.team2 = args.team2;
      q.limit = args.limit ?? 50;
      if (args.includeUnknownScores !== undefined) q.includeUnknownScores = args.includeUnknownScores;
      return Promise.resolve(jsonResult(findMatches(snap, q)));
    }
  );

  server.registerTool(
    'brazilian_soccer.head_to_head',
    {
      title: 'Head-to-head comparison',
      description: 'Compare two teams head-to-head, optionally constrained to a competition/season/date range.',
      inputSchema: {
        team1: z.string(),
        team2: z.string(),
        competition: competitionSchema,
        season: seasonSchema,
        from: dateSchema,
        to: dateSchema
      }
    },
    args => {
      const q: TeamQuery = toMatchQuery(args);
      return Promise.resolve(jsonResult(headToHead(snap, args.team1, args.team2, q)));
    }
  );

  server.registerTool(
    'brazilian_soccer.team_record',
    {
      title: 'Team record',
      description: 'Win/loss/draw + goals for a team, optionally constrained to a competition or season.',
      inputSchema: {
        team: z.string(),
        competition: competitionSchema,
        season: seasonSchema,
        from: dateSchema,
        to: dateSchema
      }
    },
    args => {
      const q: TeamQuery = toMatchQuery(args);
      return Promise.resolve(jsonResult(teamRecord(snap, args.team, q)));
    }
  );

  server.registerTool(
    'brazilian_soccer.standings',
    {
      title: 'Season standings',
      description: 'Compute a league table for a given season and competition from match results.',
      inputSchema: {
        season: z.number().int(),
        competition: z.enum(COMPETITION_VALUES).optional()
      }
    },
    args => Promise.resolve(jsonResult(standings(snap, args.season, args.competition)))
  );

  server.registerTool(
    'brazilian_soccer.find_players',
    {
      title: 'Find players',
      description: 'Search the FIFA player database by name, nationality, club and/or position.',
      inputSchema: {
        name: z.string().optional(),
        nationality: z.string().optional(),
        club: z.string().optional(),
        position: z.string().optional(),
        minOverall: z.number().int().min(0).max(99).optional(),
        limit: z.number().int().min(1).max(500).optional()
      }
    },
    args => Promise.resolve(jsonResult(findPlayers(snap, toPlayerQuery(args))))
  );

  server.registerTool(
    'brazilian_soccer.club_roster',
    {
      title: 'Club roster',
      description: 'Returns the players at a club with the average overall rating and the top-rated players.',
      inputSchema: {
        club: z.string(),
        limit: z.number().int().min(1).max(50).optional()
      }
    },
    args => Promise.resolve(jsonResult(clubRoster(snap, args.club, args.limit ?? 10)))
  );

  server.registerTool(
    'brazilian_soccer.brazilian_players_by_club',
    {
      title: 'Brazilian players grouped by club',
      description: 'Aggregate Brazilian-nationality players by their club, ranked by number of players then average rating.',
      inputSchema: {
        minPlayers: z.number().int().min(1).max(20).optional(),
        limit: z.number().int().min(1).max(200).optional()
      }
    },
    args => {
      const list = clubsByNationality(snap, 'Brazil', args.minPlayers ?? 1);
      return Promise.resolve(jsonResult(args.limit ? list.slice(0, args.limit) : list));
    }
  );

  server.registerTool(
    'brazilian_soccer.competition_stats',
    {
      title: 'Competition statistics',
      description: 'Average goals, home win rate, total matches, etc. for a competition or list of competitions.',
      inputSchema: {
        competition: competitionSchema
      }
    },
    args => Promise.resolve(jsonResult(goalsStats(snap, args.competition)))
  );

  server.registerTool(
    'brazilian_soccer.biggest_wins',
    {
      title: 'Biggest wins',
      description: 'Returns the largest margin of victory in the dataset, optionally filtered by competition/season.',
      inputSchema: {
        competition: competitionSchema,
        season: seasonSchema,
        limit: z.number().int().min(1).max(100).optional()
      }
    },
    args => Promise.resolve(jsonResult(biggestWins(snap, { competition: args.competition ?? 'all', season: args.season, limit: args.limit ?? 10 })))
  );

  server.registerTool(
    'brazilian_soccer.best_home_record',
    {
      title: 'Best home records',
      description: 'Teams with the highest home win rate (with a minimum number of home matches).',
      inputSchema: {
        minMatches: z.number().int().min(1).max(500).optional(),
        limit: z.number().int().min(1).max(50).optional()
      }
    },
    args => Promise.resolve(jsonResult(bestHomeRecord(snap, args.limit ?? 5, args.minMatches ?? 10)))
  );

  server.registerTool(
    'brazilian_soccer.last_match',
    {
      title: 'Last match between two teams',
      description: 'Returns the most recent match between two teams.',
      inputSchema: {
        team1: z.string(),
        team2: z.string()
      }
    },
    args => Promise.resolve(jsonResult(mostRecentMatch(snap, args.team1, args.team2) ?? null))
  );

  return server;
}

async function main(): Promise<void> {
  const snap = loadDataset();
  const server = buildServer(snap);
  const transport = new StdioServerTransport();
  await server.connect(transport);
  // Surface a friendly banner on stderr so process supervisors see the server
  // boot; stdout is reserved for JSON-RPC traffic.
  process.stderr.write(`brazilian-soccer-mcp ready: ${snap.matches.length} matches, ${snap.players.length} players, ${snap.teams.length} teams\n`);
}

main().catch(err => {
  process.stderr.write(`fatal: ${err && (err as Error).stack ? (err as Error).stack : String(err)}\n`);
  process.exit(1);
});
