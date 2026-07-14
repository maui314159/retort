#!/usr/bin/env node
/**
 * Brazilian Soccer MCP Server
 *
 * MCP server providing a knowledge graph interface for Brazilian soccer data.
 * Loads 6 Kaggle datasets and exposes query tools for matches, teams, players,
 * competitions, and statistical analysis.
 *
 * Data sources (all CC-licensed):
 *   - Brasileirao_Matches.csv (CC BY 4.0)
 *   - Brazilian_Cup_Matches.csv (CC BY 4.0)
 *   - Libertadores_Matches.csv (CC BY 4.0)
 *   - BR-Football-Dataset.csv (CC0)
 *   - novo_campeonato_brasileiro.csv (CC BY 4.0)
 *   - fifa_data.csv (Apache 2.0)
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';

import { loadAllData, getMatchCount, getPlayerCount } from './data.js';
import {
  searchMatches,
  getTeamRecord,
  getHeadToHead,
  searchPlayers,
  getStandings,
  getBiggestWins,
  getAverageGoals,
  getHomeAwayStats,
  getTopScoringTeams,
  getTeamBestAwayRecord,
  getCompetitionList,
  getSeasonList,
} from './queries.js';

// ── Preload data at startup ──────────────────────────────────────────

loadAllData();

// ── Formatting helpers ───────────────────────────────────────────────

function formatMatchLine(m: {
  date: string;
  homeTeamDisplay: string;
  awayTeamDisplay: string;
  homeGoal: number;
  awayGoal: number;
  competition: string;
  round: string;
  stage: string;
  season: number;
}): string {
  const roundInfo = m.round ? ` Round ${m.round}` : '';
  const stageInfo = m.stage ? ` (${m.stage})` : '';
  const compDisplay = m.competition.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  return `${m.date}: ${m.homeTeamDisplay} ${m.homeGoal}-${m.awayGoal} ${m.awayTeamDisplay} (${compDisplay}${roundInfo}${stageInfo})`;
}

// ── Server setup ─────────────────────────────────────────────────────

const server = new McpServer({
  name: 'brazilian-soccer-mcp',
  version: '1.0.0',
});

// ── Tools ────────────────────────────────────────────────────────────

// 1. search_matches
server.registerTool(
  'search_matches',
  {
    description: 'Search Brazilian soccer matches by team, competition, season, or date range.',
    inputSchema: {
      team: z.string().optional().describe('Team name to search for (home or away)'),
      opponent: z.string().optional().describe('Opponent team name (narrows to matches between these two teams)'),
      competition: z.string().optional().describe('Competition: "brasileirao", "copa do brasil", or "libertadores"'),
      season: z.number().optional().describe('Season year (e.g. 2023)'),
      dateFrom: z.string().optional().describe('Start date in YYYY-MM-DD format'),
      dateTo: z.string().optional().describe('End date in YYYY-MM-DD format'),
      limit: z.number().optional().default(50).describe('Maximum matches to return'),
    },
  },
  async ({ team, opponent, competition, season, dateFrom, dateTo, limit }) => {
    const results = searchMatches({ team, opponent, competition, season, dateFrom, dateTo, limit });
    if (results.length === 0) {
      return { content: [{ type: 'text' as const, text: 'No matches found matching the criteria.' }] };
    }
    const lines = results.map(formatMatchLine);
    return {
      content: [{ type: 'text' as const, text: `Found ${results.length} match(es):\n\n${lines.join('\n')}` }],
    };
  }
);

// 2. get_team_stats
server.registerTool(
  'get_team_stats',
  {
    description: 'Get comprehensive statistics for a team: wins, losses, draws, goals, home/away records, per-competition breakdown.',
    inputSchema: {
      team: z.string().describe('Team name (e.g. "Flamengo", "Palmeiras", "Corinthians")'),
    },
  },
  async ({ team }) => {
    const record = getTeamRecord(team);
    if (!record) {
      return { content: [{ type: 'text' as const, text: `No match data found for team "${team}".` }] };
    }

    const lines = [
      `${record.teamDisplay} - All-Time Record`,
      `─────────────────────────────────`,
      `Matches: ${record.matches} | Wins: ${record.wins} | Draws: ${record.draws} | Losses: ${record.losses}`,
      `Goals For: ${record.goalsFor} | Goals Against: ${record.goalsAgainst} | Goal Diff: ${record.goalsFor - record.goalsAgainst > 0 ? '+' : ''}${record.goalsFor - record.goalsAgainst}`,
      `Points: ${record.points} | Win Rate: ${record.matches > 0 ? Math.round((record.wins / record.matches) * 1000) / 10 : 0}%`,
      ``,
      `Home Record: ${record.homeStats.wins}W ${record.homeStats.draws}D ${record.homeStats.losses}L (GF:${record.homeStats.goalsFor} GA:${record.homeStats.goalsAgainst})`,
      `Away Record: ${record.awayStats.wins}W ${record.awayStats.draws}D ${record.awayStats.losses}L (GF:${record.awayStats.goalsFor} GA:${record.awayStats.goalsAgainst})`,
    ];

    if (Object.keys(record.competitions).length > 0) {
      lines.push(``, `By Competition:`);
      for (const [comp, stats] of Object.entries(record.competitions)) {
        const compName = comp.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        lines.push(`  ${compName}: ${stats.matches} matches, ${stats.wins}W ${stats.draws}D ${stats.losses}L`);
      }
    }

    return { content: [{ type: 'text' as const, text: lines.join('\n') }] };
  }
);

// 3. get_head_to_head
server.registerTool(
  'get_head_to_head',
  {
    description: 'Compare two teams head-to-head: total matches, wins, draws, goals, and recent match history.',
    inputSchema: {
      team1: z.string().describe('First team name'),
      team2: z.string().describe('Second team name'),
    },
  },
  async ({ team1, team2 }) => {
    const h2h = getHeadToHead(team1, team2);
    if (!h2h) {
      return { content: [{ type: 'text' as const, text: `No head-to-head matches found between "${team1}" and "${team2}".` }] };
    }

    const lines = [
      `${h2h.team1Display} vs ${h2h.team2Display} - Head-to-Head`,
      `─────────────────────────────────────────`,
      `Total Matches: ${h2h.totalMatches}`,
      `${h2h.team1Display}: ${h2h.team1Wins} wins, ${h2h.team1Goals} goals`,
      `${h2h.team2Display}: ${h2h.team2Wins} wins, ${h2h.team2Goals} goals`,
      `Draws: ${h2h.draws}`,
      ``,
      `Recent Matches:`,
      ...h2h.matches.slice(0, 20).map(formatMatchLine),
    ];

    if (h2h.matches.length > 20) {
      lines.push(`... and ${h2h.matches.length - 20} more matches`);
    }

    return { content: [{ type: 'text' as const, text: lines.join('\n') }] };
  }
);

// 4. search_players
server.registerTool(
  'search_players',
  {
    description: 'Search FIFA player database by name, nationality, club, position, or rating range.',
    inputSchema: {
      name: z.string().optional().describe('Player name to search (partial match)'),
      nationality: z.string().optional().describe('Nationality (e.g. "Brazil", "Argentina")'),
      club: z.string().optional().describe('Club name (e.g. "Flamengo", "Real Madrid")'),
      position: z.string().optional().describe('Playing position (e.g. "ST", "GK", "LW")'),
      minRating: z.number().optional().describe('Minimum overall rating (0-99)'),
      maxRating: z.number().optional().describe('Maximum overall rating (0-99)'),
      sortBy: z.string().optional().default('-overall').describe('Sort field (e.g. "overall", "-potential", "age")'),
      limit: z.number().optional().default(25).describe('Maximum players to return'),
    },
  },
  async ({ name, nationality, club, position, minRating, maxRating, sortBy, limit }) => {
    const results = searchPlayers({ name, nationality, club, position, minRating, maxRating, sortBy, limit });
    if (results.length === 0) {
      return { content: [{ type: 'text' as const, text: 'No players found matching the criteria.' }] };
    }

    const lines = [`Found ${results.length} player(s):`, ''];
    for (const p of results) {
      lines.push(
        `${p.name} | Overall: ${p.overall} | Pot: ${p.potential} | Pos: ${p.position} | Age: ${p.age} | Club: ${p.clubDisplay} | ${p.nationality}`
      );
    }

    return { content: [{ type: 'text' as const, text: lines.join('\n') }] };
  }
);

// 5. get_standings
server.registerTool(
  'get_standings',
  {
    description: 'Get competition standings for a given season, calculated from match results.',
    inputSchema: {
      competition: z.string().describe('Competition: "brasileirao", "copa do brasil", or "libertadores"'),
      season: z.number().describe('Season year (e.g. 2019, 2023)'),
    },
  },
  async ({ competition, season }) => {
    const standings = getStandings(competition, season);
    if (standings.length === 0) {
      return { content: [{ type: 'text' as const, text: `No standings available for ${competition} ${season}.` }] };
    }

    const compDisplay = competition.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    const lines = [
      `${compDisplay} ${season} - Standings`,
      `──────────────────────────────────────────────`,
      `Pos  Team                      P   W   D   L   GF  GA  GD  Pts`,
      `───  ────                      ─   ─   ─   ─   ──  ──  ──  ───`,
    ];

    for (const s of standings) {
      const pos = String(s.position).padStart(2);
      const team = s.teamDisplay.padEnd(24).slice(0, 24);
      lines.push(
        `${pos}.  ${team}  ${String(s.played).padStart(2)}  ${String(s.wins).padStart(2)}  ${String(s.draws).padStart(2)}  ${String(s.losses).padStart(2)}  ${String(s.goalsFor).padStart(2)}  ${String(s.goalsAgainst).padStart(2)}  ${String(s.goalDifference > 0 ? '+' + s.goalDifference : s.goalDifference).padStart(3)}  ${String(s.points).padStart(3)}`
      );
    }

    return { content: [{ type: 'text' as const, text: lines.join('\n') }] };
  }
);

// 6. get_biggest_wins
server.registerTool(
  'get_biggest_wins',
  {
    description: 'Find the biggest wins (largest goal difference) in the dataset.',
    inputSchema: {
      competition: z.string().optional().describe('Filter by competition (optional)'),
      limit: z.number().optional().default(10).describe('Number of results to return'),
    },
  },
  async ({ competition, limit }) => {
    const wins = getBiggestWins(competition, limit);
    const compLabel = competition ? ` in ${competition.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}` : '';
    const lines = [
      `Biggest Victories${compLabel}:`,
      `─────────────────────────────────────`,
      ...wins.map((m, i) => {
        const diff = Math.abs(m.homeGoal - m.awayGoal);
        return `${i + 1}. ${m.date}: ${m.homeTeamDisplay} ${m.homeGoal}-${m.awayGoal} ${m.awayTeamDisplay} (${m.competition.replace(/_/g, ' ')}, +${diff} goal diff)`;
      }),
    ];

    return { content: [{ type: 'text' as const, text: lines.join('\n') }] };
  }
);

// 7. get_competition_stats
server.registerTool(
  'get_competition_stats',
  {
    description: 'Get aggregate statistics for a competition: average goals, home/away win rates, top scoring teams.',
    inputSchema: {
      competition: z.string().describe('Competition: "brasileirao", "copa do brasil", or "libertadores"'),
      season: z.number().optional().describe('Season year (optional, for single-season stats)'),
    },
  },
  async ({ competition, season }) => {
    const avgGoals = getAverageGoals(competition, season);
    const haStats = getHomeAwayStats(competition, season);
    const topScorers = getTopScoringTeams(competition, season, 5);

    const compDisplay = competition.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    const seasonLabel = season ? ` ${season}` : ' (all seasons)';

    const lines = [
      `${compDisplay}${seasonLabel} - Statistics`,
      `─────────────────────────────────────────`,
      `Total Matches: ${avgGoals.totalMatches}`,
      `Total Goals: ${avgGoals.totalGoals}`,
      `Average Goals per Match: ${avgGoals.avgGoalsPerMatch}`,
      ``,
      `Home Wins: ${haStats.homeWins} (${haStats.homeWinRate}%)`,
      `Away Wins: ${haStats.awayWins}`,
      `Draws: ${haStats.draws}`,
      ``,
      `Top Scoring Teams:`,
      ...topScorers.map((t, i) =>
        `  ${i + 1}. ${t.teamDisplay} - ${t.goals} goals in ${t.matches} matches (${Math.round(t.goals / t.matches * 100) / 100} per match)`
      ),
    ];

    return { content: [{ type: 'text' as const, text: lines.join('\n') }] };
  }
);

// 8. get_best_away_teams
server.registerTool(
  'get_best_away_teams',
  {
    description: 'Find teams with the best away win records.',
    inputSchema: {
      limit: z.number().optional().default(10).describe('Number of teams to return'),
    },
  },
  async ({ limit }) => {
    const teams = getTeamBestAwayRecord(limit);
    const lines = [
      `Best Away Records (min 5 matches):`,
      `───────────────────────────────────`,
      ...teams.map((t, i) =>
        `${i + 1}. ${t.teamDisplay} - ${t.awayWins}W in ${t.awayMatches} away matches (${t.awayWinRate}%)`
      ),
    ];
    return { content: [{ type: 'text' as const, text: lines.join('\n') }] };
  }
);

// 9. get_server_info
server.registerTool(
  'get_server_info',
  {
    description: 'Get information about the server: loaded datasets, match/player counts, available competitions.',
    inputSchema: {},
  },
  async () => {
    const comps = getCompetitionList();
    const seasons = getSeasonList();

    const lines = [
      `Brazilian Soccer MCP Server v1.0.0`,
      `───────────────────────────────────`,
      `Loaded Datasets:`,
      `  - Brasileirao_Matches.csv (Serie A matches)`,
      `  - Brazilian_Cup_Matches.csv (Copa do Brasil)`,
      `  - Libertadores_Matches.csv (Copa Libertadores)`,
      `  - BR-Football-Dataset.csv (Extended match stats)`,
      `  - novo_campeonato_brasileiro.csv (Historical 2003-2019)`,
      `  - fifa_data.csv (FIFA player database)`,
      ``,
      `Total Matches Loaded: ${getMatchCount()}`,
      `Total Players Loaded: ${getPlayerCount()}`,
      ``,
      `Competitions Available: ${comps.map(c => c.replace(/_/g, ' ').replace(/\b\w/g, c2 => c2.toUpperCase())).join(', ')}`,
      `Seasons Available: ${seasons.slice(0, 10).join(', ')}... (${seasons.length} total)`,
    ];

    return { content: [{ type: 'text' as const, text: lines.join('\n') }] };
  }
);

// ── Main ─────────────────────────────────────────────────────────────

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  // Log to stderr (stdio transport uses stdout for protocol)
  console.error(`Brazilian Soccer MCP Server started. ${getMatchCount()} matches, ${getPlayerCount()} players loaded.`);
}

main().catch(err => {
  console.error('Failed to start server:', err);
  process.exit(1);
});
