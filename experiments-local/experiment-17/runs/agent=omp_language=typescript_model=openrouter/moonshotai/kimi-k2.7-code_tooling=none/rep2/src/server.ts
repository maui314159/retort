/**
 * Brazilian Soccer MCP Server
 * MCP server exposing tools for querying Brazilian soccer data.
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  CallToolResult,
  ListToolsRequestSchema,
  Tool,
} from '@modelcontextprotocol/sdk/types.js';
import { loadRepository, SoccerRepository } from './data.js';
import {
  bestAwayRecord,
  competitionStandings,
  competitionStats,
  findMatches,
  findPlayers,
  formatCompetitionStats,
  formatHeadToHead,
  formatMatchList,
  formatPlayers,
  formatStandings,
  formatTeamStats,
  headToHead,
  teamStatistics,
} from './queries.js';

export const TOOLS: Tool[] = [
  {
    name: 'search_matches',
    description:
      'Search Brazilian soccer matches by team, competition, season, date range, or round.',
    inputSchema: {
      type: 'object',
      properties: {
        team: { type: 'string', description: 'Team name (home or away)' },
        homeTeam: { type: 'string', description: 'Home team name' },
        awayTeam: { type: 'string', description: 'Away team name' },
        teamA: { type: 'string', description: 'First team for head-to-head search' },
        teamB: { type: 'string', description: 'Second team for head-to-head search' },
        competition: {
          type: 'string',
          description: 'Competition name, e.g. Brasileirão, Copa do Brasil, Copa Libertadores',
        },
        season: { type: 'number', description: 'Season year' },
        fromDate: { type: 'string', description: 'Start date (YYYY-MM-DD)' },
        toDate: { type: 'string', description: 'End date (YYYY-MM-DD)' },
        round: { type: 'string', description: 'Round/stage identifier' },
        limit: { type: 'number', description: 'Maximum number of matches to return' },
      },
      additionalProperties: false,
    },
  },
  {
    name: 'team_statistics',
    description:
      'Calculate win/loss/draw, goals, and win rate for a team in a season and/or competition.',
    inputSchema: {
      type: 'object',
      properties: {
        team: { type: 'string', description: 'Team name' },
        season: { type: 'number', description: 'Season year' },
        competition: { type: 'string', description: 'Competition name' },
        venue: {
          type: 'string',
          enum: ['home', 'away'],
          description: 'Filter to home or away matches',
        },
      },
      required: ['team'],
      additionalProperties: false,
    },
  },
  {
    name: 'head_to_head',
    description:
      'Compare two teams head-to-head including all matches and aggregate record.',
    inputSchema: {
      type: 'object',
      properties: {
        teamA: { type: 'string', description: 'First team' },
        teamB: { type: 'string', description: 'Second team' },
      },
      required: ['teamA', 'teamB'],
      additionalProperties: false,
    },
  },
  {
    name: 'search_players',
    description:
      'Search FIFA player data by name, nationality, club, or position. Results are sorted by overall rating.',
    inputSchema: {
      type: 'object',
      properties: {
        name: { type: 'string', description: 'Player name' },
        nationality: { type: 'string', description: 'Player nationality' },
        club: { type: 'string', description: 'Club name' },
        position: { type: 'string', description: 'Playing position' },
        minOverall: { type: 'number', description: 'Minimum overall rating' },
        limit: { type: 'number', description: 'Maximum number of players to return' },
      },
      additionalProperties: false,
    },
  },
  {
    name: 'competition_standings',
    description:
      'Calculate final league standings for a competition and season from match results.',
    inputSchema: {
      type: 'object',
      properties: {
        competition: { type: 'string', description: 'Competition name' },
        season: { type: 'number', description: 'Season year' },
      },
      required: ['competition', 'season'],
      additionalProperties: false,
    },
  },
  {
    name: 'competition_statistics',
    description:
      'Compute aggregated competition statistics: average goals, home/away/draw win rates, and biggest wins.',
    inputSchema: {
      type: 'object',
      properties: {
        competition: {
          type: 'string',
          description: 'Competition name (omit for all competitions)',
        },
      },
      additionalProperties: false,
    },
  },
  {
    name: 'best_away_record',
    description:
      'Return teams with the best away records, optionally filtered by competition.',
    inputSchema: {
      type: 'object',
      properties: {
        competition: {
          type: 'string',
          description: 'Competition name (omit for all competitions)',
        },
      },
      additionalProperties: false,
    },
  },
];

export function createToolRunner(
  repository: SoccerRepository
): (name: string, args: Record<string, unknown>) => Promise<CallToolResult> {
  return async (name, args) => {
    args ??= {};

    switch (name) {
      case 'search_matches': {
        const matches = findMatches(repository, {
          team: args.team as string | undefined,
          homeTeam: args.homeTeam as string | undefined,
          awayTeam: args.awayTeam as string | undefined,
          teamA: args.teamA as string | undefined,
          teamB: args.teamB as string | undefined,
          competition: args.competition as string | undefined,
          season: args.season as number | undefined,
          fromDate: args.fromDate as string | undefined,
          toDate: args.toDate as string | undefined,
          round: args.round as string | undefined,
          limit: args.limit as number | undefined,
        });
        return {
          content: [{ type: 'text', text: formatMatchList(matches) }],
        };
      }

      case 'team_statistics': {
        const stats = teamStatistics(repository, args.team as string, {
          season: args.season as number | undefined,
          competition: args.competition as string | undefined,
          venue: args.venue as 'home' | 'away' | undefined,
        });
        return {
          content: [{ type: 'text', text: formatTeamStats(stats) }],
        };
      }

      case 'head_to_head': {
        const result = headToHead(
          repository,
          args.teamA as string,
          args.teamB as string
        );
        return {
          content: [{ type: 'text', text: formatHeadToHead(result) }],
        };
      }

      case 'search_players': {
        const all = findPlayers(repository, {
          name: args.name as string | undefined,
          nationality: args.nationality as string | undefined,
          club: args.club as string | undefined,
          position: args.position as string | undefined,
          minOverall: args.minOverall as number | undefined,
        });
        const limit = args.limit as number | undefined;
        const players =
          limit !== undefined && all.length > limit ? all.slice(0, limit) : all;
        return {
          content: [{ type: 'text', text: formatPlayers(players, all.length) }],
        };
      }

      case 'competition_standings': {
        const rows = competitionStandings(
          repository,
          args.competition as string,
          args.season as number
        );
        return {
          content: [
            {
              type: 'text',
              text: formatStandings(
                rows,
                args.season as number,
                args.competition as string
              ),
            },
          ],
        };
      }

      case 'competition_statistics': {
        const stats = competitionStats(
          repository,
          args.competition as string | undefined
        );
        return {
          content: [
            {
              type: 'text',
              text: formatCompetitionStats(stats, args.competition as string | undefined),
            },
          ],
        };
      }

      case 'best_away_record': {
        const records = bestAwayRecord(
          repository,
          args.competition as string | undefined
        );
        const lines = records.map(
          (r) =>
            `- ${r.team}: ${r.wins}W ${r.draws}D ${r.losses}L (${r.winRate}% win rate, ${r.goalsFor}-${r.goalsAgainst})`
        );
        return {
          content: [
            {
              type: 'text',
              text:
                'Best away records (min. 5 away matches):\n' + lines.join('\n'),
            },
          ],
        };
      }

      default:
        return {
          content: [{ type: 'text', text: `Error: Unknown tool: ${name}` }],
          isError: true,
        };
    }
  };
}

export async function createServer(repo?: SoccerRepository): Promise<Server> {
  const repository = repo ?? (await loadRepository());
  const runTool = createToolRunner(repository);

  const server = new Server(
    {
      name: 'brazilian-soccer-mcp-server',
      version: '1.0.0',
    },
    {
      capabilities: {
        tools: {},
      },
    }
  );

  server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: TOOLS,
  }));

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    return runTool(name, args ?? {});
  });

  return server;
}

export async function startServer(): Promise<void> {
  const server = await createServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
}
