/**
 * MCP server exposing Brazilian soccer tools over stdio.
 *
 * Registers one tool per query capability from the spec:
 *   - search_matches        (match queries by team/opponent/competition/season/date)
 *   - head_to_head          (two-team comparison)
 *   - team_stats            (win/loss/draw/goals, optionally venue-restricted)
 *   - search_players        (FIFA player search)
 *   - top_players           (top-N by rating with filters)
 *   - standings             (computed standings for a competition+season)
 *   - champion              (winner of a competition+season)
 *   - relegated             (bottom-N of a competition+season)
 *   - competition_stats     (aggregate goals / home-away rates)
 *   - biggest_wins          (largest goal-difference victories)
 *   - list_competitions     (competitions present in dataset)
 *   - list_teams            (distinct team names)
 *   - list_seasons          (seasons present, optionally for a competition)
 *
 * The server lazily loads the dataset on first tool call and caches it for
 * the lifetime of the process.
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import type { Competition, Dataset, Match } from './types.js';
import { loadDataset, resolveDataDir } from './loader.js';
import * as Q from './query.js';
import * as F from './format.js';

const COMPETITIONS: Competition[] = [
  'Brasileirao',
  'Copa do Brasil',
  'Libertadores',
  'Historical Brasileirao',
  'BR-Football',
];

let _dataset: Dataset | null = null;

/** Lazily load and cache the dataset. */
export function getDataset(): Dataset {
  if (!_dataset) {
    _dataset = loadDataset(resolveDataDir());
  }
  return _dataset;
}

/** Reset the cached dataset (used by tests). */
export function resetDataset(): void {
  _dataset = null;
}

/** Inject a dataset (used by tests). */
export function setDataset(ds: Dataset): void {
  _dataset = ds;
}

const CompetitionSchema = z.enum([
  'Brasileirao',
  'Copa do Brasil',
  'Libertadores',
  'Historical Brasileirao',
  'BR-Football',
]);

