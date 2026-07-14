/*
 * Brazilian Soccer MCP Server - Server factory
 *
 * Builds and configures the MCP Server instance, exposing the tool surface
 * defined in the specification. This module is separate from the stdio entry
 * point so that the server can be instantiated directly in tests.
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema
} from '@modelcontextprotocol/sdk/types.js';
import { QueryEngine } from './engine.js';
import {
  formatMatches,
  formatHeadToHead,
  formatTeamRecord,
  formatStandings,
  formatPlayers,
  formatBiggestWins,
  formatAverageGoals,
  formatHomeWinRate,
  formatPlayerClubsSummary
} from './formatter.js';

export function createServer(engine: QueryEngine): Server {
  const server = new Server(
    {
      name: 'brazilian-soccer-mcp-server',
      version: '1.0.0'
    },
    {
      capabilities: {
        tools: {}
      }
    }
  );

  server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: [
      {
        name: 'search_matches',
        description:
          'Search matches by team(s), competition, season, date range, round, or stage.',
        inputSchema: {
          type: 'object',
          properties: {
            team: { type: 'string', description: 'Team name (home or away)' },
            homeTeam: { type: 'string' },
            awayTeam: { type: 'string' },
            teamA: { type: 'string', description: 'First team for head-to-head search' },
            teamB: { type: 'string', description: 'Second team for head-to-head search' },
            competition: { type: 'string' },
            season: { type: 'number' },
            fromDate: { type: 'string', format: 'date' },
            toDate: { type: 'string', format: 'date' },
            round: { type: 'string' },
            stage: { type: 'string' }
          }
        }
      },
      {
        name: 'get_team_record',
        description: 'Get win/draw/loss/goals record for a team, optionally filtered.',
        inputSchema: {
          type: 'object',
          required: ['team'],
          properties: {
            team: { type: 'string' },
            competition: { type: 'string' },
            season: { type: 'number' },
            side: { type: 'string', enum: ['home', 'away', 'both'] }
          }
        }
      },
      {
        name: 'get_head_to_head',
        description: 'Get historical results between two teams.',
        inputSchema: {
          type: 'object',
          required: ['teamA', 'teamB'],
          properties: {
            teamA: { type: 'string' },
            teamB: { type: 'string' },
            competition: { type: 'string' },
            season: { type: 'number' }
          }
        }
      },
      {
        name: 'search_players',
        description:
          'Search FIFA player data by name, nationality, club, position, or minimum overall rating.',
        inputSchema: {
          type: 'object',
          properties: {
            name: { type: 'string' },
            nationality: { type: 'string' },
            club: { type: 'string' },
            position: { type: 'string' },
            minOverall: { type: 'number' },
            limit: { type: 'number' }
          }
        }
      },
      {
        name: 'get_standings',
        description: 'Calculate league standings for a competition and season.',
        inputSchema: {
          type: 'object',
          required: ['competition', 'season'],
          properties: {
            competition: { type: 'string' },
            season: { type: 'number' }
          }
        }
      },
      {
        name: 'get_statistics',
        description:
          'Compute statistical summaries such as average goals, home win rate, biggest wins, or away records.',
        inputSchema: {
          type: 'object',
          required: ['type'],
          properties: {
            type: {
              type: 'string',
              enum: [
                'average_goals',
                'home_win_rate',
                'biggest_wins',
                'best_away_record',
                'top_scorer_teams'
              ]
            },
            competition: { type: 'string' },
            season: { type: 'number' },
            limit: { type: 'number' }
          }
        }
      },
      {
        name: 'list_metadata',
        description: 'List competitions or seasons available in the loaded dataset.',
        inputSchema: {
          type: 'object',
          required: ['type'],
          properties: {
            type: { type: 'string', enum: ['competitions', 'seasons'] },
            team: { type: 'string' },
            competition: { type: 'string' }
          }
        }
      },
      {
        name: 'player_clubs_summary',
        description:
          'Summarise how many players and their average overall rating per club.',
        inputSchema: {
          type: 'object',
          properties: {
            club: { type: 'string' }
          }
        }
      }
    ]
  }));

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const args = (request.params.arguments ?? {}) as Record<string, unknown>;

    try {
      let text = '';

      switch (request.params.name) {
        case 'search_matches': {
          const matches = engine.findMatches({
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
            stage: args.stage as string | undefined
          });
          text = args.teamA && args.teamB
            ? formatHeadToHead(engine.getHeadToHead(args.teamA as string, args.teamB as string))
            : formatMatches(matches);
          break;
        }

        case 'get_team_record': {
          const record = engine.getTeamRecord(
            args.team as string,
            {
              competition: args.competition as string | undefined,
              season: args.season as number | undefined
            },
            (args.side as 'home' | 'away' | 'both') ?? 'both'
          );
          text = formatTeamRecord(
            record,
            `${record.team} ${args.side ? args.side + ' ' : ''}record`
          );
          break;
        }

        case 'get_head_to_head': {
          const h2h = engine.getHeadToHead(
            args.teamA as string,
            args.teamB as string,
            {
              competition: args.competition as string | undefined,
              season: args.season as number | undefined
            }
          );
          text = formatHeadToHead(h2h);
          break;
        }

        case 'search_players': {
          const players = engine.findPlayers({
            name: args.name as string | undefined,
            nationality: args.nationality as string | undefined,
            club: args.club as string | undefined,
            position: args.position as string | undefined,
            minOverall: args.minOverall as number | undefined,
            limit: args.limit as number | undefined
          });
          const label = args.nationality
            ? `${args.nationality} players`
            : args.club
              ? `Players at ${args.club}`
              : args.position
                ? `${args.position} players`
                : 'Players';
          text = formatPlayers(players, label);
          break;
        }

        case 'get_standings': {
          const standings = engine.calculateStandings(
            args.competition as string,
            args.season as number
          );
          text = formatStandings(standings, `${args.season} ${args.competition}`);
          break;
        }

        case 'get_statistics': {
          const type = args.type as string;
          const filters = {
            competition: args.competition as string | undefined,
            season: args.season as number | undefined
          };
          switch (type) {
            case 'average_goals':
              text = formatAverageGoals(engine.averageGoals(filters));
              break;
            case 'home_win_rate':
              text = formatHomeWinRate(engine.homeWinRate(filters));
              break;
            case 'biggest_wins': {
              const winsLimit = args.limit as number | undefined;
              const wins = engine.biggestWins(filters, winsLimit);
              text = formatBiggestWins(wins);
              break;
            }
            case 'best_away_record': {
              const records = engine.bestAwayRecord(filters);
              const bestLimit = args.limit as number | undefined;
              text = records
                .slice(0, bestLimit ?? 10)
                .map((r) => formatTeamRecord(r))
                .join('\n\n');
              break;
            }
            case 'top_scorer_teams': {
              const topLimit = args.limit as number | undefined;
              const records = engine.topScorerTeams(filters, topLimit);
              text = records.map((r) => `- ${r.team}: ${r.goalsFor} goals`).join('\n');
              break;
            }
            default:
              text = `Unsupported statistics type: ${type}`;
          }
          break;
        }

        case 'list_metadata': {
          const type = args.type as string;
          if (type === 'competitions') {
            const list = engine.listCompetitions(args.team as string | undefined);
            text = list.join('\n');
          } else if (type === 'seasons') {
            const list = engine.listSeasons(args.competition as string | undefined);
            text = list.map(String).join('\n');
          } else {
            text = 'Unsupported metadata type.';
          }
          break;
        }

        case 'player_clubs_summary': {
          const summary = engine.playerClubsSummary(args.club as string | undefined);
          text = formatPlayerClubsSummary(
            summary,
            args.club ? `Clubs matching "${args.club}"` : 'Player clubs'
          );
          break;
        }

        default:
          text = `Unknown tool: ${request.params.name}`;
      }

      return {
        content: [
          {
            type: 'text',
            text
          }
        ]
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      return {
        content: [
          {
            type: 'text',
            text: `Error: ${message}`
          }
        ],
        isError: true
      };
    }
  });

  return server;
}
