#!/usr/bin/env node
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import {
  loadAllMatches,
  loadFIFAData,
  normalizeTeamName,
} from './utils/csvLoader.js';
import {
  Match,
  Player,
  TeamStats,
} from './types/index.js';

// Data storage
let allMatches: Match[] = [];
let allPlayers: Player[] = [];

// Initialize the MCP server
const server = new McpServer({
  name: 'brazilian-soccer-mcp-server',
  version: '1.0.0',
}, {
  capabilities: {
    tools: {},
  },
  instructions: `This is a Brazilian Soccer MCP Server that provides access to historical data about Brazilian football.
You can query information about:
- Matches from Brasileirão, Copa do Brasil, and Copa Libertadores
- Team statistics and head-to-head records
- Player information from FIFA database
- Competition standings and statistics

Use the available tools to search and analyze Brazilian soccer data.`,
});

// Tool: Find matches by team
server.registerTool('find_matches_by_team', {
  description: 'Find matches for a specific team or between two teams. Returns match details including date, score, and competition.',
  inputSchema: {
    team: z.string().describe('Team name (e.g., "Flamengo", "Palmeiras")'),
    opponent: z.string().optional().describe('Optional: specific opponent to filter for head-to-head matches'),
    competition: z.string().optional().describe('Optional: filter by competition (e.g., "Brasileirão", "Copa do Brasil", "Libertadores")'),
    season: z.number().optional().describe('Optional: filter by season year (e.g., 2023)'),
  },
  annotations: {
    title: 'Find Matches by Team',
  },
}, async (args: any) => {
  const { team, opponent, competition, season } = args;

  const normalizedTeam = normalizeTeamName(team);
  const normalizedOpponent = opponent ? normalizeTeamName(opponent) : null;

  let matches = allMatches.filter(m =>
    (normalizeTeamName(m.homeTeam) === normalizedTeam ||
     normalizeTeamName(m.awayTeam) === normalizedTeam)
  );

  if (normalizedOpponent) {
    matches = matches.filter(m =>
      (normalizeTeamName(m.homeTeam) === normalizedTeam && normalizeTeamName(m.awayTeam) === normalizedOpponent) ||
      (normalizeTeamName(m.awayTeam) === normalizedTeam && normalizeTeamName(m.homeTeam) === normalizedOpponent)
    );
  }

  if (competition) {
    matches = matches.filter(m => m.competition.toLowerCase().includes(competition.toLowerCase()));
  }

  if (season) {
    matches = matches.filter(m => m.season === season);
  }

  if (matches.length === 0) {
    return { content: [{ type: 'text', text: `No matches found for ${team}${opponent ? ` vs ${opponent}` : ''}.` }] };
  }

  const matchList = matches.slice(0, 50).map(m =>
    `${m.datetime.split(' ')[0]}: ${m.homeTeam} ${m.homeGoal}-${m.awayGoal} ${m.awayTeam} (${m.competition}${m.round ? ` Round ${m.round}` : ''})`
  ).join('\n');

  return {
    content: [{
      type: 'text',
      text: `Found ${matches.length} matches for ${team}${opponent ? ` vs ${opponent}` : ''}:\n\n${matchList}${matches.length > 50 ? `\n\n... and ${matches.length - 50} more matches` : ''}`,
    }],
  };
});

