#!/usr/bin/env node
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { loadMatches, loadPlayers, normalizeTeamName } from './data.js';
import { Match, Player } from './types.js';

let matchesCache: Match[] | null = null;
let playersCache: Player[] | null = null;

async function getMatches(): Promise<Match[]> {
  if (!matchesCache) {
    matchesCache = await loadMatches();
  }
  return matchesCache!;
}
async function getPlayers(): Promise<Player[]> {
  if (!playersCache) {
    playersCache = await loadPlayers();
  }
  return playersCache!;
}

function formatDate(date: Date): string {
  return date.toISOString().split('T')[0];
}

const server = new McpServer({
  name: 'brazilian-soccer-mcp',
  version: '1.0.0',
});

server.registerTool(
  'search_matches',
  {
    description: 'Search for matches by team, season, or competition.',
    inputSchema: z.object({
      team: z.string().optional().describe('Team name (e.g., "Flamengo", "Palmeiras")'),
      season: z.number().optional().describe('Season year (e.g., 2023)'),
      competition: z.string().optional().describe('Competition name (e.g., "Brasileirão", "Copa do Brasil")'),
      limit: z.number().optional().default(50).describe('Maximum number of results'),
    }),
  },
  async ({ team, season, competition, limit }) => {
    const matches = await getMatches();
    let filtered = matches;

    if (team) {
      const normalizedSearch = normalizeTeamName(team);
      filtered = filtered.filter(m => 
        normalizeTeamName(m.homeTeam).includes(normalizedSearch) || 
        normalizeTeamName(m.awayTeam).includes(normalizedSearch)
      );
    }

    if (season) {
      filtered = filtered.filter(m => m.season === season);
    }

    if (competition) {
      filtered = filtered.filter(m => m.competition.toLowerCase().includes(competition.toLowerCase()));
    }

    filtered = filtered.sort((a, b) => b.date.getTime() - a.date.getTime()).slice(0, limit || 50);

    const results = filtered.map(m => ({
      date: formatDate(m.date),
      season: m.season,
      competition: m.competition,
      homeTeam: m.homeTeam,
      awayTeam: m.awayTeam,
      homeGoals: m.homeGoals,
      awayGoals: m.awayGoals,
      round: m.round || m.stage || 'N/A',
    }));

    return {
      content: [{ type: 'text', text: JSON.stringify(results, null, 2) }],
    };
  }
);

server.registerTool(
  'get_team_statistics',
  {
    description: 'Get win/loss/draw records and goals for a specific team in a season.',
    inputSchema: z.object({
      team: z.string().describe('Team name'),
      season: z.number().optional().describe('Season year'),
      competition: z.string().optional().describe('Competition name'),
    }),
  },
  async ({ team, season, competition }) => {
    const matches = await getMatches();
    const normalizedSearch = normalizeTeamName(team);
    
    let filtered = matches;
    if (season) filtered = filtered.filter(m => m.season === season);
    if (competition) filtered = filtered.filter(m => m.competition.toLowerCase().includes(competition.toLowerCase()));

    const teamMatches = filtered.filter(m => 
      normalizeTeamName(m.homeTeam).includes(normalizedSearch) || 
      normalizeTeamName(m.awayTeam).includes(normalizedSearch)
    );

    let wins = 0;
    let draws = 0;
    let losses = 0;
    let goalsFor = 0;
    let goalsAgainst = 0;
    let homeMatches = 0;
    let awayMatches = 0;
    let homeWins = 0;

    for (const m of teamMatches) {
      const isHome = normalizeTeamName(m.homeTeam).includes(normalizedSearch);
      const teamGoals = isHome ? m.homeGoals : m.awayGoals;
      const oppGoals = isHome ? m.awayGoals : m.homeGoals;

      goalsFor += teamGoals;
      goalsAgainst += oppGoals;

      if (isHome) {
        homeMatches++;
        if (teamGoals > oppGoals) {
          wins++;
          homeWins++;
        } else if (teamGoals === oppGoals) {
          draws++;
        } else {
          losses++;
        }
      } else {
        awayMatches++;
        if (teamGoals > oppGoals) wins++;
        else if (teamGoals === oppGoals) draws++;
        else losses++;
      }
    }

    const totalMatches = wins + draws + losses;
    const winRate = totalMatches > 0 ? ((wins / totalMatches) * 100).toFixed(1) + '%' : '0%';

    return {
      content: [{ type: 'text', text: JSON.stringify({
        team,
        season: season || 'All',
        competition: competition || 'All',
        totalMatches,
        wins,
        draws,
        losses,
        goalsFor,
        goalsAgainst,
        homeMatches,
        awayMatches,
        homeWins,
        winRate,
      }, null, 2) }],
    };
  }
);

