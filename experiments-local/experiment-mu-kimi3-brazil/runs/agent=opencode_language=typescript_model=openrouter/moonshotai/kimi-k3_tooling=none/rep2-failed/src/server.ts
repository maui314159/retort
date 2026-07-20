/**
 * MCP server exposing the Brazilian soccer knowledge graph as tools.
 * Transport: stdio (standard for MCP servers).
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { KnowledgeGraph } from "./knowledgeGraph.js";
import {
  formatMatchLine,
  formatMatchList,
  formatPlayerList,
  formatStandings,
  formatTeamRecord,
} from "./format.js";

function text(s: string) {
  return { content: [{ type: "text" as const, text: s }] };
}

export function createServer(graph: KnowledgeGraph): McpServer {
  const server = new McpServer({
    name: "brazilian-soccer-mcp",
    version: "1.0.0",
  });

  server.tool(
    "search_matches",
    "Find soccer matches by team (home/away/either), opponent, competition, season, or date range.",
    {
      team: z.string().optional().describe("Team name (matches home or away)"),
      opponent: z.string().optional().describe("Second team; use with `team` for head-to-head fixtures"),
      competition: z.string().optional().describe("e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores'"),
      season: z.number().optional().describe("Season year, e.g. 2023"),
      date_from: z.string().optional().describe("ISO date YYYY-MM-DD"),
      date_to: z.string().optional().describe("ISO date YYYY-MM-DD"),
      limit: z.number().optional().describe("Max matches to return (default 20)"),
    },
    async ({ team, opponent, competition, season, date_from, date_to, limit }) => {
      const matches = graph.findMatches({
        team: opponent ? undefined : team,
        teamA: opponent ? team : undefined,
        teamB: opponent,
        competition,
        season,
        dateFrom: date_from,
        dateTo: date_to,
        limit: limit ?? 20,
      });
      if (!matches.length) return text("No matches found for the given criteria.");
      const header = team
        ? opponent
          ? `${team} vs ${opponent}:`
          : `Matches involving ${team}:`
        : "Matches:";
      return text(`${header}\n${formatMatchList(matches)}`);
    },
  );

  server.tool(
    "head_to_head",
    "Head-to-head record between two teams: all matches plus win/draw/loss summary.",
    {
      team_a: z.string(),
      team_b: z.string(),
    },
    async ({ team_a, team_b }) => {
      const h2h = graph.headToHead(team_a, team_b);
      if (!h2h.total) return text(`No matches found between ${team_a} and ${team_b}.`);
      const list = formatMatchList(h2h.matches.slice(0, 15), h2h.total);
      return text(
        `${team_a} vs ${team_b}:\n${list}\n\nHead-to-head in dataset: ${team_a} ${h2h.winsA} wins, ${team_b} ${h2h.winsB} wins, ${h2h.draws} draws (from ${h2h.total} matches)`,
      );
    },
  );

  server.tool(
    "team_statistics",
    "Win/draw/loss record and goals for a team, optionally by season, competition and venue (home/away).",
    {
      team: z.string(),
      season: z.number().optional(),
      competition: z.string().optional(),
      venue: z.enum(["home", "away", "all"]).optional(),
    },
    async ({ team, season, competition, venue }) => {
      const rec = graph.teamStats(team, { season, competition, venue });
      const scope = [season, competition].filter((x) => x !== undefined).join(" ");
      const label = `${team} ${venue && venue !== "all" ? `${venue} record` : "record"}${scope ? ` (${scope})` : ""}`;
      return text(formatTeamRecord(label, rec));
    },
  );

  server.tool(
    "competition_standings",
    "League table for a season computed from match results (3 points for a win).",
    {
      season: z.number(),
      competition: z.string().optional().describe("Defaults to Brasileirão Série A"),
    },
    async ({ season, competition }) => {
      const comp = competition ?? "Brasileirão Série A";
      const rows = graph.standings(season, comp);
      if (!rows.length) return text(`No match data for ${comp} ${season}.`);
      return text(formatStandings(rows, `${season} ${comp} Standings`));
    },
  );

  server.tool(
    "top_scoring_teams",
    "Teams with the most goals scored in a season and/or competition.",
    {
      season: z.number().optional(),
      competition: z.string().optional(),
      limit: z.number().optional(),
    },
    async ({ season, competition, limit }) => {
      const rows = graph.topScoringTeams(season, competition, limit ?? 10);
      if (!rows.length) return text("No data for the given filters.");
      const lines = rows.map((r, i) => `${i + 1}. ${r.team} - ${r.goals} goals`);
      const scope = [competition, season].filter(Boolean).join(" ");
      return text(`Top scoring teams${scope ? ` (${scope})` : ""}:\n${lines.join("\n")}`);
    },
  );

  server.tool(
    "team_competitions",
    "List every competition a team appears in across all datasets.",
    { team: z.string() },
    async ({ team }) => {
      const rows = graph.teamCompetitions(team);
      if (!rows.length) return text(`No matches found for ${team}.`);
      const lines = rows.map((r) => `- ${r.competition}: ${r.matches} matches`);
      return text(`${team} has played in:\n${lines.join("\n")}`);
    },
  );

  server.tool(
    "last_match",
    "Most recent match between two teams, with score.",
    {
      team_a: z.string(),
      team_b: z.string(),
    },
    async ({ team_a, team_b }) => {
      const m = graph.lastMatch(team_a, team_b);
      if (!m) return text(`No matches found between ${team_a} and ${team_b}.`);
      return text(`Most recent ${team_a} vs ${team_b}:\n${formatMatchLine(m)}`);
    },
  );

  server.tool(
    "search_players",
    "Search FIFA player data by name, nationality, club, position and minimum overall rating.",
    {
      name: z.string().optional(),
      nationality: z.string().optional().describe("e.g. 'Brazil'"),
      club: z.string().optional().describe("e.g. 'Flamengo'"),
      position: z.string().optional().describe("e.g. 'ST', 'GK', 'CDM'"),
      min_overall: z.number().optional(),
      limit: z.number().optional().describe("Default 20"),
    },
    async ({ name, nationality, club, position, min_overall, limit }) => {
      const players = graph.searchPlayers({
        name,
        nationality,
        club,
        position,
        minOverall: min_overall,
        limit: limit ?? 20,
      });
      if (!players.length) return text("No players found for the given criteria.");
      return text(formatPlayerList(players));
    },
  );

  server.tool(
    "brazilian_players_by_club",
    "Summary of Brazilian players grouped by Brazilian club (count and average rating).",
    {},
    async () => {
      const rows = graph.playersByClubSummary({ nationality: "Brazil", brazilianClubsOnly: true });
      if (!rows.length) return text("No Brazilian players found at Brazilian clubs in the dataset.");
      const lines = rows.map((r) => `- ${r.club}: ${r.players} players (avg rating: ${r.avgOverall.toFixed(0)})`);
      return text(`Brazilian players at Brazilian clubs:\n${lines.join("\n")}`);
    },
  );

  server.tool(
    "biggest_wins",
    "Largest victory margins in the dataset, optionally filtered by competition/season.",
    {
      competition: z.string().optional(),
      season: z.number().optional(),
      limit: z.number().optional(),
    },
    async ({ competition, season, limit }) => {
      const matches = graph.biggestWins({ competition, season }, limit ?? 10);
      if (!matches.length) return text("No matches found for the given filters.");
      const scope = competition ?? "all competitions";
      const lines = matches.map((m, i) => `${i + 1}. ${formatMatchLine(m).replace(/^- /, "")}`);
      return text(`Biggest victories (${scope}${season ? ` ${season}` : ""}):\n${lines.join("\n")}`);
    },
  );

  server.tool(
    "goals_statistics",
    "Aggregate scoring statistics: average goals per match, home/away win rates, draw rate.",
    {
      competition: z.string().optional(),
      season: z.number().optional(),
      team: z.string().optional(),
    },
    async ({ competition, season, team }) => {
      const s = graph.goalsStats({ competition, season, team });
      if (!s.matches) return text("No matches found for the given filters.");
      const scope = [team, competition, season].filter(Boolean).join(", ") || "all data";
      return text(
        [
          `Statistics (${scope}):`,
          `- Matches: ${s.matches}`,
          `- Total goals: ${s.totalGoals}`,
          `- Average goals per match: ${s.avgGoalsPerMatch.toFixed(2)}`,
          `- Home win rate: ${(s.homeWinRate * 100).toFixed(1)}%`,
          `- Away win rate: ${(s.awayWinRate * 100).toFixed(1)}%`,
          `- Draw rate: ${(s.drawRate * 100).toFixed(1)}%`,
        ].join("\n"),
      );
    },
  );

  server.tool(
    "list_competitions",
    "List all competitions present in the loaded datasets.",
    {},
    async () => text(`Competitions in dataset:\n${graph.competitions().map((c) => `- ${c}`).join("\n")}`),
  );

  return server;
}

export async function main() {
  const { getGraph } = await import("./knowledgeGraph.js");
  const graph = await getGraph();
  const server = createServer(graph);
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error(
    `brazilian-soccer-mcp ready: ${graph.matches.length} matches, ${graph.players.length} players`,
  );
}