// Tool: Get team statistics
server.registerTool('get_team_stats', {
  description: 'Get comprehensive statistics for a team including wins, losses, goals, and win rate. Can filter by competition and season.',
  inputSchema: {
    team: z.string().describe('Team name (e.g., "Corinthians", "Palmeiras")'),
    competition: z.string().optional().describe('Optional: filter by competition'),
    season: z.number().optional().describe('Optional: filter by season year'),
    homeAway: z.enum(['home', 'away', 'all']).optional().describe('Optional: "home", "away", or "all" (default)'),
  },
  annotations: {
    title: 'Get Team Statistics',
  },
}, async (args: any) => {
  const { team, competition, season, homeAway = 'all' } = args;

  const normalizedTeam = normalizeTeamName(team);

  let matches = allMatches.filter(m => {
    const isHome = normalizeTeamName(m.homeTeam) === normalizedTeam;
    const isAway = normalizeTeamName(m.awayTeam) === normalizedTeam;

    if (homeAway === 'home') return isHome;
    if (homeAway === 'away') return isAway;
    return isHome || isAway;
  });

  if (competition) {
    matches = matches.filter(m => m.competition.toLowerCase().includes(competition.toLowerCase()));
  }

  if (season) {
    matches = matches.filter(m => m.season === season);
  }

  if (matches.length === 0) {
    return { content: [{ type: 'text', text: `No matches found for ${team}.` }] };
  }

  const stats: TeamStats = {
    team,
    matches: matches.length,
    wins: 0,
    draws: 0,
    losses: 0,
    goalsFor: 0,
    goalsAgainst: 0,
    points: 0,
  };

  matches.forEach(m => {
    const isHome = normalizeTeamName(m.homeTeam) === normalizedTeam;
    const teamGoals = isHome ? m.homeGoal : m.awayGoal;
    const opponentGoals = isHome ? m.awayGoal : m.homeGoal;

    stats.goalsFor += teamGoals;
    stats.goalsAgainst += opponentGoals;

    if (teamGoals > opponentGoals) {
      stats.wins++;
      stats.points += 3;
    } else if (teamGoals === opponentGoals) {
      stats.draws++;
      stats.points += 1;
    } else {
      stats.losses++;
    }
  });

  const winRate = ((stats.wins / stats.matches) * 100).toFixed(1);

  return {
    content: [{
      type: 'text',
      text: `${team} Statistics${competition ? ` (${competition})` : ''}${season ? ` - ${season}` : ''}:\n\n` +
        `Matches: ${stats.matches}\n` +
        `Wins: ${stats.wins}, Draws: ${stats.draws}, Losses: ${stats.losses}\n` +
        `Goals For: ${stats.goalsFor}, Goals Against: ${stats.goalsAgainst}\n` +
        `Goal Difference: ${stats.goalsFor - stats.goalsAgainst}\n` +
        `Points: ${stats.points}\n` +
        `Win Rate: ${winRate}%`,
    }],
  };
});

// Tool: Search players
server.registerTool('search_players', {
  description: 'Search for players by name, nationality, club, or position. Returns player details including ratings and attributes.',
  inputSchema: {
    name: z.string().optional().describe('Optional: search by player name (partial match)'),
    nationality: z.string().optional().describe('Optional: filter by nationality (e.g., "Brazil", "Argentina")'),
    club: z.string().optional().describe('Optional: filter by club name (partial match)'),
    position: z.string().optional().describe('Optional: filter by position (e.g., "FW", "GK", "MF")'),
    minOverall: z.number().optional().describe('Optional: minimum overall rating'),
    maxResults: z.number().optional().describe('Optional: maximum number of results (default 20)'),
  },
  annotations: {
    title: 'Search Players',
  },
}, async (args: any) => {
  const { name, nationality, club, position, minOverall, maxResults = 20 } = args;

  let players = allPlayers;

  if (name) {
    players = players.filter(p => p.name.toLowerCase().includes(name.toLowerCase()));
  }

  if (nationality) {
    players = players.filter(p => p.nationality.toLowerCase().includes(nationality.toLowerCase()));
  }

  if (club) {
    players = players.filter(p => p.club.toLowerCase().includes(club.toLowerCase()));
  }

  if (position) {
    players = players.filter(p => p.position.toLowerCase().includes(position.toLowerCase()));
  }

  if (minOverall) {
    players = players.filter(p => p.overall >= minOverall);
  }

  // Sort by overall rating
  players.sort((a, b) => b.overall - a.overall);

  if (players.length === 0) {
    return { content: [{ type: 'text', text: 'No players found matching the criteria.' }] };
  }

  const playerList = players.slice(0, maxResults).map((p, i) =>
    `${i + 1}. ${p.name} - Overall: ${p.overall}, Potential: ${p.potential}, Position: ${p.position}, Club: ${p.club}, Nationality: ${p.nationality}`
  ).join('\n');

  return {
    content: [{
      type: 'text',
      text: `Found ${players.length} players${name ? ` matching "${name}"` : ''}:\n\n${playerList}${players.length > maxResults ? `\n\n... and ${players.length - maxResults} more` : ''}`,
    }],
  };
});

