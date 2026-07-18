/**
 * brazilian-soccer-mcp — MCP server
 *
 * Context block
 * ============
 * See src/types.ts for the top-level project context block.
 *
 * Exposes the `SoccerDatabase` query engine over the Model Context Protocol
 * (stdio transport). Each tool returns a `CallToolResult` whose `content`
 * is the human-readable formatted text produced by `src/format.ts`.
 *
 * Tools exposed:
 *   find_matches          — filter matches by team/opponent/competition/season/dates.
 *   last_match_between    — most recent fixture between two teams.
 *   team_stats            — W/D/L + goals, home/away split.
 *   head_to_head          — pairwise record + match list.
 *   competitions_for_team — distinct competitions a team appears in.
 *   player_search         — FIFA player filter (name/nationality/club/position).
 *   top_brazilian_players — convenience: Brazilian players sorted by rating.
 *   brazilian_players_by_club — Brazilian players grouped by club.
 *   standings             — computed league table for competition+season.
 *   biggest_wins          — largest goal-difference victories.
 *   average_goals         — mean goals-per-match + home/away/draw rates.
 *   best_record_at_venue  — team with the best home (or away) record.
 *
 * Run: `node dist/index.js` (stdio MCP server).
 * Build: `npm run build`. Tests: `npm test`.
 */

import { fileURLToPath } from "node:url";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import { SoccerDatabase } from "./engine.js";
import { defaultDataDir, loadAllMatches, loadFifaPlayers } from "./loaders.js";
import * as fmt from "./format.js";

function textResult(text: string): CallToolResult {
  return {
    content: [{ type: "text", text }],
  };
}

