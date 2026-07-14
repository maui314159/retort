/**
 * Brazilian Soccer MCP Server
 *
 * Exposes tools for querying Brazilian soccer data:
 *   - search_matches: find matches by team, competition, season, date range
 *   - get_head_to_head: compare two teams head-to-head
 *   - get_team_stats: win/loss/draw record for a team
 *   - search_players: find players by name, nationality, club, position, rating
 *   - get_competition_standings: league table for a competition season
 *   - get_biggest_wins: biggest victories in a competition
 *   - get_competition_overview: aggregate statistics for a competition
 *
 * Data loaded from data/kaggle/ on first tool call (lazy, cached).
 * Server communicates via stdio (MCP standard).
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { loadData } from './data/loader.js';
import {
  searchMatches,
  getHeadToHead,
  formatSearchResults,
  formatHeadToHead,
} from './tools/matches.js';
import {
  getTeamRecord,
  formatTeamStats,
  getTopGoalTeams,
} from './tools/teams.js';
import {
  searchPlayers,
  formatPlayerResults,
} from './tools/players.js';
import {
  getStandings,
  formatStandings,
  getAvailableSeasons,
} from './tools/competitions.js';
import {
  computeStats,
  getBiggestWins,
  formatStats,
  formatBiggestWins,
} from './tools/statistics.js';

const server = new McpServer({
  name: 'brazilian-soccer-mcp',
  version: '1.0.0',
});

// ─── search_matches ────────────────────────────────────────────────────────────

server.tool(
  'search_matches',
  'Search for matches by team, competition, season, or date range. Use team for single-team queries, team1+team2 for head-to-head matchups.',
  {
    team: z.string().optional().describe('Team name (searches both home and away). E.g. "Flamengo", "Palmeiras"'),
    team1: z.string().optional().describe('First team for head-to-head search (pair with team2)'),
    team2: z.string().optional().describe('Second team for head-to-head search (pair with team1)'),
    competition: z.string().optional().describe('Competition filter: "brasileirao", "copa_do_brasil", "libertadores", or tournament name'),
    season: z.number().int().optional().describe('Season year, e.g. 2023'),
    dateFrom: z.string().optional().describe('Start date filter (YYYY-MM-DD)'),
    dateTo: z.string().optional().describe('End date filter (YYYY-MM-DD)'),
    limit: z.number().int().min(1).max(100).optional().describe('Max results (default 20)'),
  },
  async (params) => {
    const { matches } = loadData();
    const all = searchMatches(matches, { ...params, limit: undefined });
    const results = searchMatches(matches, params);
    return {
      content: [{ type: 'text', text: formatSearchResults(results, all.length, params) }],
    };
  }
);

// ─── get_head_to_head ──────────────────────────────────────────────────────────

server.tool(
  'get_head_to_head',
  'Get head-to-head record and match history between two teams.',
  {
    team1: z.string().describe('First team name'),
    team2: z.string().describe('Second team name'),
    competition: z.string().optional().describe('Filter by competition'),
    season: z.number().int().optional().describe('Filter by season year'),
  },
  async ({ team1, team2, competition, season }) => {
    const { matches } = loadData();
    const result = getHeadToHead(matches, team1, team2, competition, season);
    return {
      content: [{ type: 'text', text: formatHeadToHead(result, team1, team2) }],
    };
  }
);

// ─── get_team_stats ────────────────────────────────────────────────────────────

server.tool(
  'get_team_stats',
  'Get win/loss/draw statistics for a team, optionally filtered by competition, season, or venue (home/away).',
  {
    team: z.string().describe('Team name'),
    competition: z.string().optional().describe('Competition filter'),
    season: z.number().int().optional().describe('Season year'),
    homeOnly: z.boolean().optional().describe('Only count home matches'),
    awayOnly: z.boolean().optional().describe('Only count away matches'),
  },
  async ({ team, competition, season, homeOnly, awayOnly }) => {
    const { matches } = loadData();
    const record = getTeamRecord(matches, team, competition, season, homeOnly, awayOnly);
    return {
      content: [{ type: 'text', text: formatTeamStats(record, competition, season) }],
    };
  }
);

// ─── search_players ────────────────────────────────────────────────────────────

server.tool(
  'search_players',
  'Search FIFA player database by name, nationality, club, position, or overall rating.',
  {
    name: z.string().optional().describe('Player name (partial match), e.g. "Neymar"'),
    nationality: z.string().optional().describe('Nationality filter, e.g. "Brazil"'),
    club: z.string().optional().describe('Club filter, e.g. "Flamengo"'),
    position: z.string().optional().describe('Position filter, e.g. "ST", "GK", "LW"'),
    minOverall: z.number().int().min(0).max(99).optional().describe('Minimum overall rating'),
    maxOverall: z.number().int().min(0).max(99).optional().describe('Maximum overall rating'),
    limit: z.number().int().min(1).max(100).optional().describe('Max results (default 20)'),
  },
  async (params) => {
    const { players } = loadData();
    const allMatching = searchPlayers(players, { ...params, limit: undefined });
    const results = searchPlayers(players, params);
    return {
      content: [{ type: 'text', text: formatPlayerResults(results, allMatching.length, params) }],
    };
  }
);

// ─── get_competition_standings ─────────────────────────────────────────────────

server.tool(
  'get_competition_standings',
  'Calculate league standings for a competition season from match results.',
  {
    competition: z.string().describe('Competition name: "brasileirao", "copa_do_brasil", "libertadores"'),
    season: z.number().int().describe('Season year, e.g. 2019'),
  },
  async ({ competition, season }) => {
    const { matches } = loadData();
    const standings = getStandings(matches, competition, season);
    return {
      content: [{ type: 'text', text: formatStandings(standings, competition, season) }],
    };
  }
);

// ─── get_biggest_wins ──────────────────────────────────────────────────────────

server.tool(
  'get_biggest_wins',
  'Find the biggest victories (by goal difference) in the dataset.',
  {
    competition: z.string().optional().describe('Filter by competition'),
    limit: z.number().int().min(1).max(50).optional().describe('Number of results (default 10)'),
  },
  async ({ competition, limit }) => {
    const { matches } = loadData();
    const wins = getBiggestWins(matches, competition, limit ?? 10);
    return {
      content: [{ type: 'text', text: formatBiggestWins(wins, competition) }],
    };
  }
);

// ─── get_competition_overview ──────────────────────────────────────────────────

server.tool(
  'get_competition_overview',
  'Get aggregate statistics for a competition: avg goals/match, home win rate, total matches.',
  {
    competition: z.string().optional().describe('Competition filter'),
    season: z.number().int().optional().describe('Season year filter'),
  },
  async ({ competition, season }) => {
    const { matches } = loadData();
    const stats = computeStats(matches, competition, season);
    return {
      content: [{ type: 'text', text: formatStats(stats, competition, season) }],
    };
  }
);

// ─── get_top_scoring_teams ─────────────────────────────────────────────────────

server.tool(
  'get_top_scoring_teams',
  'Find the teams with the most goals scored in a competition or season.',
  {
    competition: z.string().optional().describe('Competition filter'),
    season: z.number().int().optional().describe('Season year filter'),
    limit: z.number().int().min(1).max(50).optional().describe('Number of results (default 10)'),
  },
  async ({ competition, season, limit }) => {
    const { matches } = loadData();
    const top = getTopGoalTeams(matches, competition, season, limit ?? 10);
    if (top.length === 0) return { content: [{ type: 'text', text: 'No data found.' }] };

    const ctx = [
      competition ? competition.replace(/_/g, ' ') : 'all competitions',
      season ? String(season) : '',
    ].filter(Boolean).join(' ');

    const lines = [`Top scoring teams — ${ctx}:`, ''];
    for (let i = 0; i < top.length; i++) {
      const t = top[i];
      const avg = (t.goals / t.matches).toFixed(2);
      lines.push(`${i + 1}. ${t.team}: ${t.goals} goals in ${t.matches} matches (${avg} per match)`);
    }
    return { content: [{ type: 'text', text: lines.join('\n') }] };
  }
);

// ─── get_available_seasons ─────────────────────────────────────────────────────

server.tool(
  'get_available_seasons',
  'List all available seasons in the dataset for a given competition.',
  {
    competition: z.string().optional().describe('Competition filter'),
  },
  async ({ competition }) => {
    const { matches } = loadData();
    const seasons = getAvailableSeasons(matches, competition);
    const ctx = competition ? competition.replace(/_/g, ' ') : 'all competitions';
    const text = seasons.length > 0
      ? `Available seasons for ${ctx}: ${seasons.join(', ')}`
      : `No season data found for ${ctx}.`;
    return { content: [{ type: 'text', text }] };
  }
);

// ─── Run server ────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  process.stderr.write(`Fatal: ${err}\n`);
  process.exit(1);
});