/** Build a configured McpServer with all tools registered. */
export function buildServer(dataset: Dataset = getDataset()): McpServer {
  const server = new McpServer(
    { name: 'brazilian-soccer-mcp', version: '1.0.0' },
    { capabilities: { tools: {} } },
  );

  const matches = dataset.matches;
  const players = dataset.players;

  const json = (obj: unknown) => JSON.stringify(obj, null, 2);
  const text = (s: string, structured?: unknown) => ({
    content: [
      { type: 'text' as const, text: s },
      ...(structured
        ? [{ type: 'text' as const, text: `\n--- JSON ---\n${json(structured)}` }]
        : []),
    ],
  });

  server.tool(
    'search_matches',
    'Search matches by team, opponent, competition, season, and/or date range.',
    {
      team: z.string().optional().describe('Team name (home or away).'),
      opponent: z.string().optional().describe('Opponent team name.'),
      home_team: z.string().optional(),
      away_team: z.string().optional(),
      competition: CompetitionSchema.optional(),
      season: z.number().int().optional(),
      from_date: z
        .string()
        .optional()
        .describe('ISO date YYYY-MM-DD inclusive.'),
      to_date: z.string().optional(),
      limit: z.number().int().min(0).max(500).default(50),
    },
    (args) => {
      const result = Q.filterMatches(matches, {
        team: args.team,
        opponent: args.opponent,
        homeTeam: args.home_team,
        awayTeam: args.away_team,
        competition: args.competition as Competition | undefined,
        season: args.season,
        fromDate: args.from_date,
        toDate: args.to_date,
        limit: args.limit,
      });
      return text(F.formatMatches(result, 'Matches:'), result);
    },
  );

  server.tool(
    'head_to_head',
    'Head-to-head record between two teams.',
    {
      team_a: z.string(),
      team_b: z.string(),
    },
    (args) => {
      const h2h = Q.headToHead(matches, args.team_a, args.team_b);
      return text(F.formatHeadToHead(h2h), h2h);
    },
  );

  server.tool(
    'team_stats',
    "Team statistics (W/D/L, goals, points) for a season/competition, optionally home-only or away-only.",
    {
      team: z.string(),
      competition: CompetitionSchema.optional(),
      season: z.number().int().optional(),
      venue: z.enum(['any', 'home', 'away']).default('any'),
    },
    (args) => {
      const scoped = Q.filterMatches(matches, {
        team: args.team,
        competition: args.competition as Competition | undefined,
        season: args.season,
      });
      const rec =
        args.venue === 'home'
          ? Q.teamVenueRecord(scoped, args.team, 'home')
          : args.venue === 'away'
            ? Q.teamVenueRecord(scoped, args.team, 'away')
            : Q.teamRecord(scoped, args.team);
      const label = `${args.team} ${args.venue !== 'any' ? args.venue : ''} record${
        args.season ? ` ${args.season}` : ''
      }${args.competition ? ` ${args.competition}` : ''}:`;
      return text(F.formatTeamRecord(rec, label), rec);
    },
  );

  server.tool(
    'search_players',
    'Search FIFA player database by name substring.',
    { name: z.string(), limit: z.number().int().min(1).max(200).default(25) },
    (args) => {
      const result = Q.searchPlayers(players, args.name).slice(0, args.limit);
      return text(F.formatPlayers(result, `Players matching "${args.name}":`), result);
    },
  );

  server.tool(
    'top_players',
    'Top-N players by FIFA overall rating, optionally filtered by nationality, club, or position.',
    {
      limit: z.number().int().min(1).max(200).default(10),
      nationality: z.string().optional(),
      club: z.string().optional(),
      position: z.string().optional(),
    },
    (args) => {
      const result = Q.topPlayers(players, args);
      return text(
        F.formatPlayers(result, `Top ${args.limit} players:`),
        result,
      );
    },
  );

  server.tool(
    'standings',
    'Computed standings (from match results) for a competition and season.',
    {
      competition: CompetitionSchema,
      season: z.number().int().optional(),
    },
    (args) => {
      const table = Q.standings(matches, args.competition, args.season);
      return text(
        F.formatStandings(
          table,
          `${args.season ?? 'All-time'} ${args.competition} Standings:`,
        ),
        table,
      );
    },
  );

  server.tool(
    'champion',
    'Champion (top of standings) for a competition+season.',
    {
      competition: CompetitionSchema,
      season: z.number().int(),
    },
    (args) => {
      const champ = Q.champion(matches, args.competition, args.season);
      return text(
        champ
          ? `${args.season} ${args.competition} champion: ${champ.team} (${champ.points} pts, ${champ.wins}W ${champ.draws}D ${champ.losses}L)`
          : `No champion data for ${args.competition} ${args.season}.`,
        champ,
      );
    },
  );

  server.tool(
    'relegated',
    'Relegated teams (bottom N of standings) for a competition+season.',
    {
      competition: CompetitionSchema,
      season: z.number().int(),
      bottom_n: z.number().int().min(1).max(10).default(4),
    },
    (args) => {
      const teams = Q.relegated(matches, args.competition, args.season, args.bottom_n);
      return text(
        F.formatStandings(
          teams,
          `${args.season} ${args.competition} Relegated (bottom ${args.bottom_n}):`,
        ),
        teams,
      );
    },
  );

  server.tool(
    'competition_stats',
    'Aggregate statistics (avg goals, home/away win rates) for a competition+season.',
    {
      competition: CompetitionSchema.optional(),
      season: z.number().int().optional(),
    },
    (args) => {
      const scoped = Q.filterMatches(matches, {
        competition: args.competition as Competition | undefined,
        season: args.season,
      });
      return text(
        F.formatStats(
          scoped,
          `${args.season ?? 'All-time'} ${args.competition ?? 'all competitions'} stats:`,
        ),
        {
          avgGoals: Q.averageGoalsPerMatch(scoped),
          rates: Q.homeAwayRates(scoped),
        },
      );
    },
  );

  server.tool(
    'biggest_wins',
    'Largest goal-difference victories across a competition+season.',
    {
      competition: CompetitionSchema.optional(),
      season: z.number().int().optional(),
      limit: z.number().int().min(1).max(50).default(10),
    },
    (args) => {
      const scoped = Q.filterMatches(matches, {
        competition: args.competition as Competition | undefined,
        season: args.season,
      });
      const wins = Q.biggestWins(scoped, args.limit);
      return text(F.formatMatches(wins, 'Biggest victories:'), wins);
    },
  );

  server.tool('list_competitions', 'List all competitions present in the dataset.', {}, () => {
    return text(
      `Competitions:\n${Q.allCompetitions(matches).map((c) => `- ${c}`).join('\n')}`,
      { competitions: Q.allCompetitions(matches) },
    );
  });

  server.tool(
    'list_teams',
    'List distinct team names. Optional substring filter.',
    { filter: z.string().optional(), limit: z.number().int().min(1).max(2000).default(500) },
    (args) => {
      let teams = Q.allTeams(matches);
      if (args.filter) {
        const q = args.filter.toLowerCase();
        teams = teams.filter((t) => t.toLowerCase().includes(q));
      }
      teams = teams.slice(0, args.limit);
      return text(`Teams:\n${teams.map((t) => `- ${t}`).join('\n')}`, { teams });
    },
  );

  server.tool(
    'list_seasons',
    'List seasons present in the dataset, optionally for a competition.',
    { competition: CompetitionSchema.optional() },
    (args) => {
      const seasons = Q.seasonsFor(matches, args.competition as Competition | undefined);
      return text(
        `Seasons${args.competition ? ` for ${args.competition}` : ''}:\n${seasons.join(', ')}`,
        { seasons },
      );
    },
  );

  return server;
}

/** Run the MCP server over stdio (entry point). */
export async function runServer(): Promise<void> {
  const server = buildServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

export { COMPETITIONS };
export type { Match };
