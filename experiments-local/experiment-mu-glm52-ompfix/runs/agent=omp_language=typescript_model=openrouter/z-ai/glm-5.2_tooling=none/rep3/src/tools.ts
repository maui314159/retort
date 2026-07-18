/**
 * Brazilian Soccer MCP Server — Tool Definitions
 * -----------------------------------------------------------------------------
 * Context block:
 *   This module registers the MCP tools exposed by the server. Each tool maps
 *   to one of the five required capability categories in the spec:
 *     1. search_matches      — Match Queries (by team, opponent, date range,
 *        competition, season, stage)
 *     2. team_stats           — Team Queries (W/D/L, goals, win rate, venue)
 *     3. head_to_head         — Team Queries (head-to-head comparison)
 *     4. standings            — Competition Queries (computed table + champion)
 *     5. match_statistics     — Statistical Analysis (avg goals, home/away
 *        win rates, biggest wins)
 *     6. biggest_wins         — Statistical Analysis (ranked victories)
 *     7. last_match           — Simple Lookups ("when did X last play Y?")
 *     8. search_players       — Player Queries (name/nationality/club/position)
 *     9. top_players          — Player Queries (ranked by overall)
 *    10. brazilian_players_at_brazilian_clubs — Player Queries (cross-file
 *        Brazilian-clubs grouping)
 *    11. list_competitions    — Discovery (catalog of loaded datasets)
 *
 *   Every tool returns a single `content` text blob produced by the pure
 *   formatters in `format.ts`. The query engine does the work; tools only
 *   translate args ↔ filters and format. Schemas use zod raw shapes passed
 *   to `registerTool`. All tools are read-only.
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { Dataset } from "./data/types.js";
import {
  biggestWins,
  brazilianPlayersAtBrazilianClubs,
  findMatches,
  findPlayers,
  headToHead,
  lastMatch,
  matchStatistics,
  standings,
  teamStats,
} from "./data/query.js";
import {
  formatBiggestWins,
  formatClubBrazilianPlayers,
  formatHeadToHead,
  formatMatch,
  formatMatches,
  formatPlayers,
  formatStandings,
  formatStatistics,
  formatTeamStats,
} from "./data/format.js";

/** Competition keys accepted by filtering tools. */
const COMPETITION_VALUES = [
  "brasileirao",
  "copa-do-brasil",
  "libertadores",
  "brasileirao-historical",
  "serie-a",
  "serie-b",
  "serie-c",
  "copa-do-brasil-ext",
] as const;

