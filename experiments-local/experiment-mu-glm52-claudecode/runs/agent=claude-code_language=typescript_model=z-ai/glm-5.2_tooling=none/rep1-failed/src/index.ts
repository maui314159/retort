#!/usr/bin/env node
/**
 * Brazilian Soccer MCP Server — entry point
 * =========================================
 * Context block:
 *   Wires the query engine (`src/query.ts`) to the Model Context Protocol over
 *   stdio using the low-level `Server` API with plain JSON-Schema tool
 *   definitions. (The high-level `McpServer.tool()` overload triggers
 *   "excessively deep" zod type instantiation on larger schemas; plain JSON
 *   Schema avoids that entirely and keeps input validation identical.)
 *
 *   Eleven tools are exposed so an LLM can answer natural-language questions
 *   across the five capability categories in the task spec (matches, teams,
 *   players, competitions, statistics). Each tool returns a plain-text answer
 *   block shaped like the spec's "Example answer format" snippets.
 *
 *   Run with:  node dist/index.js     (after `npm run build`)
 *   The server loads all six Kaggle CSV files lazily on the first tool call so
 *   that cold start cost is paid only when needed.
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import type { Tool } from '@modelcontextprotocol/sdk/types.js';

import { loadData } from './loader.js';
import {
  averageGoals,
  biggestWins,
  canonicalMatches,
  competitionSummary,
  headToHead,
  homeAwaySplit,
  resolveTeams,
  searchMatches,
  searchPlayers,
  standings,
  teamStatistics,
  topPlayers,
} from './query.js';
import {
  formatMatch,
  formatPlayer,
  formatStanding,
  formatTeamRecord,
} from './format.js';

/** Lazy, canonicalized data accessor — startup is instant and parse happens once. */
let data: { matches: ReturnType<typeof canonicalMatches>; players: ReturnType<typeof loadData>['players'] } | null = null;
function db() {
  if (!data) {
    const raw = loadData();
    data = { matches: canonicalMatches(raw.matches), players: raw.players };
  }
  return data;
}

/** Tool handler signature: receives the validated args object. */
type Handler = (args: Record<string, unknown>) => string;

/** Minimal JSON-Schema shape matching MCP's Tool.inputSchema (object form). */
interface ToolInputSchema {
  type: 'object';
  properties?: Record<string, object>;
  required?: string[];
  // Index signature to satisfy MCP's ZodObject-catchall-unknown input schema type.
  [key: string]: unknown;
}

/** Build a JSON-Schema object type from a field map. */
function objectSchema(
  properties: Record<string, object>,
  required?: string[],
): ToolInputSchema {
  return {
    type: 'object',
    properties,
    required: required ?? [],
  };
}

interface ToolDef {
  name: string;
  description: string;
  inputSchema: ToolInputSchema;
  handler: Handler;
}

