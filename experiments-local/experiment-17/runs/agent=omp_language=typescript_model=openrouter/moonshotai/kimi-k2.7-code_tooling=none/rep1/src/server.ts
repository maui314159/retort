import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { SoccerEngine, MatchFilters, PlayerFilters } from "./engine.js";

function formatMatch(m: { date: string; home: string; away: string; homeGoals: number | null; awayGoals: number | null; competition: string; round: string | null; stage: string | null }): string {
  const score = m.homeGoals !== null && m.awayGoals !== null ? `${m.homeGoals}-${m.awayGoals}` : "?-?";
  const detail = m.stage || (m.round ? `Round ${m.round}` : "");
  return `${m.date}: ${m.home} ${score} ${m.away}${detail ? ` (${m.competition} ${detail})` : ` (${m.competition})`}`;
}

export function createMcpServer(engine: SoccerEngine): McpServer {
  const server = new McpServer({
    name: "brazilian-soccer-mcp-server",
    version: "1.0.0",
  });

  server.registerTool(
    "search_matches",
    {
      description: "Find matches by team, competition, season, or date range. Returns a list of matches with scores and details.",
      inputSchema: z.object({
        team: z.string().optional().describe("Team name to search for (home or away)"),
        home: z.string().optional().describe("Home team name"),
        away: z.string().optional().describe("Away team name"),
        competition: z.string().optional().describe("Competition name (Brasileirao, Copa do Brasil, Copa Libertadores)"),
        season: z.number().int().optional().describe("Season year"),
        fromDate: z.string().optional().describe("Start date (YYYY-MM-DD)"),
        toDate: z.string().optional().describe("End date (YYYY-MM-DD)"),
        limit: z.number().int().optional().describe("Maximum number of matches to return"),
      }),
    },
    async (args) => {
      const filters: MatchFilters = {
        team: args.team,
        home: args.home,
        away: args.away,
        competition: args.competition,
        season: args.season,
        fromDate: args.fromDate,
        toDate: args.toDate,
        limit: args.limit,
      };
      const matches = engine.findMatches(filters);
      const lines = matches.length ? ["Found matches:", ...matches.map(formatMatch)] : ["No matches found."];
      return { content: [{ type: "text", text: lines.join("\n") }] };
    },
  );

  server.registerTool(
    "head_to_head",
    {
      description: "Compare two teams head-to-head, including wins/losses/draws and recent matches.",
      inputSchema: z.object({
        teamA: z.string().describe("First team"),
        teamB: z.string().describe("Second team"),
        competition: z.string().optional(),
        season: z.number().int().optional(),
        limit: z.number().int().optional(),
      }),
    },
    async (args) => {
      const { matches, winsA, winsB, draws } = engine.getHeadToHead(args.teamA, args.teamB, {
        competition: args.competition,
        season: args.season,
        limit: args.limit,
      });
      const lines = [
        `${args.teamA} vs ${args.teamB} head-to-head:`,
        `Record: ${args.teamA} ${winsA} wins, ${args.teamB} ${winsB} wins, ${draws} draws`,
        "Matches:",
        ...matches.slice(0, args.limit || 20).map(formatMatch),
      ];
      return { content: [{ type: "text", text: lines.join("\n") }] };
    },
  );

  server.registerTool(
    "team_stats",
    {
      description: "Get win/loss/draw record, goals, and home/away split for a team.",
      inputSchema: z.object({
        team: z.string().describe("Team name"),
        competition: z.string().optional(),
        season: z.number().int().optional(),
      }),
    },
    async (args) => {
      const stats = engine.getTeamStats(args.team, {
        competition: args.competition,
        season: args.season,
      });
      const lines = [
        `${stats.team} stats:`,
        `Matches: ${stats.matches}`,
        `Wins: ${stats.wins}, Draws: ${stats.draws}, Losses: ${stats.losses}`,
        `Goals For: ${stats.goalsFor}, Goals Against: ${stats.goalsAgainst}`,
        `Win rate: ${stats.winRate.toFixed(1)}%`,
        `Home: ${stats.homeRecord.wins}-${stats.homeRecord.draws}-${stats.homeRecord.losses} (${stats.homeRecord.goalsFor} GF, ${stats.homeRecord.goalsAgainst} GA)`,
        `Away: ${stats.awayRecord.wins}-${stats.awayRecord.draws}-${stats.awayRecord.losses} (${stats.awayRecord.goalsFor} GF, ${stats.awayRecord.goalsAgainst} GA)`,
      ];
      return { content: [{ type: "text", text: lines.join("\n") }] };
    },
  );

  server.registerTool(
    "standings",
    {
      description: "Calculate league standings for a season (Brasileirao points system).",
      inputSchema: z.object({
        season: z.number().int().describe("Season year"),
        competition: z.string().optional(),
      }),
    },
    async (args) => {
      const standings = engine.getStandings(args.season, args.competition);
      const lines = standings.length
        ? [
            `${args.season} ${args.competition || "Brasileirao"} standings:`,
            ...standings.map(
              (r) =>
                `${r.rank}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L) GF:${r.goalsFor} GA:${r.goalsAgainst}`,
            ),
          ]
        : ["No standings data found."];
      return { content: [{ type: "text", text: lines.join("\n") }] };
    },
  );

  server.registerTool(
    "search_players",
    {
      description: "Search FIFA player data by name, nationality, club, or position.",
      inputSchema: z.object({
        name: z.string().optional(),
        nationality: z.string().optional(),
        club: z.string().optional(),
        position: z.string().optional(),
        minOverall: z.number().int().optional(),
        limit: z.number().int().optional(),
      }),
    },
    async (args) => {
      const filters: PlayerFilters = {
        name: args.name,
        nationality: args.nationality,
        club: args.club,
        position: args.position,
        minOverall: args.minOverall,
        limit: args.limit,
      };
      const players = engine.getPlayers(filters);
      const lines = players.length
        ? players.map((p) => `${p.name} - Overall: ${p.overall ?? "?"}, Position: ${p.position ?? "?"}, Club: ${p.club ?? "?"}, Nationality: ${p.nationality ?? "?"}`)
        : ["No players found."];
      return { content: [{ type: "text", text: lines.join("\n") }] };
    },
  );

  server.registerTool(
    "get_player",
    {
      description: "Get detailed info about a specific player by name.",
      inputSchema: z.object({
        name: z.string(),
      }),
    },
    async (args) => {
      const players = engine.getPlayers({ name: args.name, limit: 5 });
      const lines = players.length
        ? players.map(
            (p) =>
              `${p.name} - Age: ${p.age ?? "?"}, Nationality: ${p.nationality ?? "?"}, Overall: ${p.overall ?? "?"}, Potential: ${p.potential ?? "?"}, Club: ${p.club ?? "?"}, Position: ${p.position ?? "?"}`,
          )
        : ["No player found."];
      return { content: [{ type: "text", text: lines.join("\n") }] };
    },
  );

  server.registerTool(
    "competition_info",
    {
      description: "Get top scorers and basic stats for a competition/season.",
      inputSchema: z.object({
        competition: z.string().optional(),
        season: z.number().int().optional(),
      }),
    },
    async (args) => {
      const topScorers = engine.getTopScorers(args.season, args.competition, 10);
      const avg = engine.getAverageGoals({ competition: args.competition, season: args.season });
      const lines = [
        `Competition: ${args.competition || "All"}${args.season ? ` Season: ${args.season}` : ""}`,
        `Average goals per match: ${avg.averageGoals.toFixed(2)}`,
        `Home win rate: ${avg.homeWinRate.toFixed(1)}%`,
        "Top scoring teams:",
        ...topScorers.map((t, i) => `${i + 1}. ${t.team} - ${t.goalsFor} goals`),
      ];
      return { content: [{ type: "text", text: lines.join("\n") }] };
    },
  );

  server.registerTool(
    "statistics_summary",
    {
      description: "Get aggregate statistics like average goals per match, home win rate, and biggest wins.",
      inputSchema: z.object({
        competition: z.string().optional(),
        season: z.number().int().optional(),
      }),
    },
    async (args) => {
      const avg = engine.getAverageGoals({ competition: args.competition, season: args.season });
      const biggest = engine.getBiggestWins(10, { competition: args.competition, season: args.season });
      const lines = [
        `Statistics${args.competition ? ` for ${args.competition}` : ""}${args.season ? ` (${args.season})` : ""}:`,
        `Total matches: ${avg.totalMatches}`,
        `Average goals per match: ${avg.averageGoals.toFixed(2)}`,
        `Home win rate: ${avg.homeWinRate.toFixed(1)}%`,
        "Biggest wins:",
        ...biggest.map(formatMatch),
      ];
      return { content: [{ type: "text", text: lines.join("\n") }] };
    },
  );

  server.registerTool(
    "derbies",
    {
      description: "Find classic derby matches in the dataset for a given season or across all seasons.",
      inputSchema: z.object({
        season: z.number().int().optional(),
        competition: z.string().optional(),
        limit: z.number().int().optional(),
      }),
    },
    async (args) => {
      const filters: MatchFilters = {
        season: args.season,
        competition: args.competition,
        limit: args.limit,
      };
      const derbies = engine.getDerbies(filters);
      const lines = derbies.length ? ["Derby matches:", ...derbies.map(formatMatch)] : ["No derby matches found."];
      return { content: [{ type: "text", text: lines.join("\n") }] };
    },
  );

  return server;
}

export async function runServer(engine: SoccerEngine): Promise<void> {
  const server = createMcpServer(engine);
  const transport = new StdioServerTransport();
  await server.connect(transport);
}
