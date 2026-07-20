/**
 * MCP server definition: exposes the Brazilian soccer dataset as a set of
 * query tools (matches, teams, players, competitions, statistics).
 */
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { DatasetStore, Match, TeamIdentity } from './types.js';
import {
  STANDINGS_COMPETITIONS,
  biggestWins,
  brazilianPlayersByClub,
  clubPlayerSummary,
  computeStandings,
  findPlayer,
  findTeams,
  headToHead,
  listCompetitions,
  matchStatistics,
  normalizeCompetition,
  resolveTeam,
  searchMatches,
  searchPlayers,
  teamCompetitions,
  teamStats,
  topScoringTeams,
  byDateDesc,
} from './queries.js';
import { formatMatchList, formatRecord, num, pct } from './format.js';

type TextResult = { content: { type: 'text'; text: string }[]; isError?: boolean };

const text = (t: string): TextResult => ({ content: [{ type: 'text', text: t }] });
const err = (t: string): TextResult => ({
  content: [{ type: 'text', text: t }],
  isError: true,
});

const COMPETITION_NAMES = [
  'Brasileirão Série A',
  'Brasileirão Série B',
  'Brasileirão Série C',
  'Copa do Brasil',
  'Copa Libertadores',
];

export function createServer(store: DatasetStore): McpServer {
  const server = new McpServer(
    { name: 'brazilian-soccer-mcp', version: '1.0.0' },
    { capabilities: { tools: {}, resources: {} } },
  );

  /** Resolve a competition string or produce an error result. */
  const competitionOrError = (
    raw?: string,
  ): { competition?: string; error?: TextResult } => {
    if (!raw) return {};
    const c = normalizeCompetition(raw);
    if (!c) {
      return {
        error: err(
          `Unknown competition "${raw}". Valid values: ${COMPETITION_NAMES.join(', ')}.`,
        ),
      };
    }
    return { competition: c };
  };

  /** Resolve a team string, building a helpful error/ambiguity note. */
  const teamOrError = (
    raw: string,
  ): { team?: TeamIdentity; note?: string; error?: TextResult } => {
    const { team, alternatives } = resolveTeam(store, raw);
    if (!team) {
      return {
        error: err(
          `Team "${raw}" not found in the dataset. Use the find_teams tool to list similar names.`,
        ),
      };
    }
    let note: string | undefined;
    if (alternatives.length > 0) {
      const names = alternatives
        .slice(0, 3)
        .map((t) => t.displayName)
        .join(', ');
      note = `Note: "${raw}" also matches ${names}; showing results for ${team.displayName}. Specify a state suffix (e.g. "Botafogo-PB") to pick another.`;
    }
    return { team, note };
  };

  const withNote = (body: string, note?: string) =>
    text(note ? `${note}\n\n${body}` : body);

  // ------------------------------------------------------------------
  // Match queries
  // ------------------------------------------------------------------

  server.registerTool(
    'search_matches',
    {
      title: 'Search matches',
      description:
        'Search soccer matches by team, opponent, competition, season or date range. ' +
        'Covers Brasileirão Série A/B/C, Copa do Brasil and Copa Libertadores. ' +
        'Team names may be given with or without state suffix or accents (e.g. "Flamengo", "Gremio", "São Paulo").',
      inputSchema: {
        team: z.string().optional().describe('Team name (matches home and away games)'),
        opponent: z.string().optional().describe('Opponent team name; combined with team for head-to-head fixtures'),
        competition: z.string().optional().describe('Competition name, e.g. "Serie A", "Copa do Brasil", "Libertadores"'),
        season: z.number().int().optional().describe('Season year, e.g. 2023'),
        dateFrom: z.string().optional().describe('ISO date yyyy-mm-dd lower bound'),
        dateTo: z.string().optional().describe('ISO date yyyy-mm-dd upper bound'),
        includeUnplayed: z.boolean().optional().describe('Include scheduled/cancelled matches without scores (default false)'),
        newestFirst: z.boolean().optional().describe('Sort newest first (default false = oldest first)'),
        limit: z.number().int().min(1).max(200).optional().describe('Max matches to return (default 25)'),
      },
    },
    async (args) => {
      const { competition, error: compErr } = competitionOrError(args.competition);
      if (compErr) return compErr;
      let team: TeamIdentity | undefined;
      let opponent: TeamIdentity | undefined;
      let note: string | undefined;
      if (args.team) {
        const r = teamOrError(args.team);
        if (r.error) return r.error;
        team = r.team;
        note = r.note;
      }
      if (args.opponent) {
        const r = teamOrError(args.opponent);
        if (r.error) return r.error;
        opponent = r.team;
        note = note ?? r.note;
      }
      let matches = searchMatches(store, {
        team,
        opponent,
        competition,
        season: args.season,
        dateFrom: args.dateFrom,
        dateTo: args.dateTo,
        playedOnly: !args.includeUnplayed,
      });
      matches = matches.sort(args.newestFirst ? byDateDesc : (a, b) => (a.date ?? '').localeCompare(b.date ?? ''));
      const limit = args.limit ?? 25;
      if (matches.length === 0) return withNote('No matches found for the given criteria.', note);
      const header = `${matches.length} match(es) found${matches.length > limit ? `, showing first ${limit}` : ''}:`;
      return withNote(`${header}\n${formatMatchList(matches, limit)}`, note);
    },
  );

  server.registerTool(
    'head_to_head',
    {
      title: 'Head-to-head record',
      description:
        'All matches between two teams plus the aggregate win/draw/loss record, ' +
        'e.g. "Flamengo vs Fluminense".',
      inputSchema: {
        teamA: z.string().describe('First team name'),
        teamB: z.string().describe('Second team name'),
        competition: z.string().optional().describe('Restrict to a competition'),
        season: z.number().int().optional().describe('Restrict to a season'),
        limit: z.number().int().min(1).max(100).optional().describe('Max matches to list (default 20)'),
      },
    },
    async (args) => {
      const { competition, error: compErr } = competitionOrError(args.competition);
      if (compErr) return compErr;
      const ra = teamOrError(args.teamA);
      if (ra.error) return ra.error;
      const rb = teamOrError(args.teamB);
      if (rb.error) return rb.error;
      const h2h = headToHead(store, ra.team!, rb.team!, {
        competition,
        season: args.season,
      });
      const scope = [competition, args.season].filter(Boolean).join(' ');
      const title = `${ra.team!.displayName} vs ${rb.team!.displayName}${scope ? ` (${scope})` : ''}:`;
      if (h2h.matches.length === 0) return text(`${title}\nNo matches found in dataset.`);
      const list = formatMatchList(h2h.matches, args.limit ?? 20);
      const summary =
        `Head-to-head in dataset: ${ra.team!.displayName} ${h2h.winsA} wins, ` +
        `${rb.team!.displayName} ${h2h.winsB} wins, ${h2h.draws} draws ` +
        `(goals ${h2h.goalsA}-${h2h.goalsB})`;
      return text([title, list, '', summary].join('\n'));
    },
  );

  // ------------------------------------------------------------------
  // Team queries
  // ------------------------------------------------------------------

  server.registerTool(
    'team_stats',
    {
      title: 'Team statistics',
      description:
        'Win/draw/loss record, goals scored/conceded and win rate for a team, ' +
        'optionally filtered by season, competition and venue (home/away). ' +
        'Example: "Corinthians home record in 2022".',
      inputSchema: {
        team: z.string().describe('Team name'),
        season: z.number().int().optional().describe('Season year'),
        competition: z.string().optional().describe('Competition name'),
        venue: z.enum(['home', 'away', 'all']).optional().describe('Filter by venue (default all)'),
      },
    },
    async (args) => {
      const { competition, error: compErr } = competitionOrError(args.competition);
      if (compErr) return compErr;
      const { team, note, error } = teamOrError(args.team);
      if (error) return error;
      const { record, home, away } = teamStats(store, team!, {
        season: args.season,
        competition,
        venue: args.venue ?? 'all',
      });
      const scope = [
        args.venue && args.venue !== 'all' ? args.venue : undefined,
        args.season,
        competition,
      ].filter(Boolean).join(' ');
      const lines = [
        `${team!.displayName} record${scope ? ` (${scope})` : ''}:`,
        formatRecord(record),
      ];
      if (!args.venue || args.venue === 'all') {
        lines.push('', `Home: ${home.wins}W ${home.draws}D ${home.losses}L (GF ${home.goalsFor}, GA ${home.goalsAgainst}, ${pct(home.matches ? home.wins / home.matches : 0)} wins)`);
        lines.push(`Away: ${away.wins}W ${away.draws}D ${away.losses}L (GF ${away.goalsFor}, GA ${away.goalsAgainst}, ${pct(away.matches ? away.wins / away.matches : 0)} wins)`);
      }
      return withNote(lines.join('\n'), note);
    },
  );

  server.registerTool(
    'compare_teams',
    {
      title: 'Compare two teams',
      description:
        'Head-to-head record plus season/competition statistics for two teams side by side.',
      inputSchema: {
        teamA: z.string().describe('First team name'),
        teamB: z.string().describe('Second team name'),
        season: z.number().int().optional().describe('Season year filter for the stats'),
        competition: z.string().optional().describe('Competition filter for the stats'),
      },
    },
    async (args) => {
      const { competition, error: compErr } = competitionOrError(args.competition);
      if (compErr) return compErr;
      const ra = teamOrError(args.teamA);
      if (ra.error) return ra.error;
      const rb = teamOrError(args.teamB);
      if (rb.error) return rb.error;
      const h2h = headToHead(store, ra.team!, rb.team!, { competition, season: args.season });
      const sa = teamStats(store, ra.team!, { competition, season: args.season });
      const sb = teamStats(store, rb.team!, { competition, season: args.season });
      const scope = [args.season, competition].filter(Boolean).join(' ');
      const lines = [
        `${ra.team!.displayName} vs ${rb.team!.displayName}${scope ? ` — ${scope}` : ''}:`,
        '',
        `${ra.team!.displayName}: ${sa.record.wins}W ${sa.record.draws}D ${sa.record.losses}L in ${sa.record.matches} matches, GF ${sa.record.goalsFor} GA ${sa.record.goalsAgainst}`,
        `${rb.team!.displayName}: ${sb.record.wins}W ${sb.record.draws}D ${sb.record.losses}L in ${sb.record.matches} matches, GF ${sb.record.goalsFor} GA ${sb.record.goalsAgainst}`,
        '',
        `Direct encounters (${h2h.matches.length}): ${ra.team!.displayName} ${h2h.winsA} wins, ${rb.team!.displayName} ${h2h.winsB} wins, ${h2h.draws} draws (goals ${h2h.goalsA}-${h2h.goalsB})`,
      ];
      if (h2h.matches.length > 0) {
        lines.push('', formatMatchList(h2h.matches, 10));
      }
      return text(lines.join('\n'));
    },
  );

  server.registerTool(
    'team_competitions',
    {
      title: 'Competitions of a team',
      description:
        'List every competition (with seasons and match counts) a team has played in the dataset. ' +
        'Example: "What competitions has Palmeiras played in?"',
      inputSchema: {
        team: z.string().describe('Team name'),
      },
    },
    async (args) => {
      const { team, note, error } = teamOrError(args.team);
      if (error) return error;
      const info = teamCompetitions(store, team!);
      const lines = info.competitions.map(
        (c) =>
          `- ${c.competition}: ${c.matches} matches` +
          (c.seasons.length
            ? `, seasons ${c.seasons[0]}-${c.seasons[c.seasons.length - 1]} (${c.seasons.length} seasons)`
            : ''),
      );
      return withNote(
        [`${team!.displayName} competitions in dataset:`, ...lines].join('\n'),
        note,
      );
    },
  );

  server.registerTool(
    'find_teams',
    {
      title: 'Find teams by name',
      description:
        'Disambiguation helper: list team identities matching a name, including ' +
        'state variants (e.g. "Botafogo" -> RJ/PB/SP) and known name variants.',
      inputSchema: {
        query: z.string().describe('Name (or part of a name) to search for'),
      },
    },
    async (args) => {
      const found = findTeams(store, args.query).slice(0, 15);
      if (found.length === 0) return text(`No teams matching "${args.query}".`);
      const lines = found.map(
        (t) =>
          `- ${t.displayName} [${t.key}] — ${t.matchCount} matches; also written as: ${[...t.variants].slice(0, 6).join(', ')}`,
      );
      return text([`Teams matching "${args.query}":`, ...lines].join('\n'));
    },
  );

  // ------------------------------------------------------------------
  // Competition queries
  // ------------------------------------------------------------------

  server.registerTool(
    'standings',
    {
      title: 'League standings',
      description:
        'Calculate the final league table (points, W/D/L, goals) for a Brasileirão ' +
        'division and season from match results. Marks the champion and relegation zone. ' +
        'Example: "Who won the 2019 Brasileirão?" -> standings(competition="Serie A", season=2019).',
      inputSchema: {
        competition: z.string().describe('"Serie A", "Serie B" or "Serie C"'),
        season: z.number().int().describe('Season year, e.g. 2019'),
        limit: z.number().int().min(1).max(30).optional().describe('Rows to show (default all)'),
      },
    },
    async (args) => {
      const { competition, error: compErr } = competitionOrError(args.competition);
      if (compErr) return compErr;
      if (!STANDINGS_COMPETITIONS.has(competition!)) {
        return err(
          `Standings can only be calculated for round-robin leagues (Série A/B/C), not for "${competition}". Use search_matches to inspect its fixtures.`,
        );
      }
      const rows = computeStandings(store, competition as never, args.season);
      if (rows.length === 0) {
        return err(`No matches found for ${competition} ${args.season}.`);
      }
      const isSerieA = competition === 'Brasileirão Série A';
      const limit = args.limit ?? rows.length;
      const lines = rows.slice(0, limit).map((r) => {
        const tag =
          r.position === 1
            ? ' - Champion'
            : isSerieA && r.position > rows.length - 4
              ? ' - Relegated'
              : '';
        return `${r.position}. ${r.team.displayName} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L) GD ${r.goalDifference}${tag}`;
      });
      return text(
        [
          `${args.season} ${competition} standings (calculated from ${rows.reduce((s, r) => s + r.matches, 0) / 2} matches):`,
          ...lines,
        ].join('\n'),
      );
    },
  );

  server.registerTool(
    'list_competitions',
    {
      title: 'List competitions',
      description: 'List the competitions covered by the dataset with seasons and match counts.',
      inputSchema: {},
    },
    async () => {
      const lines = listCompetitions(store).map(
        (c) =>
          `- ${c.competition}: ${c.matches} matches` +
          (c.seasons.length ? `, seasons ${c.seasons[0]}-${c.seasons[c.seasons.length - 1]}` : ''),
      );
      return text(['Competitions in dataset:', ...lines].join('\n'));
    },
  );

  // ------------------------------------------------------------------
  // Player queries
  // ------------------------------------------------------------------

  server.registerTool(
    'search_players',
    {
      title: 'Search players (FIFA database)',
      description:
        'Search the FIFA player database by name, nationality, club, position or ' +
        'rating. Sorted by overall rating. Examples: Brazilian players, ' +
        'highest-rated players at Flamengo, forwards (positionGroup=FWD).',
      inputSchema: {
        name: z.string().optional().describe('Player name (partial, accent-insensitive)'),
        nationality: z.string().optional().describe('Nationality, e.g. "Brazil"'),
        club: z.string().optional().describe('Club name, e.g. "Flamengo"'),
        position: z.string().optional().describe('Exact position code, e.g. "ST", "CB", "GK"'),
        positionGroup: z.enum(['GK', 'DEF', 'MID', 'FWD']).optional().describe('Position group filter'),
        minOverall: z.number().int().optional().describe('Minimum overall rating'),
        limit: z.number().int().min(1).max(100).optional().describe('Max players (default 20)'),
      },
    },
    async (args) => {
      const players = searchPlayers(store, {
        name: args.name,
        nationality: args.nationality,
        club: args.club,
        position: args.position,
        positionGroup: args.positionGroup,
        minOverall: args.minOverall,
        limit: args.limit ?? 20,
      });
      if (players.length === 0) return text('No players found for the given criteria.');
      const lines = players.map(
        (p, i) =>
          `${i + 1}. ${p.name} - Overall: ${p.overall ?? '?'}, Position: ${p.position ?? '?'}, Club: ${p.club ?? 'none'}${p.nationality ? `, ${p.nationality}` : ''}`,
      );
      return text([`${players.length} player(s):`, ...lines].join('\n'));
    },
  );

  server.registerTool(
    'players_by_club',
    {
      title: 'Players of a club',
      description:
        'List FIFA-database players of a club with ratings, plus club average. ' +
        'Example: "Who are the highest-rated players at Flamengo?"',
      inputSchema: {
        club: z.string().describe('Club name'),
        nationality: z.string().optional().describe('Nationality filter, e.g. "Brazil"'),
        limit: z.number().int().min(1).max(100).optional().describe('Max players (default 25)'),
      },
    },
    async (args) => {
      const summary = clubPlayerSummary(store, args.club);
      const players = searchPlayers(store, {
        club: args.club,
        nationality: args.nationality,
        limit: args.limit ?? 25,
      });
      if (players.length === 0) return text(`No players found for club "${args.club}".`);
      const lines = players.map(
        (p) => `- ${p.name} - Overall: ${p.overall ?? '?'}, Position: ${p.position ?? '?'}, Age: ${p.age ?? '?'}`,
      );
      const header = summary
        .map((s) => `${s.club}: ${s.players} players (avg rating: ${num(s.avgOverall, 0)})`)
        .join('; ');
      return text([`Players at "${args.club}" (${header}):`, ...lines].join('\n'));
    },
  );

  server.registerTool(
    'player_profile',
    {
      title: 'Player profile',
      description:
        'Detailed profile of one player: club, ratings, physical attributes and top skills. ' +
        'Example: "Who is Gabriel Barbosa?"',
      inputSchema: {
        name: z.string().describe('Player name'),
      },
    },
    async (args) => {
      const candidates = findPlayer(store, args.name);
      if (candidates.length === 0) return err(`Player "${args.name}" not found in the FIFA database.`);
      const p = candidates[0];
      const topSkills = Object.entries(p.skills)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 8)
        .map(([k, v]) => `${k} ${v}`)
        .join(', ');
      const lines = [
        `${p.name}${p.nationality ? ` (${p.nationality})` : ''}`,
        `Club: ${p.club ?? 'none'}, Position: ${p.position ?? '?'}, Jersey: ${p.jerseyNumber ?? '?'}`,
        `Age: ${p.age ?? '?'}, Height: ${p.height ?? '?'}, Weight: ${p.weight ?? '?'}, Preferred foot: ${p.preferredFoot ?? '?'}`,
        `Overall: ${p.overall ?? '?'}, Potential: ${p.potential ?? '?'}`,
        `Value: ${p.value ?? '?'}, Wage: ${p.wage ?? '?'}`,
        `Top skills: ${topSkills}`,
      ];
      if (candidates.length > 1) {
        lines.push('', `Other matches: ${candidates.slice(1).map((c) => `${c.name} (${c.club ?? 'no club'})`).join(', ')}`);
      }
      return text(lines.join('\n'));
    },
  );

  server.registerTool(
    'brazilian_players_summary',
    {
      title: 'Brazilian players summary',
      description:
        'Overview of Brazilian players in the FIFA database: top-rated players and ' +
        'club distribution with average ratings.',
      inputSchema: {
        top: z.number().int().min(1).max(50).optional().describe('Number of top players to list (default 10)'),
        clubs: z.number().int().min(1).max(50).optional().describe('Number of clubs to list (default 10)'),
      },
    },
    async (args) => {
      const topPlayers = searchPlayers(store, {
        nationality: 'Brazil',
        limit: args.top ?? 10,
      });
      const clubs = brazilianPlayersByClub(store, args.clubs ?? 10);
      const lines = [
        `Top-rated Brazilian players in dataset (${store.players.filter((p) => p.nationality === 'Brazil').length} total):`,
        ...topPlayers.map(
          (p, i) => `${i + 1}. ${p.name} - Overall: ${p.overall}, Position: ${p.position}, Club: ${p.club ?? 'none'}`,
        ),
        '',
        'Brazilian players by club:',
        ...clubs.map((c) => `- ${c.club}: ${c.players} players (avg rating: ${num(c.avgOverall, 0)})`),
      ];
      return text(lines.join('\n'));
    },
  );

  // ------------------------------------------------------------------
  // Statistical analysis
  // ------------------------------------------------------------------

  server.registerTool(
    'match_statistics',
    {
      title: 'Aggregate match statistics',
      description:
        'Average goals per match, home/away win rates and draw rate over a scope ' +
        '(competition, season, team, date range). Example: "Average goals per match in the Brasileirão".',
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
        team: z.string().optional().describe('Restrict to matches of one team'),
        dateFrom: z.string().optional(),
        dateTo: z.string().optional(),
      },
    },
    async (args) => {
      const { competition, error: compErr } = competitionOrError(args.competition);
      if (compErr) return compErr;
      let team: TeamIdentity | undefined;
      let note: string | undefined;
      if (args.team) {
        const r = teamOrError(args.team);
        if (r.error) return r.error;
        team = r.team;
        note = r.note;
      }
      const stats = matchStatistics(store, {
        competition,
        season: args.season,
        team,
        dateFrom: args.dateFrom,
        dateTo: args.dateTo,
      });
      if (stats.matches === 0) return withNote('No matches in the given scope.', note);
      const scope = [competition, args.season, team?.displayName, args.dateFrom && `${args.dateFrom}..${args.dateTo ?? ''}`]
        .filter(Boolean)
        .join(' ');
      return withNote(
        [
          `Statistics${scope ? ` for ${scope}` : ''}:`,
          `Matches: ${stats.matches}`,
          `Average goals per match: ${num(stats.avgGoalsPerMatch)}`,
          `Home win rate: ${pct(stats.homeWinRate)}`,
          `Draw rate: ${pct(stats.drawRate)}`,
          `Away win rate: ${pct(stats.awayWinRate)}`,
        ].join('\n'),
        note,
      );
    },
  );

  server.registerTool(
    'biggest_wins',
    {
      title: 'Biggest victories',
      description:
        'Largest victory margins in the dataset, optionally scoped by competition, season or team.',
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
        team: z.string().optional().describe('Only wins by this team'),
        limit: z.number().int().min(1).max(50).optional().describe('Rows (default 10)'),
      },
    },
    async (args) => {
      const { competition, error: compErr } = competitionOrError(args.competition);
      if (compErr) return compErr;
      let team: TeamIdentity | undefined;
      let note: string | undefined;
      if (args.team) {
        const r = teamOrError(args.team);
        if (r.error) return r.error;
        team = r.team;
        note = r.note;
      }
      const wins = biggestWins(
        store,
        { competition, season: args.season, team },
        args.limit ?? 10,
      );
      if (wins.length === 0) return withNote('No matches in the given scope.', note);
      const scope = [competition, args.season, team?.displayName].filter(Boolean).join(' ');
      const lines = wins.map(
        (w, i) =>
          `${i + 1}. ${w.match.date ?? 'unknown date'}: ${w.match.homeTeam.displayName} ${w.score} ${w.match.awayTeam.displayName} (${w.match.competition}${w.match.season ? ` ${w.match.season}` : ''})`,
      );
      return withNote([`Biggest victories${scope ? ` (${scope})` : ''}:`, ...lines].join('\n'), note);
    },
  );

  server.registerTool(
    'top_scoring_teams',
    {
      title: 'Top scoring teams',
      description:
        'Rank teams by goals scored in a competition/season. ' +
        'Example: "Which team scored the most goals in Serie A 2023?"',
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
        limit: z.number().int().min(1).max(50).optional().describe('Rows (default 10)'),
      },
    },
    async (args) => {
      const { competition, error: compErr } = competitionOrError(args.competition);
      if (compErr) return compErr;
      const rows = topScoringTeams(
        store,
        { competition, season: args.season },
        args.limit ?? 10,
      );
      if (rows.length === 0) return text('No matches in the given scope.');
      const scope = [competition, args.season].filter(Boolean).join(' ');
      const lines = rows.map(
        (r, i) => `${i + 1}. ${r.team.displayName} - ${r.goals} goals in ${r.matches} matches (${num(r.avgPerMatch)}/match)`,
      );
      return text([`Top scoring teams${scope ? ` (${scope})` : ''}:`, ...lines].join('\n'));
    },
  );

  // ------------------------------------------------------------------
  // Dataset info
  // ------------------------------------------------------------------

  server.registerTool(
    'dataset_info',
    {
      title: 'Dataset information',
      description: 'Data sources, licenses, row counts and load time of the underlying CSV datasets.',
      inputSchema: {},
    },
    async () => {
      const played = store.dedupedMatches.filter((m) => m.played).length;
      return text(
        [
          'Brazilian Soccer MCP dataset:',
          `- Matches: ${store.dedupedMatches.length} unique (${played} played) from ${store.matches.length} source rows`,
          `- Teams: ${store.teams.size} canonical identities`,
          `- Players (FIFA): ${store.players.length}`,
          `- Loaded at: ${store.loadedAt.toISOString()}`,
          '',
          'Sources (all Kaggle, pre-downloaded to data/kaggle/):',
          '- Brasileirao_Matches.csv / Brazilian_Cup_Matches.csv / Libertadores_Matches.csv (CC BY 4.0, ricardomattos05)',
          '- BR-Football-Dataset.csv (CC0 Public Domain, cuecacuela)',
          '- novo_campeonato_brasileiro.csv (CC BY 4.0, macedojleo)',
          '- fifa_data.csv (Apache 2.0, youssefelbadry10)',
        ].join('\n'),
      );
    },
  );

  // ------------------------------------------------------------------
  // Resource: dataset description
  // ------------------------------------------------------------------

  server.registerResource(
    'dataset-info',
    'soccer://datasets/info',
    {
      title: 'Dataset information',
      description: 'JSON description of the loaded datasets, sources and licenses.',
      mimeType: 'application/json',
    },
    async (uri) => ({
      contents: [
        {
          uri: uri.href,
          mimeType: 'application/json',
          text: JSON.stringify(
            {
              matches: store.dedupedMatches.length,
              sourceRows: store.matches.length,
              teams: store.teams.size,
              players: store.players.length,
              competitions: listCompetitions(store),
              sources: [
                { file: 'Brasileirao_Matches.csv', license: 'CC BY 4.0', source: 'kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro' },
                { file: 'Brazilian_Cup_Matches.csv', license: 'CC BY 4.0', source: 'kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro' },
                { file: 'Libertadores_Matches.csv', license: 'CC BY 4.0', source: 'kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro' },
                { file: 'BR-Football-Dataset.csv', license: 'CC0 Public Domain', source: 'kaggle.com/datasets/cuecacuela/brazilian-football-matches' },
                { file: 'novo_campeonato_brasileiro.csv', license: 'CC BY 4.0', source: 'kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019' },
                { file: 'fifa_data.csv', license: 'Apache 2.0', source: 'kaggle.com/datasets/youssefelbadry10/fifa-players-data' },
              ],
            },
            null,
            2,
          ),
        },
      ],
    }),
  );

  return server;
}