const TOOLS: ToolDef[] = [
  {
    name: 'search_matches',
    description:
      'Search Brazilian soccer matches by team, opponent, competition, season, or date range. Returns a list of matches with date, teams, score, and competition.',
    inputSchema: objectSchema({
      team: { type: 'string', description: 'Team name (e.g. "Flamengo", "Palmeiras-SP").' },
      opponent: { type: 'string', description: 'Opponent team name; only matches between team and opponent are returned.' },
      competition: { type: 'string', description: 'Competition: Brasileirão, Copa do Brasil, Libertadores, Série B, Série C.' },
      season: { type: 'integer', description: 'Season year, e.g. 2023.' },
      from_date: { type: 'string', description: 'ISO date YYYY-MM-DD lower bound (inclusive).' },
      to_date: { type: 'string', description: 'ISO date YYYY-MM-DD upper bound (inclusive).' },
      limit: { type: 'integer', description: 'Max matches to return (default 20).' },
    }),
    handler: (a) => {
      const matches = searchMatches(db().matches, {
        team: a.team as string | undefined,
        opponent: a.opponent as string | undefined,
        competition: a.competition as string | undefined,
        season: a.season as number | undefined,
        fromDate: a.from_date as string | undefined,
        toDate: a.to_date as string | undefined,
        limit: (a.limit as number | undefined) ?? 20,
      });
      if (matches.length === 0) return 'No matches found for the given criteria.';
      const lines = matches.map(formatMatch);
      lines.push(`\n(${matches.length} match${matches.length === 1 ? '' : 'es'} in result set)`);
      return lines.join('\n');
    },
  },
  {
    name: 'head_to_head',
    description:
      'Compare two teams head-to-head across all datasets. Returns each match and a win/draw/loss summary.',
    inputSchema: objectSchema({
      team_a: { type: 'string', description: 'First team, e.g. "Flamengo".' },
      team_b: { type: 'string', description: 'Second team, e.g. "Fluminense".' },
      limit: { type: 'integer', description: 'Max matches to list (default 25).' },
    }, ['team_a', 'team_b']),
    handler: (a) => {
      const teamA = a.team_a as string;
      const teamB = a.team_b as string;
      const h = headToHead(db().matches, teamA, teamB);
      if (h.matches.length === 0) return `No matches found between ${teamA} and ${teamB}.`;
      const lines = h.matches.slice(0, (a.limit as number | undefined) ?? 25).map(formatMatch);
      lines.push(
        `\nHead-to-head in dataset: ${teamA} ${h.aWins} wins, ${teamB} ${h.bWins} wins, ${h.draws} draws (${h.matches.length} matches total)`,
      );
      return lines.join('\n');
    },
  },
  {
    name: 'team_statistics',
    description:
      "Compute win/draw/loss, goals for/against, points, and win rate for a team, optionally filtered by season, competition, or venue (home/away/all).",
    inputSchema: objectSchema({
      team: { type: 'string', description: 'Team name, e.g. "Corinthians".' },
      season: { type: 'integer', description: 'Season year, e.g. 2022.' },
      competition: { type: 'string', description: 'Competition filter.' },
      venue: { type: 'string', enum: ['home', 'away', 'all'], description: 'Venue filter (default all).' },
    }, ['team']),
    handler: (a) => {
      const team = a.team as string;
      const venue = a.venue as 'home' | 'away' | 'all' | undefined;
      const t = teamStatistics(db().matches, {
        team,
        season: a.season as number | undefined,
        competition: a.competition as string | undefined,
        venue,
      });
      if (t.played === 0) return `No matches found for ${team} with the given filters.`;
      const season = a.season as number | undefined;
      const competition = a.competition as string | undefined;
      const label = `${team} record${season ? ` (${season})` : ''}${competition ? ` ${competition}` : ''}${venue && venue !== 'all' ? ` ${venue}` : ''}`;
      return formatTeamRecord(t, label);
    },
  },
  {
    name: 'competition_standings',
    description:
      'Calculate competition standings for a season from match results (3 points for a win, 1 for a draw). Works best with Brasileirão seasons.',
    inputSchema: objectSchema({
      competition: { type: 'string', description: 'Competition, e.g. "Brasileirão".' },
      season: { type: 'integer', description: 'Season year, e.g. 2019.' },
      limit: { type: 'integer', description: 'Max rows (default 20).' },
    }, ['competition', 'season']),
    handler: (a) => {
      const competition = a.competition as string;
      const season = a.season as number;
      const table = standings(db().matches, {
        competition,
        season,
        limit: (a.limit as number | undefined) ?? 20,
      });
      if (table.length === 0) return `No standings data for ${competition} ${season}.`;
      const lines = [
        `${season} ${competition} Standings (calculated from matches):`,
        ...table.map((t, i) => formatStanding(t, i + 1, i === 0)),
      ];
      return lines.join('\n');
    },
  },
  {
    name: 'competition_summary',
    description: 'List all available competitions with their seasons and match counts.',
    inputSchema: objectSchema({}),
    handler: () => {
      const summary = competitionSummary(db().matches);
      const lines: string[] = ['Available competitions:'];
      for (const c of summary) {
        lines.push(`- ${c.competition}: ${c.totalMatches} matches`);
        const seasonsList = c.seasons.map((s) => `${s.season} (${s.matches})`).join(', ');
        lines.push(`    seasons: ${seasonsList}`);
      }
      return lines.join('\n');
    },
  },
  {
    name: 'average_goals',
    description:
      'Average goals per match and home-win rate, optionally filtered by competition and/or season.',
    inputSchema: objectSchema({
      competition: { type: 'string' },
      season: { type: 'integer' },
    }),
    handler: (a) => {
      const competition = a.competition as string | undefined;
      const season = a.season as number | undefined;
      const r = averageGoals(db().matches, { competition, season });
      if (r.matches === 0) return 'No matches found for the given filters.';
      const label = `Average goals${competition ? ` in ${competition}` : ''}${season ? ` ${season}` : ''}`;
      return [
        `${label}:`,
        `- Matches: ${r.matches}`,
        `- Total goals: ${r.totalGoals}`,
        `- Average goals per match: ${r.avgPerMatch}`,
        `- Home win rate: ${r.homeWinRate}%`,
      ].join('\n');
    },
  },
  {
    name: 'biggest_wins',
    description:
      'Biggest victories by goal difference, optionally filtered by competition and/or season.',
    inputSchema: objectSchema({
      competition: { type: 'string' },
      season: { type: 'integer' },
      limit: { type: 'integer', description: 'Max results (default 10).' },
    }),
    handler: (a) => {
      const wins = biggestWins(db().matches, {
        competition: a.competition as string | undefined,
        season: a.season as number | undefined,
        limit: (a.limit as number | undefined) ?? 10,
      });
      if (wins.length === 0) return 'No matches found for the given filters.';
      return ['Biggest victories (provided data):', ...wins.map(formatMatch)].join('\n');
    },
  },
  {
    name: 'home_away_split',
    description: 'Home-win, away-win, and draw split for a competition and/or season.',
    inputSchema: objectSchema({
      competition: { type: 'string' },
      season: { type: 'integer' },
    }),
    handler: (a) => {
      const r = homeAwaySplit(db().matches, {
        competition: a.competition as string | undefined,
        season: a.season as number | undefined,
      });
      if (r.total === 0) return 'No matches found for the given filters.';
      const pct = (n: number) => ((n / r.total) * 100).toFixed(1);
      return [
        `Home vs away split (${r.total} matches):`,
        `- Home wins: ${r.homeWins} (${pct(r.homeWins)}%)`,
        `- Away wins: ${r.awayWins} (${pct(r.awayWins)}%)`,
        `- Draws: ${r.draws} (${pct(r.draws)}%)`,
      ].join('\n');
    },
  },
  {
    name: 'search_players',
    description:
      'Search the FIFA player database by name, nationality, club, position, and/or minimum overall rating. Useful for "Brazilian players", "forwards at São Paulo", "Gabriel Barbosa".',
    inputSchema: objectSchema({
      name: { type: 'string' },
      nationality: { type: 'string', description: 'e.g. "Brazil".' },
      club: { type: 'string' },
      position: { type: 'string', description: 'e.g. "ST", "GK", "LW".' },
      min_overall: { type: 'integer', description: 'Minimum overall rating.' },
      limit: { type: 'integer', description: 'Max results (default 20).' },
    }),
    handler: (a) => {
      const players = searchPlayers(db().players, {
        name: a.name as string | undefined,
        nationality: a.nationality as string | undefined,
        club: a.club as string | undefined,
        position: a.position as string | undefined,
        minOverall: a.min_overall as number | undefined,
        limit: (a.limit as number | undefined) ?? 20,
      });
      if (players.length === 0) return 'No players found for the given criteria.';
      return players.map((p) => formatPlayer(p)).join('\n');
    },
  },
  {
    name: 'top_players',
    description:
      'Top-rated players (by FIFA Overall), optionally filtered by nationality, club, or position. Returns ranked list.',
    inputSchema: objectSchema({
      nationality: { type: 'string' },
      club: { type: 'string' },
      position: { type: 'string' },
      limit: { type: 'integer', description: 'Max results (default 10).' },
    }),
    handler: (a) => {
      const players = topPlayers(db().players, {
        nationality: a.nationality as string | undefined,
        club: a.club as string | undefined,
        position: a.position as string | undefined,
        limit: (a.limit as number | undefined) ?? 10,
      });
      if (players.length === 0) return 'No players found for the given criteria.';
      return players.map((p, i) => formatPlayer(p, i + 1)).join('\n');
    },
  },
  {
    name: 'resolve_teams',
    description:
      'Resolve a team name to the distinct teams present in the datasets (handles "Palmeiras-SP" vs "Palmeiras"). Use this when a team name is ambiguous before calling other tools.',
    inputSchema: objectSchema({
      query: { type: 'string', description: 'Team name or fragment, e.g. "atletico", "São Paulo".' },
    }, ['query']),
    handler: (a) => {
      const query = a.query as string;
      const teams = resolveTeams(db().matches, query);
      if (teams.length === 0) return `No teams matching "${query}".`;
      const lines = [`Teams matching "${query}":`];
      for (const t of teams) {
        lines.push(`- ${t.display}${t.state ? ` (${t.state})` : ''}`);
      }
      return lines.join('\n');
    },
  },
];

const toolList: Tool[] = TOOLS.map((t) => ({
  name: t.name,
  description: t.description,
  inputSchema: t.inputSchema,
}));

const server = new Server(
  { name: 'brazilian-soccer-mcp', version: '1.0.0' },
  { capabilities: { tools: {} } },
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: toolList,
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const name = request.params.name;
  const args = (request.params.arguments ?? {}) as Record<string, unknown>;
  const def = TOOLS.find((t) => t.name === name);
  if (!def) {
    return {
      content: [{ type: 'text' as const, text: `Unknown tool: ${name}` }],
      isError: true,
    };
  }
  try {
    const text = def.handler(args);
    return { content: [{ type: 'text' as const, text }] };
  } catch (err) {
    return {
      content: [{ type: 'text' as const, text: `Error: ${(err as Error).message}` }],
      isError: true,
    };
  }
});

async function main(): Promise<void> {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Brazilian Soccer MCP Server running on stdio');
}

main().catch((error) => {
  console.error('Fatal error in main():', error);
  process.exit(1);
});
