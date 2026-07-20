/**
 * MCP server exposing the Brazilian soccer knowledge graph as tools.
 * The createServer factory is transport-agnostic so tests can drive it
 * over an in-memory transport; production wiring lives in index.ts.
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { Competition, Match } from "./lib/types.js";
import { Dataset } from "./lib/dataset.js";
import { KnowledgeGraph, GraphNode } from "./lib/graph.js";
import {
  biggestWins,
  brazilianPlayersByClub,
  competitionStats,
  computeStandings,
  findMatches,
  headToHead,
  resolveCompetition,
  resolveTeamOrError,
  searchPlayers,
  teamRecord,
} from "./lib/queries.js";
import {
  formatBigWins,
  formatCompetitionStats,
  formatHeadToHead,
  formatMatchLine,
  formatMatchList,
  formatPlayer,
  formatStandings,
  formatTeamRecord,
} from "./lib/format.js";

const DEFAULT_MATCH_LIMIT = 20;

function textResult(text: string) {
  return { content: [{ type: "text" as const, text }] };
}

function errorText(text: string) {
  return { content: [{ type: "text" as const, text }], isError: true };
}

function sortByDateDesc(matches: Match[]): Match[] {
  return [...matches].sort((a, b) => (b.date ?? "").localeCompare(a.date ?? ""));
}

export function createServer(dataset: Dataset, graph: KnowledgeGraph): McpServer {
  const server = new McpServer({
    name: "brazilian-soccer-mcp",
    version: "1.0.0",
  });

  const resolveCompetitionOrReply = (input?: string): { competition: Competition | null; error?: string } => {
    if (!input) return { competition: null };
    const c = resolveCompetition(input);
    if (!c) {
      return {
        competition: null,
        error: `Unknown competition: "${input}". Known competitions: ${Object.values(Competition).join(", ")}.`,
      };
    }
    return { competition: c };
  };

  // ------------------------------------------------------------------
  server.registerTool(
    "dataset_summary",
    {
      title: "Dataset summary",
      description:
        "Overview of the loaded Brazilian soccer datasets: row counts per source file, matches per competition, teams, players and season coverage.",
      inputSchema: {},
    },
    async () => {
      const byCompetition = new Map<string, number>();
      const seasons = new Set<number>();
      for (const m of dataset.matches) {
        byCompetition.set(m.competition, (byCompetition.get(m.competition) ?? 0) + 1);
        if (m.season !== null) seasons.add(m.season);
      }
      const lines = [
        "Brazilian Soccer Knowledge Graph — dataset summary",
        "",
        "Source files (rows loaded):",
        ...Object.entries(dataset.loadReport).map(([f, n]) => `- ${f}: ${n}`),
        "",
        `Unified matches (after cross-file dedupe): ${dataset.matches.length}`,
        ...[...byCompetition.entries()].map(([c, n]) => `- ${c}: ${n} matches`),
        `Teams: ${dataset.teams.size}`,
        `Players (FIFA database): ${dataset.players.length}`,
        `Seasons covered: ${Math.min(...seasons)}–${Math.max(...seasons)}`,
        `Knowledge graph: ${graph.nodes.size} nodes`,
      ];
      return textResult(lines.join("\n"));
    },
  );

  // ------------------------------------------------------------------
  server.registerTool(
    "find_matches",
    {
      title: "Find matches",
      description:
        "Find matches by team (and optionally a specific opponent), competition, season, date range and venue. Team names accept accents and state suffixes (\"Flamengo\", \"Flamengo-RJ\", \"São Paulo\" all work).",
      inputSchema: {
        team: z.string().optional().describe("Team name, e.g. 'Palmeiras' or 'Palmeiras-SP'."),
        opponent: z.string().optional().describe("Opponent team name for matches between two teams."),
        competition: z.string().optional().describe("Competition name or alias: 'Brasileirão', 'Série A', 'Copa do Brasil', 'Libertadores', 'Série B', 'Série C'."),
        season: z.number().int().optional().describe("Season year, e.g. 2023."),
        dateFrom: z.string().optional().describe("ISO date lower bound YYYY-MM-DD."),
        dateTo: z.string().optional().describe("ISO date upper bound YYYY-MM-DD."),
        venue: z.enum(["home", "away", "any"]).optional().describe("Restrict to home or away matches of `team`."),
        round: z.string().optional().describe("Round/stage filter: league round number ('1'-'38'), Copa do Brasil round ('8' = final), Libertadores stage ('group stage', 'round of 16', 'quarterfinals', 'semifinals', 'final')."),
        limit: z.number().int().min(1).max(100).optional().describe(`Max matches to list (default ${DEFAULT_MATCH_LIMIT}).`),
      },
    },
    async ({ team, opponent, competition, season, dateFrom, dateTo, venue, round, limit }) => {
      let teamNode = null;
      if (team) {
        const r = resolveTeamOrError(dataset, team);
        if (r.error) return errorText(r.error);
        teamNode = r.team!;
      }
      let oppNode = null;
      if (opponent) {
        const r = resolveTeamOrError(dataset, opponent);
        if (r.error) return errorText(r.error);
        oppNode = r.team!;
      }
      const comp = resolveCompetitionOrReply(competition);
      if (comp.error) return errorText(comp.error);

      const matches = findMatches(dataset, {
        team: teamNode,
        opponent: oppNode,
        competition: comp.competition,
        season: season ?? null,
        dateFrom: dateFrom ?? null,
        dateTo: dateTo ?? null,
        venue: venue ?? "any",
        round: round ?? null,
      });
      if (matches.length === 0) {
        return textResult("No matches found for the given criteria.");
      }
      const max = limit ?? DEFAULT_MATCH_LIMIT;
      // Most recent first for readability.
      const ordered = sortByDateDesc(matches);
      const { lines, hiddenCount } = formatMatchList(ordered, max);
      const headerBits = [
        teamNode ? `team=${teamNode.name}` : null,
        oppNode ? `opponent=${oppNode.name}` : null,
        comp.competition ? `competition=${comp.competition}` : null,
        season ? `season=${season}` : null,
        dateFrom || dateTo ? `dates=${dateFrom ?? "..."}..${dateTo ?? "..."}` : null,
      ].filter(Boolean);
      const out = [
        `${matches.length} match(es) found (${headerBits.join(", ")}):`,
        ...lines,
      ];
      if (hiddenCount > 0) out.push(`- ... (${hiddenCount} more matches in dataset)`);
      return textResult(out.join("\n"));
    },
  );

  // ------------------------------------------------------------------
  server.registerTool(
    "head_to_head",
    {
      title: "Head-to-head",
      description:
        "Compare two teams: all matches between them plus aggregate wins/draws/losses and goals. Example: Flamengo vs Fluminense (Fla-Flu derby).",
      inputSchema: {
        teamA: z.string().describe("First team name."),
        teamB: z.string().describe("Second team name."),
        competition: z.string().optional().describe("Optional competition filter."),
        season: z.number().int().optional().describe("Optional season filter."),
        limit: z.number().int().min(1).max(50).optional().describe("Max matches to list (default 10)."),
      },
    },
    async ({ teamA, teamB, competition, season, limit }) => {
      const ra = resolveTeamOrError(dataset, teamA);
      if (ra.error) return errorText(ra.error);
      const rb = resolveTeamOrError(dataset, teamB);
      if (rb.error) return errorText(rb.error);
      const comp = resolveCompetitionOrReply(competition);
      if (comp.error) return errorText(comp.error);

      const h2h = headToHead(dataset, ra.team!, rb.team!, {
        competition: comp.competition,
        season: season ?? null,
      });
      if (h2h.matches.length === 0) {
        return textResult(`No matches found between ${ra.team!.name} and ${rb.team!.name} in the dataset.`);
      }
      h2h.matches = sortByDateDesc(h2h.matches);
      return textResult(formatHeadToHead(ra.team!, rb.team!, h2h, limit ?? 10));
    },
  );

  // ------------------------------------------------------------------
  server.registerTool(
    "team_stats",
    {
      title: "Team statistics",
      description:
        "Win/draw/loss record, goals scored/conceded and win rate for a team, optionally filtered by season, competition and venue (home/away).",
      inputSchema: {
        team: z.string().describe("Team name."),
        season: z.number().int().optional().describe("Season year."),
        competition: z.string().optional().describe("Competition filter."),
        venue: z.enum(["home", "away", "any"]).optional().describe("Venue filter (default any)."),
      },
    },
    async ({ team, season, competition, venue }) => {
      const r = resolveTeamOrError(dataset, team);
      if (r.error) return errorText(r.error);
      const comp = resolveCompetitionOrReply(competition);
      if (comp.error) return errorText(comp.error);

      const matches = findMatches(dataset, {
        team: r.team!,
        competition: comp.competition,
        season: season ?? null,
        venue: venue ?? "any",
        playedOnly: true,
      });
      if (matches.length === 0) {
        return textResult(`No played matches found for ${r.team!.name} with the given filters.`);
      }
      const record = teamRecord(matches, r.team!);
      const context = [
        venue && venue !== "any" ? `${venue} record` : "record",
        season ? `(${season}${comp.competition ? ` ${comp.competition}` : ""})` : comp.competition ? `(${comp.competition})` : "(all competitions in dataset)",
      ].join(" ");
      return textResult(formatTeamRecord(r.team!, record, context));
    },
  );

  // ------------------------------------------------------------------
  server.registerTool(
    "standings",
    {
      title: "League standings",
      description:
        "Points table for a league season calculated from match results (3 pts win, 1 draw; tiebreakers: wins, goal difference, goals for). Works for Brasileirão Série A (2003-2023), Série B and Série C.",
      inputSchema: {
        season: z.number().int().describe("Season year, e.g. 2019."),
        competition: z.string().optional().describe("League: 'Brasileirão Série A' (default), 'Série B' or 'Série C'."),
      },
    },
    async ({ season, competition }) => {
      const comp = competition ? resolveCompetition(competition) : Competition.BrasileiraoSerieA;
      if (!comp) {
        return errorText(`Unknown competition: "${competition}".`);
      }
      if (![Competition.BrasileiraoSerieA, Competition.SerieB, Competition.SerieC].includes(comp)) {
        return errorText(`Standings are only available for league competitions (Série A/B/C), not ${comp}.`);
      }
      const rows = computeStandings(dataset, comp, season);
      if (rows.length === 0) {
        return textResult(`No played matches found for ${comp} ${season}.`);
      }
      return textResult(formatStandings(rows, comp, season));
    },
  );

  // ------------------------------------------------------------------
  server.registerTool(
    "search_players",
    {
      title: "Search players",
      description:
        "Search the FIFA player database by name, nationality (e.g. 'Brazil'), club (e.g. 'Flamengo' — matches both FIFA club names and Brazilian match-data teams), position (e.g. 'ST', or groups 'forward', 'midfielder', 'defender', 'goalkeeper') and minimum overall rating. Sorted by overall rating.",
      inputSchema: {
        name: z.string().optional().describe("Player name substring, e.g. 'Neymar' or 'Gabriel Barbosa'."),
        nationality: z.string().optional().describe("Country, e.g. 'Brazil'."),
        club: z.string().optional().describe("Club name substring as in FIFA data, e.g. 'Grêmio'."),
        team: z.string().optional().describe("Brazilian team name resolved against match data (aliases like 'Atlético Mineiro' work)."),
        position: z.string().optional().describe("Position code ('ST', 'GK', ...) or group: forward, winger, midfielder, defender, fullback, goalkeeper."),
        minOverall: z.number().int().optional().describe("Minimum FIFA overall rating."),
        limit: z.number().int().min(1).max(100).optional().describe("Max players (default 25)."),
      },
    },
    async ({ name, nationality, club, team, position, minOverall, limit }) => {
      let teamKey: string | null = null;
      let teamName: string | null = null;
      if (team) {
        const r = resolveTeamOrError(dataset, team);
        if (r.error) return errorText(r.error);
        teamKey = r.team!.key;
        teamName = r.team!.name;
      }
      const players = searchPlayers(dataset, {
        name: name ?? null,
        nationality: nationality ?? null,
        club: club ?? null,
        teamKey,
        position: position ?? null,
        minOverall: minOverall ?? null,
        limit: limit ?? 25,
      });
      if (players.length === 0) {
        const criteria = [name && `name~${name}`, nationality && `nationality=${nationality}`, club && `club~${club}`, teamName && `team=${teamName}`, position && `position=${position}`, minOverall && `overall>=${minOverall}`].filter(Boolean).join(", ");
        return textResult(`No players found for: ${criteria}. Note: the FIFA dataset covers 2018-19 squads; some Brazilian clubs are absent.`);
      }
      const header = `${players.length} player(s) found (sorted by overall rating):`;
      return textResult([header, ...players.map((p, i) => formatPlayer(p, i + 1))].join("\n"));
    },
  );

  // ------------------------------------------------------------------
  server.registerTool(
    "brazilian_players_by_club",
    {
      title: "Brazilian players by club",
      description:
        "Summary of Brazilian players at Brazilian clubs in the FIFA dataset: player count and average rating per club, plus the top-rated Brazilian players overall.",
      inputSchema: {
        top: z.number().int().min(1).max(50).optional().describe("Number of top-rated Brazilian players to list (default 10)."),
      },
    },
    async ({ top }) => {
      const topPlayers = searchPlayers(dataset, { nationality: "Brazil", limit: top ?? 10 });
      const clubs = brazilianPlayersByClub(dataset);
      const lines = [
        "Top-rated Brazilian players in dataset:",
        ...topPlayers.map((p, i) => formatPlayer(p, i + 1)),
        "",
        "Brazilian players at Brazilian clubs:",
        ...clubs.map((c) => `- ${c.team.name}: ${c.count} players (avg rating: ${c.avgOverall})`),
      ];
      return textResult(lines.join("\n"));
    },
  );

  // ------------------------------------------------------------------
  server.registerTool(
    "biggest_wins",
    {
      title: "Biggest wins",
      description: "Largest victory margins in the dataset, optionally filtered by competition and/or season.",
      inputSchema: {
        competition: z.string().optional().describe("Competition filter."),
        season: z.number().int().optional().describe("Season filter."),
        limit: z.number().int().min(1).max(50).optional().describe("Number of results (default 10)."),
      },
    },
    async ({ competition, season, limit }) => {
      const comp = resolveCompetitionOrReply(competition);
      if (comp.error) return errorText(comp.error);
      const wins = biggestWins(dataset, comp.competition, season ?? null, limit ?? 10);
      if (wins.length === 0) return textResult("No played matches found for the given filters.");
      const scope = `in ${comp.competition ?? "all competitions"}${season ? ` ${season}` : ""} (provided data)`;
      return textResult(formatBigWins(wins, scope));
    },
  );

  // ------------------------------------------------------------------
  server.registerTool(
    "competition_stats",
    {
      title: "Competition statistics",
      description:
        "Aggregated statistics: average goals per match, home/draw/away win rates and the highest-scoring team. Filter by competition and/or season; without filters covers the whole dataset.",
      inputSchema: {
        competition: z.string().optional().describe("Competition filter."),
        season: z.number().int().optional().describe("Season filter."),
      },
    },
    async ({ competition, season }) => {
      const comp = resolveCompetitionOrReply(competition);
      if (comp.error) return errorText(comp.error);
      const stats = competitionStats(dataset, comp.competition, season ?? null);
      if (stats.matches === 0) return textResult("No played matches found for the given filters.");
      return textResult(formatCompetitionStats(stats));
    },
  );

  // ------------------------------------------------------------------
  server.registerTool(
    "graph_neighbors",
    {
      title: "Explore knowledge graph",
      description:
        "Explore the soccer knowledge graph around an entity: a team (its matches, players), a player (their team) or a competition (its matches). Returns the connected nodes and relationships.",
      inputSchema: {
        entity: z.string().describe("Team name, player name or competition name."),
        edgeType: z
          .enum(["HOME_IN", "AWAY_IN", "WON", "LOST", "DREW", "PLAYS_FOR", "PLAYED_IN"])
          .optional()
          .describe("Optional relationship filter."),
        limit: z.number().int().min(1).max(100).optional().describe("Max neighbors (default 20)."),
      },
    },
    async ({ entity, edgeType, limit }) => {
      // Try team first, then competition, then player name.
      let node: GraphNode | undefined;
      const teamRes = dataset.teams.resolve(entity);
      if (teamRes.team) {
        node = graph.nodes.get(KnowledgeGraph.teamNodeId(teamRes.team));
      }
      if (!node) {
        const comp = resolveCompetition(entity);
        if (comp) node = graph.nodes.get(KnowledgeGraph.competitionNodeId(comp));
      }
      if (!node) {
        const players = searchPlayers(dataset, { name: entity, limit: 1 });
        const exact = players.find((p) => p.name.toLowerCase() === entity.toLowerCase()) ?? players[0];
        if (exact) node = graph.nodes.get(KnowledgeGraph.playerNodeId(exact));
      }
      if (!node) {
        return errorText(`Entity not found in knowledge graph: "${entity}". Try a team, player or competition name.`);
      }
      const neighbors = graph.neighbors(node.id, edgeType);
      const max = limit ?? 20;
      const shown = neighbors.slice(0, max);
      const lines = [
        `${node.type} "${node.label}" — ${neighbors.length} relationship(s)${edgeType ? ` of type ${edgeType}` : ""}:`,
        ...shown.map(({ edge, node: n }) => {
          const direction = edge.from === node!.id ? `--${edge.type}-->` : `<--${edge.type}--`;
          return `- ${direction} [${n.type}] ${n.label}`;
        }),
      ];
      if (neighbors.length > shown.length) {
        lines.push(`- ... (${neighbors.length - shown.length} more)`);
      }
      return textResult(lines.join("\n"));
    },
  );

  return server;
}
