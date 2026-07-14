/**
 * Brazilian Soccer MCP Server - Main Entry Point
 * 
 * Implements Model Context Protocol server providing tools for querying
 * Brazilian soccer data including matches, players, teams, and competitions.
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from '@modelcontextprotocol/sdk/types.js';
import { loadAllDatasets } from './csv-loader.js';
import { 
  filterMatches, 
  filterPlayers, 
  calculateTeamStats, 
  calculateHeadToHead, 
  calculateStandings,
  calculateOverallStats,
  formatMatch,
  formatPlayer,
  formatTeamStats,
  QueryFilters
} from './query.js';
import { format, isValid, parseISO } from 'date-fns';

// Load data once at startup
console.error('Loading Brazilian soccer datasets...');
const data = loadAllDatasets();
console.error(`Loaded ${data.matches.length} matches and ${data.players.length} players`);

// Create MCP server
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

// Define MCP tools
const tools: Tool[] = [
  {
    name: 'search_matches',
    description: 'Search for soccer matches by various criteria including teams, date range, season, and competition',
    inputSchema: {
      type: 'object',
      properties: {
        team: {
          type: 'string',
          description: 'Team name (home or away)'
        },
        homeTeam: {
          type: 'string',
          description: 'Home team name'
        },
        awayTeam: {
          type: 'string',
          description: 'Away team name'
        },
        teams: {
          type: 'array',
          items: { type: 'string' },
          description: 'Two teams for head-to-head matches'
        },
        dateFrom: {
          type: 'string',
          description: 'Start date (YYYY-MM-DD format)'
        },
        dateTo: {
          type: 'string',
          description: 'End date (YYYY-MM-DD format)'
        },
        season: {
          type: 'integer',
          description: 'Season year'
        },
        competition: {
          type: 'string',
          description: 'Competition name (Brasileirão, Copa do Brasil, Libertadores, etc.)'
        },
        limit: {
          type: 'integer',
          description: 'Maximum number of results'
        }
      }
    }
  },
  {
    name: 'search_players',
    description: 'Search for players by name, nationality, club, rating, or position',
    inputSchema: {
      type: 'object',
      properties: {
        name: {
          type: 'string',
          description: 'Player name (partial match)'
        },
        nationality: {
          type: 'string',
          description: 'Player nationality (e.g., Brazil)'
        },
        club: {
          type: 'string',
          description: 'Club name (e.g., Flamengo)'
        },
        minRating: {
          type: 'integer',
          description: 'Minimum overall rating'
        },
        maxRating: {
          type: 'integer',
          description: 'Maximum overall rating'
        },
        position: {
          type: 'string',
          description: 'Playing position (e.g., ST, GK, MF)'
        },
        limit: {
          type: 'integer',
          description: 'Maximum number of results'
        }
      }
    }
  },
  {
    name: 'get_team_stats',
    description: 'Get team statistics including wins, losses, draws, goals, and performance',
    inputSchema: {
      type: 'object',
      properties: {
        team: {
          type: 'string',
          description: 'Team name',
          required: true
        },
        season: {
          type: 'integer',
          description: 'Season year (optional)'
        },
        competition: {
          type: 'string',
          description: 'Competition name (optional)'
        }
      }
    }
  },
  {
    name: 'get_head_to_head',
    description: 'Get head-to-head statistics between two teams',
    inputSchema: {
      type: 'object',
      properties: {
        team1: {
          type: 'string',
          description: 'First team name',
          required: true
        },
        team2: {
          type: 'string',
          description: 'Second team name',
          required: true
        }
      }
    }
  },
  {
    name: 'get_competition_standings',
    description: 'Get competition standings calculated from match results',
    inputSchema: {
      type: 'object',
      properties: {
        competition: {
          type: 'string',
          description: 'Competition name (e.g., Brasileirão, Copa Libertadores)',
          required: true
        },
        season: {
          type: 'integer',
          description: 'Season year (optional)'
        }
      }
    }
  },
  {
    name: 'get_overall_stats',
    description: 'Get overall statistics including average goals, win rates, and biggest victories',
    inputSchema: {
      type: 'object',
      properties: {
        competition: {
          type: 'string',
          description: 'Competition name (optional, filter by competition)'
        },
        season: {
          type: 'integer',
          description: 'Season year (optional, filter by season)'
        }
      }
    }
  }
];

// Handle list tools request
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools
}));

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  
  // Validate args
  if (!args || typeof args !== 'object' || Array.isArray(args)) {
    return {
      content: [{ 
        type: 'text', 
        text: 'Error: Invalid arguments format. Arguments must be an object.' 
      }],
      isError: true
    };
  }
  
  const safeArgs = args as Record<string, unknown>;
  
  try {
    switch (name) {
      case 'search_matches': {
        const filters: QueryFilters = {};
        
        if (safeArgs.team && typeof safeArgs.team === 'string') filters.team = safeArgs.team;
        if (safeArgs.homeTeam && typeof safeArgs.homeTeam === 'string') filters.homeTeam = safeArgs.homeTeam;
        if (safeArgs.awayTeam && typeof safeArgs.awayTeam === 'string') filters.awayTeam = safeArgs.awayTeam;
        if (safeArgs.teams && Array.isArray(safeArgs.teams)) filters.teams = safeArgs.teams as string[];
        if (safeArgs.dateFrom && typeof safeArgs.dateFrom === 'string') {
          const date = parseISO(safeArgs.dateFrom);
          if (isValid(date)) filters.dateFrom = date;
        }
        if (safeArgs.dateTo && typeof safeArgs.dateTo === 'string') {
          const date = parseISO(safeArgs.dateTo);
          if (isValid(date)) filters.dateTo = date;
        }
        if (safeArgs.season && typeof safeArgs.season === 'number') filters.season = safeArgs.season;
        if (safeArgs.competition && typeof safeArgs.competition === 'string') filters.competition = safeArgs.competition;
        if (safeArgs.limit && typeof safeArgs.limit === 'number') filters.limit = safeArgs.limit;
        
        const matches = filterMatches(data.matches, filters);
        
        let responseText = '';
        if (matches.length === 0) {
          responseText = 'No matches found matching the criteria.';
        } else {
          responseText = `Found ${matches.length} matches:\n\n`;
          matches.slice(0, 20).forEach((match, i) => {
            responseText += `${i + 1}. ${formatMatch(match)}\n`;
          });
          
          if (matches.length > 20) {
            responseText += `\n... and ${matches.length - 20} more matches`;
          }
          
          // Add summary for head-to-head queries
          if (filters.teams && filters.teams.length === 2) {
            const h2h = calculateHeadToHead(data.matches, filters.teams[0], filters.teams[1]);
            responseText += `\n\nHead-to-head summary:\n`;
            responseText += `${h2h.team1}: ${h2h.team1Wins} wins\n`;
            responseText += `${h2h.team2}: ${h2h.team2Wins} wins\n`;
            responseText += `Draws: ${h2h.draws}\n`;
            responseText += `Goals: ${h2h.team1Goals}-${h2h.team2Goals}`;
          }
        }
        
        return {
          content: [{ type: 'text', text: responseText }]
        };
      }
      
      case 'search_players': {
        const filters: {
          name?: string;
          nationality?: string;
          club?: string;
          minRating?: number;
          maxRating?: number;
          position?: string;
          limit?: number;
        } = {};
        
        if (safeArgs.name && typeof safeArgs.name === 'string') filters.name = safeArgs.name;
        if (safeArgs.nationality && typeof safeArgs.nationality === 'string') filters.nationality = safeArgs.nationality;
        if (safeArgs.club && typeof safeArgs.club === 'string') filters.club = safeArgs.club;
        if (safeArgs.minRating && typeof safeArgs.minRating === 'number') filters.minRating = safeArgs.minRating;
        if (safeArgs.maxRating && typeof safeArgs.maxRating === 'number') filters.maxRating = safeArgs.maxRating;
        if (safeArgs.position && typeof safeArgs.position === 'string') filters.position = safeArgs.position;
        if (safeArgs.limit && typeof safeArgs.limit === 'number') filters.limit = safeArgs.limit;
        
        const players = filterPlayers(data.players, filters);
        
        let responseText = '';
        if (players.length === 0) {
          responseText = 'No players found matching the criteria.';
        } else {
          responseText = `Found ${players.length} players:\n\n`;
          players.slice(0, 20).forEach((player, i) => {
            responseText += `${i + 1}. ${formatPlayer(player)}\n`;
          });
          
          if (players.length > 20) {
            responseText += `\n... and ${players.length - 20} more players`;
          }
          
          // Add summary for Brazilian players
          if (safeArgs.nationality && typeof safeArgs.nationality === 'string' && 
              safeArgs.nationality.toLowerCase().includes('brazil')) {
            const brazilianPlayers = data.players.filter(p => 
              p.nationality.toLowerCase().includes('brazil')
            );
            const avgRating = brazilianPlayers.length > 0 
              ? brazilianPlayers.reduce((sum, p) => sum + p.overall, 0) / brazilianPlayers.length 
              : 0;
            responseText += `\n\nBrazilian players summary: ${brazilianPlayers.length} players, average rating: ${avgRating.toFixed(1)}`;
          }
        }
        
        return {
          content: [{ type: 'text', text: responseText }]
        };
      }
      
      case 'get_team_stats': {
        if (!safeArgs.team || typeof safeArgs.team !== 'string') {
          throw new Error('Team name is required');
        }
        
        const season = safeArgs.season && typeof safeArgs.season === 'number' ? safeArgs.season : undefined;
        const competition = safeArgs.competition && typeof safeArgs.competition === 'string' ? safeArgs.competition : undefined;
        
        const stats = calculateTeamStats(data.matches, safeArgs.team, { season, competition });
        
        let responseText = `Statistics for ${stats.team}:\n\n`;
        responseText += `Matches: ${stats.matches}\n`;
        responseText += `Record: ${stats.wins}W ${stats.draws}D ${stats.losses}L\n`;
        responseText += `Goals: ${stats.goalsFor} for, ${stats.goalsAgainst} against (${stats.goalDifference > 0 ? '+' : ''}${stats.goalDifference})\n`;
        responseText += `Win rate: ${stats.winRate.toFixed(1)}%\n`;
        
        if (stats.homeRecord) {
          responseText += `\nHome record: ${stats.homeRecord.wins}W ${stats.homeRecord.draws}D ${stats.homeRecord.losses}L, ${stats.homeRecord.goalsFor}-${stats.homeRecord.goalsAgainst}`;
        }
        
        if (stats.awayRecord) {
          responseText += `\nAway record: ${stats.awayRecord.wins}W ${stats.awayRecord.draws}D ${stats.awayRecord.losses}L, ${stats.awayRecord.goalsFor}-${stats.awayRecord.goalsAgainst}`;
        }
        
        if (season) {
          responseText += `\n\nFiltered to season ${season}`;
        }
        
        if (competition) {
          responseText += `\nFiltered to ${competition}`;
        }
        
        // Get recent matches
        const teamMatches = data.matches.filter(match => 
          match.homeTeam.includes(safeArgs.team as string) || 
          match.awayTeam.includes(safeArgs.team as string)
        ).sort((a, b) => b.date.getTime() - a.date.getTime()).slice(0, 5);
        
        if (teamMatches.length > 0) {
          responseText += '\n\nRecent matches:';
          teamMatches.forEach(match => {
            responseText += `\n${formatMatch(match)}`;
          });
        }
        
        return {
          content: [{ type: 'text', text: responseText }]
        };
      }
      
      case 'get_head_to_head': {
        if (!safeArgs.team1 || typeof safeArgs.team1 !== 'string' || !safeArgs.team2 || typeof safeArgs.team2 !== 'string') {
          throw new Error('Both team1 and team2 are required');
        }
        
        const h2h = calculateHeadToHead(data.matches, safeArgs.team1, safeArgs.team2);
        
        let responseText = `Head-to-head: ${h2h.team1} vs ${h2h.team2}\n\n`;
        responseText += `Total matches: ${h2h.matches.length}\n`;
        responseText += `${h2h.team1} wins: ${h2h.team1Wins}\n`;
        responseText += `${h2h.team2} wins: ${h2h.team2Wins}\n`;
        responseText += `Draws: ${h2h.draws}\n`;
        responseText += `Goals: ${h2h.team1Goals}-${h2h.team2Goals}\n`;
        
        if (h2h.matches.length > 0) {
          responseText += '\nRecent matches:';
          h2h.matches.slice(0, 10).forEach((match, i) => {
            responseText += `\n${i + 1}. ${formatMatch(match)}`;
          });
          
          if (h2h.matches.length > 10) {
            responseText += `\n... and ${h2h.matches.length - 10} more matches`;
          }
        }
        
        return {
          content: [{ type: 'text', text: responseText }]
        };
      }
      
      case 'get_competition_standings': {
        if (!safeArgs.competition || typeof safeArgs.competition !== 'string') {
          throw new Error('Competition name is required');
        }
        
        const season = safeArgs.season && typeof safeArgs.season === 'number' ? safeArgs.season : undefined;
        const standings = calculateStandings(data.matches, safeArgs.competition, season);
        
        let responseText = `${standings.competition} ${standings.season} Standings:\n\n`;
        
        standings.teams.slice(0, 20).forEach((team, i) => {
          responseText += `${i + 1}. ${team.team}: ${team.points} pts, ${team.matches} games, ${team.wins}W ${team.draws}D ${team.losses}L, ${team.goalsFor}-${team.goalsAgainst} (${team.goalDifference > 0 ? '+' : ''}${team.goalDifference})\n`;
        });
        
        if (standings.teams.length > 20) {
          responseText += `\n... and ${standings.teams.length - 20} more teams`;
        }
        
        return {
          content: [{ type: 'text', text: responseText }]
        };
      }
      
      case 'get_overall_stats': {
        let matches = data.matches;
        
        if (safeArgs.competition && typeof safeArgs.competition === 'string') {
          matches = matches.filter(match => 
            match.competition?.toLowerCase().includes((safeArgs.competition as string).toLowerCase())
          );
        }
        
        if (safeArgs.season && typeof safeArgs.season === 'number') {
          matches = matches.filter(match => match.season === safeArgs.season);
        }
        
        const stats = calculateOverallStats(matches);
        
        let responseText = 'Overall Statistics:\n\n';
        responseText += `Total matches: ${stats.totalMatches}\n`;
        responseText += `Average goals per match: ${stats.averageGoalsPerMatch.toFixed(2)}\n`;
        responseText += `Home win rate: ${stats.homeWinRate.toFixed(1)}%\n`;
        responseText += `Draw rate: ${stats.drawRate.toFixed(1)}%\n`;
        responseText += `Away win rate: ${stats.awayWinRate.toFixed(1)}%\n`;
        
        if (stats.biggestHomeWin) {
          responseText += `\nBiggest home win: ${formatMatch(stats.biggestHomeWin)}`;
        }
        
        if (stats.biggestAwayWin) {
          responseText += `\nBiggest away win: ${formatMatch(stats.biggestAwayWin)}`;
        }
        
        if (safeArgs.competition) {
          responseText += `\n\nFiltered to ${safeArgs.competition}`;
        }
        
        if (safeArgs.season) {
          responseText += `\nFiltered to season ${safeArgs.season}`;
        }
        
        return {
          content: [{ type: 'text', text: responseText }]
        };
      }
      
      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    return {
      content: [{ 
        type: 'text', 
        text: `Error: ${error instanceof Error ? error.message : String(error)}` 
      }],
      isError: true
    };
  }
});

// Start the server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Brazilian Soccer MCP Server running on stdio');
}

main().catch((error) => {
  console.error('Server error:', error);
  process.exit(1);
});