/** Register all Brazilian-soccer tools on the given MCP server. */
export function registerTools(server: McpServer, ds: Dataset): void {
  // ----- 1. search_matches -----
  server.registerTool(
    "search_matches",
    {
      title: "Search matches",
      description:
        "Find football matches by team, opponent, venue, competition, season, date range, or stage. Returns a formatted list (newest first).",
      inputSchema: {
        team: z.string().optional().describe("Team name (tolerant: 'Flamengo' matches 'Flamengo-RJ')."),
        opponent: z.string().optional().describe("Opponent team name; combined with team for head-to-head-style filtering."),
        venue: z.enum(["home", "away", "either"]).optional().describe("Venue filter for 'team'."),
        competition: z.enum(COMPETITION_VALUES).optional().describe("Competition to scope to."),
        season: z.number().int().optional().describe("Season year."),
        from: z.string().optional().describe("ISO date YYYY-MM-DD, inclusive lower bound."),
        to: z.string().optional().describe("ISO date YYYY-MM-DD, inclusive upper bound."),
        stage: z.string().optional().describe("Tournament stage, e.g. 'final', 'group stage' (Libertadores)."),
        round: z.string().optional().describe("Round number/label."),
        limit: z.number().int().min(0).optional().describe("Max matches to return (default 50)."),
      },
    },
    (args) => {
      const matches = findMatches(ds, {
        team: args.team,
        opponent: args.opponent,
        venue: args.venue,
        competition: args.competition,
        season: args.season,
        from: args.from,
        to: args.to,
        stage: args.stage,
        round: args.round,
        limit: args.limit ?? 50,
      });
      return text(formatMatches(matches, "Matches"));
    },
  );

  // ----- 2. team_stats -----
  server.registerTool(
    "team_stats",
    {
      title: "Team statistics",
      description:
        "Compute win/draw/loss record, goals scored/conceded, points and win rate for a team, optionally scoped by competition, season, venue and date range.",
      inputSchema: {
        team: z.string().describe("Team name (tolerant normalization applied)."),
        competition: z.enum(COMPETITION_VALUES).optional(),
        season: z.number().int().optional(),
        venue: z.enum(["home", "away", "either"]).optional(),
        from: z.string().optional(),
        to: z.string().optional(),
      },
    },
    (args) => {
      const stats = teamStats(ds, args.team, {
        competition: args.competition,
        season: args.season,
        venue: args.venue,
        from: args.from,
        to: args.to,
      });
      const scope = scopeLabel(args);
      return text(formatTeamStats(stats.team, stats, scope));
    },
  );

  // ----- 3. head_to_head -----
  server.registerTool(
    "head_to_head",
    {
      title: "Head-to-head",
      description:
        "Compare two teams head-to-head across the dataset: wins, draws, goals, and a sample of matches. Handles team-name variations and either venue/order.",
      inputSchema: {
        team1: z.string().describe("First team name."),
        team2: z.string().describe("Second team name."),
        competition: z.enum(COMPETITION_VALUES).optional(),
        season: z.number().int().optional(),
      },
    },
    (args) => {
      const h2h = headToHead(ds, args.team1, args.team2, {
        competition: args.competition,
        season: args.season,
      });
      return text(formatHeadToHead(h2h));
    },
  );

  // ----- 4. standings -----
  server.registerTool(
    "standings",
    {
      title: "Competition standings",
      description:
        "Compute a league standings table (points, W/D/L, goals, GD) from match results, scoped by competition and season. Returns ranked table with the champion.",
      inputSchema: {
        competition: z.enum(COMPETITION_VALUES).describe("Competition to compute standings for."),
        season: z.number().int().describe("Season year."),
      },
    },
    (args) => {
      const rows = standings(ds, { competition: args.competition, season: args.season });
      const title = `Standings — ${args.competition} ${args.season}`;
      return text(formatStandings(rows, title));
    },
  );

  // ----- 5. match_statistics -----
  server.registerTool(
    "match_statistics",
    {
      title: "Match statistics",
      description:
        "Aggregate statistics over a scoped set of matches: average goals, home/away win & draw rates, and biggest home/away wins. Scope by competition and/or season.",
      inputSchema: {
        competition: z.enum(COMPETITION_VALUES).optional(),
        season: z.number().int().optional(),
        team: z.string().optional().describe("Restrict to matches involving this team."),
      },
    },
    (args) => {
      const stats = matchStatistics(ds, {
        competition: args.competition,
        season: args.season,
        team: args.team,
      });
      return text(formatStatistics(stats, scopeLabel(args)));
    },
  );

  // ----- 6. biggest_wins -----
  server.registerTool(
    "biggest_wins",
    {
      title: "Biggest victories",
      description: "List the biggest victory margins in a scoped set of matches (competition/season/team).",
      inputSchema: {
        competition: z.enum(COMPETITION_VALUES).optional(),
        season: z.number().int().optional(),
        team: z.string().optional(),
        limit: z.number().int().min(1).max(100).optional().describe("Number of results (default 10)."),
      },
    },
    (args) => {
      const wins = biggestWins(ds, {
        competition: args.competition,
        season: args.season,
        team: args.team,
      }, args.limit ?? 10);
      return text(formatBiggestWins(wins, "Biggest victories"));
    },
  );

  // ----- 7. last_match -----
  server.registerTool(
    "last_match",
    {
      title: "Last match",
      description: "Find the most recent match involving a team (optionally vs an opponent, scoped by competition/season).",
      inputSchema: {
        team: z.string().describe("Team name."),
        opponent: z.string().optional(),
        competition: z.enum(COMPETITION_VALUES).optional(),
        season: z.number().int().optional(),
      },
    },
    (args) => {
      const m = lastMatch(ds, args.team, {
        opponent: args.opponent,
        competition: args.competition,
        season: args.season,
      });
      return m ? text(formatMatch(m, "Last match")) : text("No match found.");
    },
  );

  // ----- 8. search_players -----
  server.registerTool(
    "search_players",
    {
      title: "Search players",
      description:
        "Search the FIFA player database by name, nationality, club, position and/or minimum overall rating. Results are ranked by overall rating.",
      inputSchema: {
        name: z.string().optional(),
        nationality: z.string().optional().describe("e.g. 'Brazil'."),
        club: z.string().optional(),
        position: z.string().optional().describe("e.g. 'ST', 'GK', 'LW'."),
        minOverall: z.number().int().optional(),
        limit: z.number().int().min(1).optional().describe("Max results (default 20)."),
      },
    },
    (args) => {
      const players = findPlayers(ds, {
        name: args.name,
        nationality: args.nationality,
        club: args.club,
        position: args.position,
        minOverall: args.minOverall,
        limit: args.limit ?? 20,
      });
      return text(formatPlayers(players, "Players"));
    },
  );

  // ----- 9. top_players -----
  server.registerTool(
    "top_players",
    {
      title: "Top players",
      description: "List the highest-rated players, optionally filtered by nationality (e.g. Brazilian players) or club.",
      inputSchema: {
        nationality: z.string().optional(),
        club: z.string().optional(),
        limit: z.number().int().min(1).optional().describe("Number of results (default 10)."),
      },
    },
    (args) => {
      const players = findPlayers(ds, {
        nationality: args.nationality,
        club: args.club,
        limit: args.limit ?? 10,
      });
      const title = args.nationality
        ? `Top ${args.nationality} players`
        : args.club
          ? `Top players at ${args.club}`
          : "Top players";
      return text(formatPlayers(players, title));
    },
  );

  // ----- 10. brazilian_players_at_brazilian_clubs -----
  server.registerTool(
    "brazilian_players_at_brazilian_clubs",
    {
      title: "Brazilian players at Brazilian clubs",
      description: "Group Brazilian players from the FIFA dataset by Brazilian club, with counts and average ratings.",
      inputSchema: {},
    },
    () => text(formatClubBrazilianPlayers(brazilianPlayersAtBrazilianClubs(ds))),
  );

  // ----- 11. list_competitions -----
  server.registerTool(
    "list_competitions",
    {
      title: "List competitions",
      description: "List all loaded datasets/competitions with their seasons and match counts.",
      inputSchema: {},
    },
    () => {
      const lines = ["Loaded competitions:"];
      for (const c of ds.competitions) {
        const seasons = c.seasons.length ? c.seasons.join(", ") : "n/a";
        lines.push(`- ${c.label} [${c.competition}] (${c.source}): ${c.matchCount} matches, seasons: ${seasons}`);
      }
      lines.push(`- Players: ${ds.players.length}`);
      return text(lines.join("\n"));
    },
  );
}

/** Build a short human scope label for a stats call. */
function scopeLabel(args: { competition?: string; season?: number; venue?: string }): string {
  const parts: string[] = [];
  if (args.competition) parts.push(args.competition);
  if (args.season != null) parts.push(String(args.season));
  if (args.venue) parts.push(args.venue);
  return parts.join(" ");
}

/** Wrap a string as a text CallToolResult. */
function text(content: string) {
  return { content: [{ type: "text" as const, text: content }] };
}