// Tool: Get head-to-head record
server.registerTool('get_head_to_head', {
  description: 'Get head-to-head record between two teams. Returns wins, losses, draws, and recent matches.',
  inputSchema: {
    team1: z.string().describe('First team name'),
    team2: z.string().describe('Second team name'),
    competition: z.string().optional().describe('Optional: filter by competition'),
  },
  annotations: {
    title: 'Get Head-to-Head Record',
  },
}, async (args: any) => {
  const { team1, team2, competition } = args;

  const normalizedTeam1 = normalizeTeamName(team1);
  const normalizedTeam2 = normalizeTeamName(team2);

  let matches = allMatches.filter(m => {
    const home = normalizeTeamName(m.homeTeam);
    const away = normalizeTeamName(m.awayTeam);
    return (home === normalizedTeam1 && away === normalizedTeam2) ||
           (home === normalizedTeam2 && away === normalizedTeam1);
  });

  if (competition) {
    matches = matches.filter(m => m.competition.toLowerCase().includes(competition.toLowerCase()));
  }

  if (matches.length === 0) {
    return { content: [{ type: 'text', text: `No matches found between ${team1} and ${team2}.` }] };
  }

  let team1Wins = 0, team2Wins = 0, draws = 0;

  matches.forEach(m => {
    const home = normalizeTeamName(m.homeTeam);
    if (home === normalizedTeam1) {
      if (m.homeGoal > m.awayGoal) team1Wins++;
      else if (m.homeGoal < m.awayGoal) team2Wins++;
      else draws++;
    } else {
      if (m.awayGoal > m.homeGoal) team1Wins++;
      else if (m.awayGoal < m.homeGoal) team2Wins++;
      else draws++;
    }
  });

  const recentMatches = matches.slice(-10).map(m =>
    `${m.datetime.split(' ')[0]}: ${m.homeTeam} ${m.homeGoal}-${m.awayGoal} ${m.awayTeam} (${m.competition})`
  ).join('\n');

  return {
    content: [{
      type: 'text',
      text: `Head-to-Head: ${team1} vs ${team2}\n\n` +
        `Total Matches: ${matches.length}\n` +
        `${team1} Wins: ${team1Wins}\n` +
        `${team2} Wins: ${team2Wins}\n` +
        `Draws: ${draws}\n\n` +
        `Recent Matches:\n${recentMatches}`,
    }],
  };
});

// Tool: Get competition standings
server.registerTool('get_competition_standings', {
  description: 'Calculate and display standings for a competition by season. Based on match results.',
  inputSchema: {
    competition: z.string().describe('Competition name (e.g., "Brasileirão", "Copa do Brasil")'),
    season: z.number().describe('Season year (e.g., 2023)'),
  },
  annotations: {
    title: 'Get Competition Standings',
  },
}, async (args: any) => {
  const { competition, season } = args;

  const matches = allMatches.filter(m =>
    m.season === season &&
    m.competition.toLowerCase().includes(competition.toLowerCase())
  );

  if (matches.length === 0) {
    return { content: [{ type: 'text', text: `No matches found for ${competition} ${season}.` }] };
  }

  // Calculate standings
  const teamStats = new Map<string, TeamStats>();

  matches.forEach(m => {
    const homeTeam = m.homeTeam;
    const awayTeam = m.awayTeam;

    if (!teamStats.has(homeTeam)) {
      teamStats.set(homeTeam, { team: homeTeam, matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0, points: 0 });
    }
    if (!teamStats.has(awayTeam)) {
      teamStats.set(awayTeam, { team: awayTeam, matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0, points: 0 });
    }

    const homeStats = teamStats.get(homeTeam)!;
    const awayStats = teamStats.get(awayTeam)!;

    homeStats.matches++;
    awayStats.matches++;

    homeStats.goalsFor += m.homeGoal;
    homeStats.goalsAgainst += m.awayGoal;
    awayStats.goalsFor += m.awayGoal;
    awayStats.goalsAgainst += m.homeGoal;

    if (m.homeGoal > m.awayGoal) {
      homeStats.wins++;
      homeStats.points += 3;
      awayStats.losses++;
    } else if (m.homeGoal < m.awayGoal) {
      awayStats.wins++;
      awayStats.points += 3;
      homeStats.losses++;
    } else {
      homeStats.draws++;
      awayStats.draws++;
      homeStats.points += 1;
      awayStats.points += 1;
    }
  });

  const standings = Array.from(teamStats.values())
    .sort((a, b) => {
      if (b.points !== a.points) return b.points - a.points;
      return (b.goalsFor - b.goalsAgainst) - (a.goalsFor - a.goalsAgainst);
    });

  const standingsList = standings.map((s, i) =>
    `${i + 1}. ${s.team} - ${s.points} pts (${s.wins}W, ${s.draws}D, ${s.losses}L) - GD: ${s.goalsFor - s.goalsAgainst}`
  ).join('\n');

  return {
    content: [{
      type: 'text',
      text: `${competition} ${season} Standings:\n\n${standingsList}`,
    }],
  };
});

