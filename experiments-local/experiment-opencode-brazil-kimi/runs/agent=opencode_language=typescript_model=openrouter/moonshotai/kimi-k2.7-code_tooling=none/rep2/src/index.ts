#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  type Tool,
} from '@modelcontextprotocol/sdk/types.js';
import { loadData } from './loader.js';
import { createQueryEngine } from './engine.js';
import { normalizeCompetition, normalizeTeamName } from './normalize.js';
import {
  formatMatches,
  formatTeamStats,
  formatHeadToHead,
  formatStandings,
  formatPlayers,
  formatStatsSummary,
} from './format.js';

const tools: Tool[] = [
  {
    name: 'search_matches',
    description: 'Find matches by team, date range, competition, season, and round',
    inputSchema: {
      type: 'object',
      properties: {
        team: { type: 'string', description: 'Team name (matches home or away)' },
        team1: { type: 'string', description: 'First team for head-to-head search' },
        team2: { type: 'string', description: 'Second team for head-to-head search' },
        competition: { type: 'string', description: 'Competition name (Brasileirão, Copa do Brasil, Copa Libertadores)' },
        season: { type: 'integer', description: 'Season year' },
        from: { type: 'string', description: 'Start date (YYYY-MM-DD)' },
        to: { type: 'string', description: 'End date (YYYY-MM-DD)' },
        round: { type: 'string', description: 'Round/stage filter' },
        limit: { type: 'integer', description: 'Maximum number of results' },
      },
    },
  },
  {
    name: 'team_stats',
    description: 'Get win/loss/draw statistics and goals for a team',
    inputSchema: {
      type: 'object',
      properties: {
        team: { type: 'string', description: 'Team name' },
        competition: { type: 'string', description: 'Filter by competition' },
        season: { type: 'integer', description: 'Filter by season year' },
      },
      required: ['team'],
    },
  },
  {
    name: 'head_to_head',
    description: 'Compare two teams head-to-head',
    inputSchema: {
      type: 'object',
      properties: {
        team1: { type: 'string', description: 'First team' },
        team2: { type: 'string', description: 'Second team' },
        competition: { type: 'string', description: 'Filter by competition' },
        season: { type: 'integer', description: 'Filter by season year' },
      },
      required: ['team1', 'team2'],
    },
  },
  {
    name: 'competition_standings',
    description: 'Calculate league standings for a competition and season',
    inputSchema: {
      type: 'object',
      properties: {
        competition: { type: 'string', description: 'Competition name' },
        season: { type: 'integer', description: 'Season year' },
      },
      required: ['competition', 'season'],
    },
  },
  {
    name: 'search_players',
    description: 'Search FIFA player data by name, nationality, club, and position',
    inputSchema: {
      type: 'object',
      properties: {
        name: { type: 'string', description: 'Player name (partial match)' },
        nationality: { type: 'string', description: 'Nationality (e.g., Brazil)' },
        club: { type: 'string', description: 'Club name' },
        position: { type: 'string', description: 'Position code like FW, LW, GK' },
        minOverall: { type: 'integer', description: 'Minimum overall rating' },
        limit: { type: 'integer', description: 'Maximum number of results' },
      },
    },
  },
  {
    name: 'competition_stats',
    description: 'Calculate aggregated statistics for a competition or query',
    inputSchema: {
      type: 'object',
      properties: {
        competition: { type: 'string', description: 'Competition name' },
        season: { type: 'integer', description: 'Season year' },
        team: { type: 'string', description: 'Team name filter' },
      },
    },
  },
];

export async function main() {
  const dataDir = process.env.DATA_DIR;
  const data = await loadData(dataDir);
  const engine = createQueryEngine(data);

  const server = new Server(
    {
      name: 'brazilian-soccer-mcp',
      version: '1.0.0',
    },
    {
      capabilities: {
        tools: {},
      },
    }
  );

  server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools }));

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const args = (request.params.arguments as Record<string, unknown>) ?? {};
    const name = request.params.name;

    switch (name) {
      case 'search_matches': {
        const limit = typeof args.limit === 'number' ? args.limit : undefined;
        const matches = engine.findMatches({
          team: typeof args.team === 'string' ? args.team : undefined,
          team1: typeof args.team1 === 'string' ? args.team1 : undefined,
          team2: typeof args.team2 === 'string' ? args.team2 : undefined,
          competition: typeof args.competition === 'string' ? args.competition : undefined,
          season: typeof args.season === 'number' ? args.season : undefined,
          from: typeof args.from === 'string' ? args.from : undefined,
          to: typeof args.to === 'string' ? args.to : undefined,
          round: typeof args.round === 'string' ? args.round : undefined,
          limit,
        });
        const title = args.team1 && args.team2
          ? `${args.team1} vs ${args.team2}`
          : args.team
          ? `Matches for ${args.team}`
          : 'Matches';
        return { content: [{ type: 'text', text: formatMatches(matches, title) }] };
      }
      case 'team_stats': {
        const team = typeof args.team === 'string' ? args.team : '';
        const stats = engine.getTeamStats(team, {
          competition: typeof args.competition === 'string' ? args.competition : undefined,
          season: typeof args.season === 'number' ? args.season : undefined,
        });
        return { content: [{ type: 'text', text: formatTeamStats(stats) }] };
      }
      case 'head_to_head': {
        const team1 = typeof args.team1 === 'string' ? args.team1 : '';
        const team2 = typeof args.team2 === 'string' ? args.team2 : '';
        const result = engine.getHeadToHead(team1, team2, {
          competition: typeof args.competition === 'string' ? args.competition : undefined,
          season: typeof args.season === 'number' ? args.season : undefined,
        });
        return { content: [{ type: 'text', text: formatHeadToHead(team1, team2, result) }] };
      }
      case 'competition_standings': {
        const comp = normalizeCompetition(typeof args.competition === 'string' ? args.competition : '');
        const season = typeof args.season === 'number' ? args.season : 0;
        const standings = engine.getStandings(comp, season);
        return { content: [{ type: 'text', text: formatStandings(standings, comp, season) }] };
      }
      case 'search_players': {
        const players = engine.searchPlayers({
          name: typeof args.name === 'string' ? args.name : undefined,
          nationality: typeof args.nationality === 'string' ? args.nationality : undefined,
          club: typeof args.club === 'string' ? normalizeTeamName(args.club) : undefined,
          position: typeof args.position === 'string' ? args.position : undefined,
          minOverall: typeof args.minOverall === 'number' ? args.minOverall : undefined,
          limit: typeof args.limit === 'number' ? args.limit : undefined,
        });
        const title = args.nationality
          ? `Top-rated ${args.nationality} players`
          : args.club
          ? `Players at ${args.club}`
          : 'Players';
        return { content: [{ type: 'text', text: formatPlayers(players, title) }] };
      }
      case 'competition_stats': {
        const summary = engine.getStatsSummary({
          competition: typeof args.competition === 'string' ? args.competition : undefined,
          season: typeof args.season === 'number' ? args.season : undefined,
          team: typeof args.team === 'string' ? args.team : undefined,
        });
        return { content: [{ type: 'text', text: formatStatsSummary(summary) }] };
      }
      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  });

  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  console.error('Fatal error starting server:', err);
  process.exit(1);
});