server.registerTool(
  'get_head_to_head',
  {
    description: 'Get head-to-head statistics between two teams.',
    inputSchema: z.object({
      team1: z.string().describe('First team name'),
      team2: z.string().describe('Second team name'),
      limit: z.number().optional().default(20).describe('Maximum number of recent matches to show'),
    }),
  },
  async ({ team1, team2, limit }) => {
    const matches = await getMatches();
    const norm1 = normalizeTeamName(team1);
    const norm2 = normalizeTeamName(team2);

    const h2hMatches = matches.filter(m => {
      const home = normalizeTeamName(m.homeTeam);
      const away = normalizeTeamName(m.awayTeam);
      return (home.includes(norm1) && away.includes(norm2)) || (home.includes(norm2) && away.includes(norm1));
    }).sort((a, b) => b.date.getTime() - a.date.getTime()).slice(0, limit || 20);

    let team1Wins = 0;
    let team2Wins = 0;
    let draws = 0;

    for (const m of h2hMatches) {
      const home = normalizeTeamName(m.homeTeam);
      const isTeam1Home = home.includes(norm1);
      
      if (m.homeGoals > m.awayGoals) {
        if (isTeam1Home) team1Wins++; else team2Wins++;
      } else if (m.homeGoals < m.awayGoals) {
        if (isTeam1Home) team2Wins++; else team1Wins++;
      } else {
        draws++;
      }
    }

    return {
      content: [{ type: 'text', text: JSON.stringify({
        team1,
        team2,
        totalMatches: h2hMatches.length,
        team1Wins,
        team2Wins,
        draws,
        recentMatches: h2hMatches.map(m => ({
          date: formatDate(m.date),
          competition: m.competition,
          homeTeam: m.homeTeam,
          awayTeam: m.awayTeam,
          score: `${m.homeGoals} - ${m.awayGoals}`,
        }))
      }, null, 2) }],
    };
  }
);

server.registerTool(
  'search_players',
  {
    description: 'Search for players by name, nationality, or club.',
    inputSchema: z.object({
      name: z.string().optional().describe('Player name or substring'),
      nationality: z.string().optional().describe('Nationality (e.g., "Brazil")'),
      club: z.string().optional().describe('Club name'),
      minOverall: z.number().optional().describe('Minimum overall rating'),
      limit: z.number().optional().default(20).describe('Maximum number of results'),
    }),
  },
  async ({ name, nationality, club, minOverall, limit }) => {
    const players = await getPlayers();
    let filtered = players;

    if (name) {
      const lowerName = name.toLowerCase();
      filtered = filtered.filter(p => p.name.toLowerCase().includes(lowerName));
    }

    if (nationality) {
      const lowerNat = nationality.toLowerCase();
      filtered = filtered.filter(p => p.nationality.toLowerCase().includes(lowerNat));
    }

    if (club) {
      const lowerClub = club.toLowerCase();
      filtered = filtered.filter(p => p.club.toLowerCase().includes(lowerClub));
    }

    if (minOverall) {
      filtered = filtered.filter(p => p.overall >= minOverall);
    }

    filtered = filtered.sort((a, b) => b.overall - a.overall).slice(0, limit || 20);

    return {
      content: [{ type: 'text', text: JSON.stringify(filtered.map(p => ({
        name: p.name,
        age: p.age,
        nationality: p.nationality,
        overall: p.overall,
        potential: p.potential,
        club: p.club,
        position: p.position,
      })), null, 2) }],
    };
  }
);

server.registerTool(
  'get_competition_standings',
  {
    description: 'Calculate standings for a competition and season based on match results.',
    inputSchema: z.object({
      competition: z.string().describe('Competition name (e.g., "Brasileirão")'),
      season: z.number().describe('Season year'),
    }),
  },
  async ({ competition, season }) => {
    const matches = await getMatches();
    const filtered = matches.filter(m => 
      m.season === season && m.competition.toLowerCase().includes(competition.toLowerCase())
    );

    const standings: Record<string, { pts: number, p: number, w: number, d: number, l: number, gf: number, ga: number, gd: number }> = {};

    for (const m of filtered) {
      const home = normalizeTeamName(m.homeTeam);
      const away = normalizeTeamName(m.awayTeam);

      if (!standings[home]) standings[home] = { pts: 0, p: 0, w: 0, d: 0, l: 0, gf: 0, ga: 0, gd: 0 };
      if (!standings[away]) standings[away] = { pts: 0, p: 0, w: 0, d: 0, l: 0, gf: 0, ga: 0, gd: 0 };

      const homeStats = standings[home];
      const awayStats = standings[away];

      homeStats.p++;
      awayStats.p++;
      homeStats.gf += m.homeGoals;
      homeStats.ga += m.awayGoals;
      homeStats.gd = homeStats.gf - homeStats.ga;
      awayStats.gf += m.awayGoals;
      awayStats.ga += m.homeGoals;
      awayStats.gd = awayStats.gf - awayStats.ga;

      if (m.homeGoals > m.awayGoals) {
        homeStats.w++;
        homeStats.pts += 3;
        awayStats.l++;
      } else if (m.homeGoals < m.awayGoals) {
        awayStats.w++;
        awayStats.pts += 3;
        homeStats.l++;
      } else {
        homeStats.d++;
        homeStats.pts += 1;
        awayStats.d++;
        awayStats.pts += 1;
      }
    }

    const sorted = Object.entries(standings)
      .map(([team, stats]) => ({ team, ...stats }))
      .sort((a, b) => b.pts - a.pts || b.gd - a.gd || b.gf - a.gf);

    return {
      content: [{ type: 'text', text: JSON.stringify(sorted, null, 2) }],
    };
  }
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch(console.error);