// Tool: Get statistical analysis
server.registerTool('get_statistics', {
  description: 'Get statistical analysis including average goals per match, home/away win rates, and biggest wins.',
  inputSchema: {
    competition: z.string().optional().describe('Optional: filter by competition'),
    season: z.number().optional().describe('Optional: filter by season'),
    statType: z.enum(['average_goals', 'home_away_record', 'biggest_wins', 'all']).optional().describe('Type of statistic'),
  },
  annotations: {
    title: 'Get Statistics',
  },
}, async (args: any) => {
  const { competition, season, statType = 'all' } = args;

  let matches = allMatches;

  if (competition) {
    matches = matches.filter(m => m.competition.toLowerCase().includes(competition.toLowerCase()));
  }

  if (season) {
    matches = matches.filter(m => m.season === season);
  }

  if (matches.length === 0) {
    return { content: [{ type: 'text', text: 'No matches found.' }] };
  }

  const results: string[] = [];

  if (statType === 'average_goals' || statType === 'all') {
    const totalGoals = matches.reduce((sum, m) => sum + m.homeGoal + m.awayGoal, 0);
    const avgGoals = (totalGoals / matches.length).toFixed(2);
    results.push(`Average Goals Per Match: ${avgGoals}`);
  }

  if (statType === 'home_away_record' || statType === 'all') {
    const homeWins = matches.filter(m => m.homeGoal > m.awayGoal).length;
    const awayWins = matches.filter(m => m.homeGoal < m.awayGoal).length;
    const draws = matches.filter(m => m.homeGoal === m.awayGoal).length;

    results.push(`Home Win Rate: ${((homeWins / matches.length) * 100).toFixed(1)}%`);
    results.push(`Away Win Rate: ${((awayWins / matches.length) * 100).toFixed(1)}%`);
    results.push(`Draw Rate: ${((draws / matches.length) * 100).toFixed(1)}%`);
  }

  if (statType === 'biggest_wins' || statType === 'all') {
    const sortedByDifference = [...matches]
      .map(m => ({
        match: m,
        difference: Math.abs(m.homeGoal - m.awayGoal),
      }))
      .sort((a, b) => b.difference - a.difference)
      .slice(0, 10);

    const biggestWins = sortedByDifference.map((item, i) =>
      `${i + 1}. ${item.match.datetime.split(' ')[0]}: ${item.match.homeTeam} ${item.match.homeGoal}-${item.match.awayGoal} ${item.match.awayTeam} (${item.match.competition})`
    ).join('\n');

    results.push(`\nBiggest Wins:\n${biggestWins}`);
  }

  return {
    content: [{
      type: 'text',
      text: results.join('\n'),
    }],
  };
});

// Tool: Find matches by date range
server.registerTool('find_matches_by_date', {
  description: 'Find matches within a specific date range.',
  inputSchema: {
    startDate: z.string().describe('Start date (YYYY-MM-DD format)'),
    endDate: z.string().describe('End date (YYYY-MM-DD format)'),
    team: z.string().optional().describe('Optional: filter by team'),
    competition: z.string().optional().describe('Optional: filter by competition'),
  },
  annotations: {
    title: 'Find Matches by Date Range',
  },
}, async (args: any) => {
  const { startDate, endDate, team, competition } = args;

  let matches = allMatches.filter(m => {
    const matchDate = m.datetime.split(' ')[0];
    return matchDate >= startDate && matchDate <= endDate;
  });

  if (team) {
    const normalizedTeam = normalizeTeamName(team);
    matches = matches.filter(m =>
      normalizeTeamName(m.homeTeam) === normalizedTeam ||
      normalizeTeamName(m.awayTeam) === normalizedTeam
    );
  }

  if (competition) {
    matches = matches.filter(m => m.competition.toLowerCase().includes(competition.toLowerCase()));
  }

  if (matches.length === 0) {
    return { content: [{ type: 'text', text: `No matches found between ${startDate} and ${endDate}.` }] };
  }

  const matchList = matches.slice(0, 50).map(m =>
    `${m.datetime.split(' ')[0]}: ${m.homeTeam} ${m.homeGoal}-${m.awayGoal} ${m.awayTeam} (${m.competition})`
  ).join('\n');

  return {
    content: [{
      type: 'text',
      text: `Found ${matches.length} matches between ${startDate} and ${endDate}:\n\n${matchList}${matches.length > 50 ? `\n\n... and ${matches.length - 50} more` : ''}`,
    }],
  };
});

// Initialize and start the server
async function main() {
  console.error('Loading Brazilian Soccer data...');

  try {
    [allMatches, allPlayers] = await Promise.all([
      loadAllMatches(),
      loadFIFAData(),
    ]);

    console.error(`Loaded ${allMatches.length} matches and ${allPlayers.length} players.`);
  } catch (error) {
    console.error('Error loading data:', error);
    process.exit(1);
  }

  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.error('Brazilian Soccer MCP Server running on stdio');
}

main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
