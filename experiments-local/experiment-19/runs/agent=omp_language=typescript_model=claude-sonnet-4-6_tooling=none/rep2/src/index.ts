#!/usr/bin/env node
/**
 * Brazilian Soccer MCP Server
 *
 * Provides tools for querying Brazilian soccer data:
 * Brasileirão Serie A, Copa do Brasil, Copa Libertadores, and FIFA player data.
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';

import { getDatabase } from './data-loader.js';
import {
  biggestWins,
  buildTeamRecord,
  competitionOverview,
  computeStandings,
  filterMatches,
  filterPlayers,
  headToHead,
  highScoringMatches,
  rankTeams,
  resolveCompetition,
} from './query-engine.js';
import type { Match, TeamRecord } from './types.js';

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

function formatMatch(m: Match, includeCompetition = true): string {
  const winner =
    m.homeGoals > m.awayGoals
      ? ` (${m.homeTeamNormalized} won)`
      : m.homeGoals < m.awayGoals
        ? ` (${m.awayTeamNormalized} won)`
        : ' (draw)';
  const comp = includeCompetition
    ? ` [${m.competition}${m.round ? ' Round ' + m.round : ''}${m.stage ? ' – ' + m.stage : ''}]`
    : '';
  return `${m.date}: ${m.homeTeamNormalized} ${m.homeGoals}–${m.awayGoals} ${m.awayTeamNormalized}${winner}${comp}`;
}

function formatRecord(rec: TeamRecord, pos?: number): string {
  const prefix = pos !== undefined ? `${pos}. ` : '';
  return (
    `${prefix}${rec.team} – ${rec.points} pts ` +
    `(${rec.wins}W ${rec.draws}D ${rec.losses}L) ` +
    `GF:${rec.goalsFor} GA:${rec.goalsAgainst} GD:${rec.goalDiff > 0 ? '+' : ''}${rec.goalDiff} ` +
    `Win rate: ${(rec.winRate * 100).toFixed(1)}%`
  );
}

function pct(n: number): string {
  return (n * 100).toFixed(1) + '%';
}

// ---------------------------------------------------------------------------
// MCP Server
// ---------------------------------------------------------------------------

const server = new McpServer({
  name: 'brazilian-soccer-mcp-server',
  version: '1.0.0',
});

// ---------------------------------------------------------------------------
// Tool: search_matches
// ---------------------------------------------------------------------------

server.registerTool(
  'search_matches',
  {
    title: 'Search Matches',
    description: `Search Brazilian soccer match records across all competitions and datasets.

Supported competitions: Brasileirão Serie A, Copa do Brasil, Copa Libertadores, Serie B, Serie C.
Data covers: Brasileirão 2012-2022, historical Brasileirão 2003-2019, Copa do Brasil 2012-2021,
Copa Libertadores 2013-2022, plus extended stats dataset 2014-2023.

Args:
  - team: Filter matches involving this team (home or away)
  - opponent: Filter matches involving this opponent (use with team for head-to-head)
  - competition: Competition filter — "brasileirao", "copa brasil", "libertadores", "serie b", "serie c"
  - season: Year (e.g. 2019)
  - date_from: Start date ISO YYYY-MM-DD (inclusive)
  - date_to: End date ISO YYYY-MM-DD (inclusive)
  - venue: "home" | "away" | "all" (applies only when team is set)
  - limit: Max results to return (default 20, max 100)
  - offset: Results to skip for pagination (default 0)

Returns: List of matches with date, teams, score, competition, and head-to-head summary when
two teams are specified.`,
    inputSchema: z.object({
      team: z.string().optional().describe('Team name to search for'),
      opponent: z.string().optional().describe('Opponent team (combine with team for head-to-head)'),
      competition: z.string().optional().describe('Competition filter'),
      season: z.number().int().optional().describe('Season year'),
      date_from: z.string().optional().describe('Start date YYYY-MM-DD'),
      date_to: z.string().optional().describe('End date YYYY-MM-DD'),
      venue: z.enum(['home', 'away', 'all']).default('all').describe('Venue filter (requires team)'),
      limit: z.number().int().min(1).max(100).default(20).describe('Max results'),
      offset: z.number().int().min(0).default(0).describe('Pagination offset'),
    }),
    annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
  },
  async ({ team, opponent, competition, season, date_from, date_to, venue, limit, offset }) => {
    const { matches } = getDatabase();
    const filtered = filterMatches(matches, {
      team,
      opponent,
      competition,
      season,
      dateFrom: date_from,
      dateTo: date_to,
      venue,
    });

    const total = filtered.length;
    const page = filtered.slice(offset, offset + limit);

    const lines: string[] = [];

    if (team && opponent) {
      // Head-to-head summary header
      const h2h = headToHead(matches, team, opponent, competition, season);
      lines.push(`## Head-to-Head: ${team} vs ${opponent}`);
      lines.push(
        `Total: ${h2h.matches.length} matches | ` +
          `${team}: ${h2h.team1Wins} wins, ${h2h.team2Wins} wins for ${opponent}, ${h2h.draws} draws`
      );
      lines.push(
        `Goals: ${team} ${h2h.team1Goals} – ${h2h.team2Goals} ${opponent}`
      );
      lines.push('');
    } else if (team) {
      lines.push(`## Matches involving ${team}`);
    } else {
      lines.push('## Match Results');
    }

    if (competition) {
      const resolved = resolveCompetition(competition);
      lines.push(`Competition: ${resolved ?? competition}`);
    }
    if (season) lines.push(`Season: ${season}`);
    lines.push(`Showing ${page.length} of ${total} matches (offset ${offset})`);
    lines.push('');

    for (const m of page) {
      lines.push(formatMatch(m));
    }

    if (total > offset + limit) {
      lines.push('');
      lines.push(`... ${total - offset - limit} more matches. Use offset=${offset + limit} to see next page.`);
    }

    return { content: [{ type: 'text', text: lines.join('\n') }] };
  }
);

// ---------------------------------------------------------------------------
// Tool: get_team_stats
// ---------------------------------------------------------------------------

server.registerTool(
  'get_team_stats',
  {
    title: 'Get Team Statistics',
    description: `Calculate win/loss/draw record and goals statistics for a team.

Args:
  - team: Team name (required)
  - competition: Optional competition filter
  - season: Optional season year
  - venue: "home" | "away" | "all" (default "all")

Returns: Matches played, W/D/L, goals for/against, points, win rate.
Note: Points are calculated as Win=3, Draw=1, Loss=0 (standard Brazilian football rules).`,
    inputSchema: z.object({
      team: z.string().min(2).describe('Team name'),
      competition: z.string().optional().describe('Competition filter'),
      season: z.number().int().optional().describe('Season year'),
      venue: z.enum(['home', 'away', 'all']).default('all').describe('Home, away, or all matches'),
    }),
    annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
  },
  async ({ team, competition, season, venue }) => {
    const { matches } = getDatabase();
    const relevant = filterMatches(matches, { team, competition, season, venue });

    if (relevant.length === 0) {
      return {
        content: [{ type: 'text', text: `No matches found for "${team}"${season ? ` in ${season}` : ''}.` }],
      };
    }

    const rec = buildTeamRecord(team, relevant);
    const compLabel = competition ? ` (${competition})` : '';
    const seasonLabel = season ? ` ${season}` : '';
    const venueLabel = venue !== 'all' ? ` [${venue} matches]` : '';

    const lines = [
      `## ${rec.team}${compLabel}${seasonLabel}${venueLabel}`,
      '',
      `Matches: ${rec.matches}`,
      `Wins:    ${rec.wins}  Draws: ${rec.draws}  Losses: ${rec.losses}`,
      `Goals For: ${rec.goalsFor}  Goals Against: ${rec.goalsAgainst}  Goal Diff: ${rec.goalDiff >= 0 ? '+' : ''}${rec.goalDiff}`,
      `Points:  ${rec.points}`,
      `Win Rate: ${pct(rec.winRate)}`,
    ];

    return { content: [{ type: 'text', text: lines.join('\n') }] };
  }
);

// ---------------------------------------------------------------------------
// Tool: head_to_head
// ---------------------------------------------------------------------------

server.registerTool(
  'head_to_head',
  {
    title: 'Head-to-Head Record',
    description: `Show all matches between two specific teams with a full summary.

Args:
  - team1: First team name
  - team2: Second team name
  - competition: Optional competition filter
  - season: Optional season year
  - limit: Max matches to list (default 20)

Returns: Full match list sorted newest-first, plus aggregate win/draw/loss counts and goal totals.`,
    inputSchema: z.object({
      team1: z.string().min(2).describe('First team'),
      team2: z.string().min(2).describe('Second team'),
      competition: z.string().optional().describe('Competition filter'),
      season: z.number().int().optional().describe('Season year'),
      limit: z.number().int().min(1).max(100).default(20).describe('Max matches to show'),
    }),
    annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
  },
  async ({ team1, team2, competition, season, limit }) => {
    const { matches } = getDatabase();
    const h2h = headToHead(matches, team1, team2, competition, season);

    if (h2h.matches.length === 0) {
      return {
        content: [{ type: 'text', text: `No matches found between "${team1}" and "${team2}".` }],
      };
    }

    const lines = [
      `## ${team1} vs ${team2}`,
      '',
      `Total matches: ${h2h.matches.length}`,
      `${team1}: ${h2h.team1Wins} wins | ${team2}: ${h2h.team2Wins} wins | Draws: ${h2h.draws}`,
      `Goals: ${team1} ${h2h.team1Goals} – ${h2h.team2Goals} ${team2}`,
      '',
      `### Recent Matches (showing up to ${limit}):`,
    ];

    for (const m of h2h.matches.slice(0, limit)) {
      lines.push(formatMatch(m));
    }

    if (h2h.matches.length > limit) {
      lines.push(`\n... ${h2h.matches.length - limit} more matches not shown.`);
    }

    return { content: [{ type: 'text', text: lines.join('\n') }] };
  }
);

// ---------------------------------------------------------------------------
// Tool: get_standings
// ---------------------------------------------------------------------------

server.registerTool(
  'get_standings',
  {
    title: 'Get Competition Standings',
    description: `Calculate league table standings for a competition and season.

Supported for Brasileirão Serie A (2003-2022) — uses novo_campeonato_brasileiro dataset for
2003-2011 and Brasileirao_Matches for 2012-2022. Copa do Brasil (2012-2021) standings are
calculated by match count since it's a cup (not a round-robin league).

Args:
  - competition: "brasileirao" | "copa brasil" | "libertadores" (required)
  - season: Year (required)
  - limit: Number of teams to show (default 20)

Returns: Sorted league table with points, W/D/L, goal difference.`,
    inputSchema: z.object({
      competition: z.string().describe('Competition: "brasileirao", "copa brasil", "libertadores"'),
      season: z.number().int().describe('Season year'),
      limit: z.number().int().min(1).max(40).default(20).describe('Number of teams to show'),
    }),
    annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
  },
  async ({ competition, season, limit }) => {
    const { matches } = getDatabase();
    const comp = resolveCompetition(competition);
    if (!comp) {
      return {
        content: [{ type: 'text', text: `Unknown competition: "${competition}". Try "brasileirao", "copa brasil", or "libertadores".` }],
      };
    }

    // For Brasileirão, prefer historico (2003-2019) or brasileirao (2012-2022) to avoid duplication
    let relevant: Match[];
    if (comp === 'Brasileirão Serie A') {
      if (season <= 2011) {
        relevant = matches.filter((m) => m.source === 'historico' && m.season === season);
      } else if (season <= 2019) {
        // Prefer brasileirao source for 2012-2019 (has state suffixes, cleaner)
        relevant = matches.filter((m) => m.source === 'brasileirao' && m.season === season);
        if (relevant.length === 0) {
          relevant = matches.filter((m) => m.source === 'historico' && m.season === season);
        }
      } else {
        relevant = matches.filter((m) => m.source === 'brasileirao' && m.season === season);
      }
    } else {
      relevant = matches.filter((m) => m.competition === comp && m.season === season);
    }

    if (relevant.length === 0) {
      return {
        content: [{ type: 'text', text: `No data found for ${comp} season ${season}.` }],
      };
    }

    const table = computeStandings(relevant);
    const shown = table.slice(0, limit);

    const lines = [
      `## ${comp} ${season} Standings (calculated from ${relevant.length} matches)`,
      '',
      'Pos | Team | Pts | W | D | L | GF | GA | GD | Win%',
      '--- | ---- | --- | - | - | - | -- | -- | -- | ----',
    ];

    shown.forEach((rec, i) => {
      const gd = rec.goalDiff >= 0 ? `+${rec.goalDiff}` : String(rec.goalDiff);
      lines.push(
        `${i + 1}.  | ${rec.team} | ${rec.points} | ${rec.wins} | ${rec.draws} | ${rec.losses} | ${rec.goalsFor} | ${rec.goalsAgainst} | ${gd} | ${pct(rec.winRate)}`
      );
    });

    if (table.length > limit) {
      lines.push(`\n... ${table.length - limit} more teams.`);
    }

    return { content: [{ type: 'text', text: lines.join('\n') }] };
  }
);

// ---------------------------------------------------------------------------
// Tool: search_players
// ---------------------------------------------------------------------------

server.registerTool(
  'search_players',
  {
    title: 'Search Players',
    description: `Search the FIFA player database (18,000+ players) by name, nationality, club, or position.

Args:
  - name: Partial player name (case-insensitive, accent-insensitive)
  - nationality: Country name (e.g. "Brazil", "Argentina")
  - club: Club name (partial match, e.g. "Flamengo", "Palmeiras")
  - position: Playing position (e.g. "GK", "ST", "CB", "CDM")
  - min_overall: Minimum FIFA overall rating (e.g. 80)
  - max_overall: Maximum FIFA overall rating
  - limit: Max results (default 20, max 100)
  - offset: Pagination offset (default 0)
  - sort_by: Sort field — "overall" | "potential" | "name" (default "overall")

Returns: Player list sorted by overall rating descending, with name, position, club, nationality,
overall/potential ratings, and key skill ratings.`,
    inputSchema: z.object({
      name: z.string().optional().describe('Partial player name'),
      nationality: z.string().optional().describe('Country (e.g. "Brazil")'),
      club: z.string().optional().describe('Club name (partial match)'),
      position: z.string().optional().describe('Position code (e.g. "GK", "ST", "CB")'),
      min_overall: z.number().int().min(0).max(99).optional().describe('Minimum overall rating'),
      max_overall: z.number().int().min(0).max(99).optional().describe('Maximum overall rating'),
      limit: z.number().int().min(1).max(100).default(20).describe('Max results'),
      offset: z.number().int().min(0).default(0).describe('Pagination offset'),
      sort_by: z.enum(['overall', 'potential', 'name']).default('overall').describe('Sort order'),
    }),
    annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
  },
  async ({ name, nationality, club, position, min_overall, max_overall, limit, offset, sort_by }) => {
    const { players } = getDatabase();
    const filtered = filterPlayers(players, {
      name,
      nationality,
      club,
      position,
      minOverall: min_overall,
      maxOverall: max_overall,
    });

    // Sort
    const sorted = [...filtered].sort((a, b) => {
      if (sort_by === 'name') return (a.name ?? '').localeCompare(b.name ?? '');
      if (sort_by === 'potential') return (b.potential ?? 0) - (a.potential ?? 0);
      return (b.overall ?? 0) - (a.overall ?? 0);
    });

    const total = sorted.length;
    const page = sorted.slice(offset, offset + limit);

    if (page.length === 0) {
      return { content: [{ type: 'text', text: 'No players found matching the given criteria.' }] };
    }

    const lines = [
      `## Player Search Results (${total} found, showing ${page.length})`,
      '',
    ];

    for (let i = 0; i < page.length; i++) {
      const p = page[i]!;
      const overall = p.overall !== undefined ? `OVR: ${p.overall}` : '';
      const potential = p.potential !== undefined ? `POT: ${p.potential}` : '';
      const age = p.age !== undefined ? `Age: ${p.age}` : '';
      const height = p.height ? `${p.height}` : '';
      const weight = p.weight ? `${p.weight}` : '';
      const physLine = [height, weight].filter(Boolean).join(', ');
      lines.push(
        `${offset + i + 1}. **${p.name}** | ${p.position ?? 'N/A'} | ${p.club ?? 'Free agent'} | ${p.nationality ?? 'Unknown'}`
      );
      lines.push(
        `   ${[overall, potential, age, physLine].filter(Boolean).join(' | ')}`
      );
    }

    if (total > offset + limit) {
      lines.push('');
      lines.push(`... ${total - offset - limit} more players. Use offset=${offset + limit} for next page.`);
    }

    return { content: [{ type: 'text', text: lines.join('\n') }] };
  }
);

// ---------------------------------------------------------------------------
// Tool: get_competition_stats
// ---------------------------------------------------------------------------

server.registerTool(
  'get_competition_stats',
  {
    title: 'Get Competition Statistics',
    description: `Compute aggregate statistics for a competition, including average goals,
home/away win rates, biggest victories, and team rankings.

Args:
  - competition: Competition filter (optional — omit for all competitions)
  - season: Season year (optional — omit for all seasons)
  - stat_type: "overview" | "biggest_wins" | "high_scoring" | "best_home" | "best_away" | "most_goals"
  - limit: Results to show for list-type stats (default 10)

Returns:
  - overview: Total matches, avg goals/match, home/away/draw rates
  - biggest_wins: Matches with largest goal margin
  - high_scoring: Most total goals in a single match
  - best_home: Teams with best home record
  - best_away: Teams with best away record
  - most_goals: Teams that scored the most goals`,
    inputSchema: z.object({
      competition: z.string().optional().describe('Competition filter (optional)'),
      season: z.number().int().optional().describe('Season year (optional)'),
      stat_type: z
        .enum(['overview', 'biggest_wins', 'high_scoring', 'best_home', 'best_away', 'most_goals'])
        .default('overview')
        .describe('Type of statistics to return'),
      limit: z.number().int().min(1).max(50).default(10).describe('Number of results for list types'),
    }),
    annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
  },
  async ({ competition, season, stat_type, limit }) => {
    const { matches } = getDatabase();

    let subset = matches;
    if (competition) {
      const comp = resolveCompetition(competition);
      if (comp) subset = subset.filter((m) => m.competition === comp);
    }
    if (season) {
      subset = subset.filter((m) => m.season === season);
    }

    if (subset.length === 0) {
      return { content: [{ type: 'text', text: 'No matches found for the given criteria.' }] };
    }

    const compLabel = competition ?? 'All competitions';
    const seasonLabel = season ? ` ${season}` : '';

    if (stat_type === 'overview') {
      const ov = competitionOverview(subset);
      const lines = [
        `## Statistics: ${compLabel}${seasonLabel}`,
        '',
        `Total Matches:        ${ov.totalMatches}`,
        `Total Goals:          ${ov.totalGoals}`,
        `Avg Goals / Match:    ${ov.avgGoalsPerMatch.toFixed(2)}`,
        `Home Wins:            ${ov.homeWins} (${pct(ov.homeWinRate)})`,
        `Away Wins:            ${ov.awayWins} (${pct(ov.awayWins / ov.totalMatches)})`,
        `Draws:                ${ov.draws} (${pct(ov.draws / ov.totalMatches)})`,
      ];
      return { content: [{ type: 'text', text: lines.join('\n') }] };
    }

    if (stat_type === 'biggest_wins') {
      const top = biggestWins(subset, limit);
      const lines = [`## Biggest Wins — ${compLabel}${seasonLabel}`, ''];
      top.forEach((m, i) => {
        const winner = m.homeGoals > m.awayGoals ? m.homeTeamNormalized : m.awayTeamNormalized;
        const margin = Math.abs(m.homeGoals - m.awayGoals);
        lines.push(`${i + 1}. ${formatMatch(m)} [margin: ${margin}]`);
      });
      return { content: [{ type: 'text', text: lines.join('\n') }] };
    }

    if (stat_type === 'high_scoring') {
      const top = highScoringMatches(subset, limit);
      const lines = [`## Highest-Scoring Matches — ${compLabel}${seasonLabel}`, ''];
      top.forEach((m, i) => {
        const total = m.homeGoals + m.awayGoals;
        lines.push(`${i + 1}. ${formatMatch(m)} [${total} goals]`);
      });
      return { content: [{ type: 'text', text: lines.join('\n') }] };
    }

    if (stat_type === 'best_home') {
      const ranked = rankTeams(subset, 'home_record', limit);
      const lines = [`## Best Home Records — ${compLabel}${seasonLabel}`, ''];
      ranked.forEach((r, i) => lines.push(formatRecord(r, i + 1)));
      return { content: [{ type: 'text', text: lines.join('\n') }] };
    }

    if (stat_type === 'best_away') {
      const ranked = rankTeams(subset, 'away_record', limit);
      const lines = [`## Best Away Records — ${compLabel}${seasonLabel}`, ''];
      ranked.forEach((r, i) => lines.push(formatRecord(r, i + 1)));
      return { content: [{ type: 'text', text: lines.join('\n') }] };
    }

    // most_goals
    const ranked = rankTeams(subset, 'goals_for', limit);
    const lines = [`## Most Goals Scored — ${compLabel}${seasonLabel}`, ''];
    ranked.forEach((r, i) => lines.push(`${i + 1}. ${r.team} – ${r.goalsFor} goals in ${r.matches} matches`));
    return { content: [{ type: 'text', text: lines.join('\n') }] };
  }
);

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  // Pre-load data on startup so the first tool call is fast
  getDatabase();

  const transport = new StdioServerTransport();
  await server.connect(transport);
  process.stderr.write('Brazilian Soccer MCP Server running on stdio.\n');
}

main().catch((err: unknown) => {
  process.stderr.write(`Fatal error: ${err instanceof Error ? err.message : String(err)}\n`);
  process.exit(1);
});
