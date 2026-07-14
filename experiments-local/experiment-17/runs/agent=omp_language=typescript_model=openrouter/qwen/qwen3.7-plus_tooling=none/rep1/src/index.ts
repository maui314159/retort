#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { DataManager } from './data-loader.js';
import path from 'path';
import { fileURLToPath } from 'url';

const dataDir = process.env.DATA_DIR || path.join(process.cwd(), 'data', 'kaggle');

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

const dataManager = new DataManager(dataDir);

type SearchMatchesArgs = {
  team?: string;
  team1?: string;
  team2?: string;
  competition?: string;
  season?: string;
};

type GetTeamStatsArgs = {
  team: string;
  season?: string;
  competition?: string;
};

type SearchPlayersArgs = {
  name?: string;
  nationality?: string;
  club?: string;
  minOverall?: string | number;
};

type GetHeadToHeadArgs = {
  team1: string;
  team2: string;
  season?: string;
  competition?: string;
};

type GetCompetitionStandingsArgs = {
  competition: string;
  season: string;
};

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'search_matches',
        description: 'Search for soccer matches by team, competition, or season.',
        inputSchema: {
          type: 'object',
          properties: {
            team: { type: 'string', description: 'Name of the team (e.g., "Flamengo")' },
            team1: { type: 'string', description: 'First team for head-to-head or specific match search' },
            team2: { type: 'string', description: 'Second team for head-to-head or specific match search' },
            competition: { type: 'string', description: 'Competition name (e.g., "Brasileirao", "Copa do Brasil", "Libertadores")' },
            season: { type: 'string', description: 'Season year (e.g., "2023")' },
          },
        },
      },
      {
        name: 'get_team_stats',
        description: 'Get win/loss/draw statistics and goals for a specific team.',
        inputSchema: {
          type: 'object',
          properties: {
            team: { type: 'string', description: 'Name of the team' },
            season: { type: 'string', description: 'Optional season year' },
            competition: { type: 'string', description: 'Optional competition name' },
          },
          required: ['team'],
        },
      },
      {
        name: 'search_players',
        description: 'Search for players by name, nationality, club, or minimum overall rating.',
        inputSchema: {
          type: 'object',
          properties: {
            name: { type: 'string', description: 'Player name' },
            nationality: { type: 'string', description: 'Player nationality (e.g., "Brazil")' },
            club: { type: 'string', description: 'Club name' },
            minOverall: { type: 'number', description: 'Minimum overall rating' },
          },
        },
      },
      {
        name: 'get_head_to_head',
        description: 'Get head-to-head statistics and recent matches between two teams.',
        inputSchema: {
          type: 'object',
          properties: {
            team1: { type: 'string', description: 'First team name' },
            team2: { type: 'string', description: 'Second team name' },
            season: { type: 'string', description: 'Optional season year' },
            competition: { type: 'string', description: 'Optional competition name' },
          },
          required: ['team1', 'team2'],
        },
      },
      {
        name: 'get_competition_standings',
        description: 'Get calculated standings for a specific competition and season.',
        inputSchema: {
          type: 'object',
          properties: {
            competition: { type: 'string', description: 'Competition name (e.g., "Brasileirao")' },
            season: { type: 'string', description: 'Season year (e.g., "2019")' },
          },
          required: ['competition', 'season'],
        },
      },
    ],
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    if (name === 'search_matches') {
      const parsedArgs = args as unknown as SearchMatchesArgs;
      const results = dataManager.searchMatches(parsedArgs);
      return {
        content: [{ type: 'text', text: JSON.stringify(results.slice(0, 50), null, 2) }],
      };
    }

    if (name === 'get_team_stats') {
      const parsedArgs = args as unknown as GetTeamStatsArgs;
      const stats = dataManager.getTeamStats(parsedArgs.team, parsedArgs.season, parsedArgs.competition);
      return {
        content: [{ type: 'text', text: JSON.stringify(stats, null, 2) }],
      };
    }
    if (name === 'search_players') {
      const parsedArgs = args as unknown as SearchPlayersArgs;
      const searchParams: { name?: string; nationality?: string; club?: string; minOverall?: number } = {};
      if (parsedArgs.name) searchParams.name = parsedArgs.name;
      if (parsedArgs.nationality) searchParams.nationality = parsedArgs.nationality;
      if (parsedArgs.club) searchParams.club = parsedArgs.club;
      if (parsedArgs.minOverall !== undefined) {
        searchParams.minOverall = typeof parsedArgs.minOverall === 'string' ? parseFloat(parsedArgs.minOverall) : parsedArgs.minOverall;
      }
      const results = dataManager.searchPlayers(searchParams);
      return {
        content: [{ type: 'text', text: JSON.stringify(results, null, 2) }],
      };
    }

    if (name === 'get_head_to_head') {
      const parsedArgs = args as unknown as GetHeadToHeadArgs;
      const h2h = dataManager.getHeadToHead(parsedArgs.team1, parsedArgs.team2, parsedArgs.season, parsedArgs.competition);
      return {
        content: [{ type: 'text', text: JSON.stringify(h2h, null, 2) }],
      };
    }

    if (name === 'get_competition_standings') {
      const parsedArgs = args as unknown as GetCompetitionStandingsArgs;
      const standings = dataManager.getCompetitionStandings(parsedArgs.competition, parsedArgs.season);
      return {
        content: [{ type: 'text', text: JSON.stringify(standings.slice(0, 20), null, 2) }],
      };
    }

    throw new Error(`Unknown tool: ${name}`);
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return {
      content: [{ type: 'text', text: `Error: ${errorMessage}` }],
      isError: true,
    };
  }
});

async function main() {
  console.error(`Loading data from ${dataDir}...`);
  await dataManager.load();
  console.error('Data loaded successfully.');

  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Brazilian Soccer MCP Server running on stdio');
}

main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