/** Build an McpServer wired to a given SoccerDatabase (injectable for tests).. */
export function buildServer(db: SoccerDatabase): McpServer {
  const server = new McpServer({
    name: "brazilian-soccer-mcp",
    version: "1.0.0",
  });

  server.tool(
    "find_matches",
    "Find matches by team, opponent, competition, season, and/or date range (YYYY-MM-DD). Returns the most recent matches first.",
    {
      team: z.string().optional().describe("Team name (home or away)."),
      opponent: z.string().optional().describe("Opponent team name."),
      competition: z
        .string()
        .optional()
        .describe('Competition substring, e.g. "Brasileirão", "Copa do Brasil", "Libertadores".'),
      season: z.number().int().optional().describe("Season year (e.g. 2023)."),
      from_date: z.string().optional().describe("Inclusive start date YYYY-MM-DD."),
      to_date: z.string().optional().describe("Inclusive end date YYYY-MM-DD."),
      limit: z.number().int().optional().describe("Max matches to return (default 20)."),
    },
    (args) => {
      const rows = db.findMatches({
        team: args.team,
        opponent: args.opponent,
        competition: args.competition,
        season: args.season,
        fromDate: args.from_date,
        toDate: args.to_date,
        limit: args.limit ?? 20,
      });
      const header = `${args.team ?? "All teams"}${args.opponent ? " vs " + args.opponent : ""}${
        args.competition ? " (" + args.competition + ")" : ""
      }${args.season ? " " + args.season : ""}`;
      return textResult(fmt.formatMatchList(header, rows));
    },
  );

  server.tool(
    "last_match_between",
    "Most recent fixture between two teams, with date and score.",
    {
      team_a: z.string().describe("First team."),
      team_b: z.string().describe("Second team."),
    },
    (args) => {
      const m = db.lastMatchBetween(args.team_a, args.team_b);
      if (!m)
        return textResult(
          `No match found between ${args.team_a} and ${args.team_b}.`,
        );
      return textResult(
        `Last match between ${args.team_a} and ${args.team_b}:\n${fmt.formatMatchLine(m)}`,
      );
    },
  );

  server.tool(
    "team_stats",
    "Win/loss/draw record and goals for a team, optionally for a single season, with home/away split.",
    {
      team: z.string().describe("Team name."),
      season: z.number().int().optional().describe("Restrict to a season year."),
    },
    (args) => {
      const s = db.teamStats(args.team, args.season);
      const label = `${args.team}${args.season ? " (" + args.season + ")" : ""} record`;
      return textResult(fmt.formatTeamStats(s, label));
    },
  );

  server.tool(
    "head_to_head",
    "Head-to-head record and recent matches between two teams.",
    {
      team_a: z.string().describe("First team."),
      team_b: z.string().describe("Second team."),
    },
    (args) => {
      const h2h = db.headToHead(args.team_a, args.team_b);
      return textResult(fmt.formatHeadToHead(h2h));
    },
  );

  server.tool(
    "competitions_for_team",
    "List the distinct competitions a team has appeared in across all datasets.",
    {
      team: z.string().describe("Team name."),
    },
    (args) => {
      const comps = db.competitionsFor(args.team);
      if (comps.length === 0)
        return textResult(`${args.team} not found in any dataset.`);
      return textResult(
        `${args.team} appears in:\n${comps.map((c) => "- " + c).join("\n")}`,
      );
    },
  );

  server.tool(
    "player_search",
    "Search FIFA player database by name, nationality, club, and/or position; sorted by overall rating descending by default.",
    {
      name: z.string().optional(),
      nationality: z.string().optional().describe('e.g. "Brazil".'),
      club: z.string().optional(),
      position: z.string().optional().describe('e.g. "ST", "GK", "LW".'),
      limit: z.number().int().optional().describe("Max players (default 25)."),
    },
    (args) => {
      const players = db.playerSearch({
        name: args.name,
        nationality: args.nationality,
        club: args.club,
        position: args.position,
        limit: args.limit ?? 25,
      });
      const header = "Player search results";
      return textResult(fmt.formatPlayerList(header, players));
    },
  );
  server.tool(
    "top_brazilian_players",
    "Highest-rated Brazilian players in the FIFA dataset.",
    {
      limit: z.number().int().optional().describe("Max players (default 25)."),
    },
    (args) => {
      const players = db.playerSearch({
        nationality: "Brazil",
        limit: args.limit ?? 25,
      });
      return textResult(fmt.formatPlayerList("Top-rated Brazilian players", players));
    },
  );

  server.tool(
    "brazilian_players_by_club",
    "Brazilian players grouped by their club (counts and average rating), sorted by count.",
    {},
    () => {
      const rows = db.brazilianPlayersByClub();
      if (rows.length === 0) return textResult("No Brazilian players found.");
      const body = rows
        .slice(0, 50)
        .map(
          (r) =>
            `- ${r.club}: ${r.count} players (avg rating: ${r.avgRating.toFixed(1)})`,
        )
        .join("\n");
      return textResult(`Brazilian players by club:\n${body}`);
    },
  );

  server.tool(
    "standings",
    "Computed league standings for a competition and season (3-1-0 points).",
    {
      competition: z
        .string()
        .describe('Competition substring, e.g. "Brasileirão".'),
      season: z.number().int().describe("Season year."),
    },
    (args) => {
      const rows = db.standings(args.competition, args.season);
      return textResult(
        `${args.season} ${args.competition} standings (calculated from matches):\n` +
          fmt.formatStandings(rows),
      );
    },
  );

  server.tool(
    "biggest_wins",
    "Largest goal-difference victories, optionally within a competition.",
    {
      competition: z.string().optional(),
      limit: z.number().int().optional().describe("Max (default 10)."),
    },
    (args) => {
      const rows = db.biggestWins(args.limit ?? 10, args.competition);
      return textResult(fmt.formatBiggestWins(rows));
    },
  );

  server.tool(
    "average_goals",
    "Average goals per match plus home/away/draw rates, optionally within a competition.",
    {
      competition: z.string().optional(),
    },
    (args) => {
      const r = db.averageGoals(args.competition);
      return textResult(
        `Average goals${args.competition ? " (" + args.competition + ")" : ""}:\n` +
          fmt.formatAverageGoals(r),
      );
    },
  );

  server.tool(
    "best_record_at_venue",
    "Team with the best record at home or away (win-rate then points).",
    {
      venue: z.enum(["home", "away"]).describe('"home" or "away".'),
      season: z.number().int().optional(),
    },
    (args) => {
      const s = db.bestRecordAtVenue(args.venue, args.season);
      if (!s) return textResult("No matches available.");
      const v = args.venue === "home" ? s.home : s.away;
      const label = `Best ${args.venue} record: ${s.team}`;
      return textResult(fmt.formatTeamStats(s, label) + `\n- ${args.venue} matches: ${v.matches}`);
    },
  );

  return server;
}

/**
 * Load all datasets from `dataDir` (default `data/kaggle` under cwd) and
 * return a ready-to-query SoccerDatabase.
 */
export async function loadDatabase(dataDir = defaultDataDir()): Promise<SoccerDatabase> {
  const [matches, players] = await Promise.all([
    loadAllMatches(dataDir),
    loadFifaPlayers(dataDir),
  ]);
  return new SoccerDatabase(matches, players);
}

/** CLI entrypoint — stdio MCP server. */
async function main(): Promise<void> {
  const db = await loadDatabase();
  const server = buildServer(db);
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

// Run only when invoked directly as the entry point, not when imported by tests.
if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  main().catch((err) => {
    console.error("Fatal:", err);
    process.exit(1);
  });
}
