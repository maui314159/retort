/**
 * brazilian-soccer-mcp / src/server.ts
 *
 * MCP server definition and tool handlers.
 *
 * Context block:
 * Exposes the SoccerStore query engine as ten MCP tools covering the five
 * required capability categories from the spec: match queries, team queries,
 * player queries, competition queries and statistical analysis, plus two
 * discovery helpers (list_teams, list_competitions) and a derbies finder.
 * Each tool handler is a standalone, exported async function taking the
 * validated args plus the store and returning MCP `content` text — this makes
 * them unit-testable without spawning the server. `createServer` wires them to
 * a `McpServer` over stdio. Response text mirrors the example answer formats
 * in the spec (date-first match lines, W/D/L aggregates, points standings).
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import type { Match, Player } from "./types.js";
import { SoccerStore } from "./store.js";

/** MCP text content return shape (type alias so it satisfies the SDK's index-signatured return type). */
export type ToolResult = {
  content: { type: "text"; text: string }[];
};

/** Format a single match as a date-first one-liner. */
export function formatMatchLine(m: Match): string {
  const date = m.date ?? "????-??-??";
  const score =
    m.homeGoal != null && m.awayGoal != null
      ? `${m.homeTeam} ${m.homeGoal}-${m.awayGoal} ${m.awayTeam}`
      : `${m.homeTeam} vs ${m.awayTeam}`;
  const ctx: string[] = [m.competition];
  if (m.round && /^\d+$/.test(m.round)) ctx.push(`Round ${m.round}`);
  else if (m.stage) ctx.push(m.stage);
  else if (m.round) ctx.push(m.round);
  if (m.season != null) ctx.push(`${m.season}`);
  return `- ${date}: ${score} (${ctx.join(", ")})`;
}

function text(body: string): ToolResult {
  return { content: [{ type: "text" as const, text: body }] };
}

/** Truncate a long match list to `limit` lines with an overflow notice. */
function formatMatchList(matches: Match[], limit: number): string {
  const shown = matches.slice(0, limit);
  const lines = shown.map(formatMatchLine);
  if (matches.length > limit) {
    lines.push(`... (${matches.length - limit} more matches)`);
  }
  return lines.join("\n");
}

// ---- Tool handlers ------------------------------------------------------

export async function handleSearchMatches(
  args: {
    team?: string;
    opponent?: string;
    competition?: string;
    season?: number;
    from?: string;
    to?: string;
    venue?: string;
    limit?: number;
  },
  store: SoccerStore,
): Promise<ToolResult> {
  const matches = store.searchMatches(
    {
      team: args.team,
      opponent: args.opponent,
      competition: args.competition,
      season: args.season,
      from: args.from,
      to: args.to,
      venue: args.venue as "home" | "away" | "all" | undefined,
    },
    { sort: "date_desc", limit: args.limit ?? 50 },
  );
  if (matches.length === 0) return text("No matches found for the given criteria.");
  const header = `Found ${matches.length} match(es)`;
  return text(`${header}:\n${formatMatchList(matches, args.limit ?? 50)}`);
}

export async function handleHeadToHead(
  args: { team1: string; team2: string; competition?: string; limit?: number },
  store: SoccerStore,
): Promise<ToolResult> {
  const { matches, team1, team2, team1Wins, team2Wins, draws } = store.headToHead(
    args.team1,
    args.team2,
  );
  if (matches.length === 0) {
    return text(`No matches found between ${args.team1} and ${args.team2}.`);
  }
  const header = `${team1} vs ${team2} (${matches.length} matches in dataset):`;
  const lines = formatMatchList(matches, args.limit ?? 50);
  const summary = `Head-to-head: ${team1} ${team1Wins} wins, ${team2} ${team2Wins} wins, ${draws} draws`;
  return text(`${header}\n${lines}\n${summary}`);
}

export async function handleTeamStats(
  args: {
    team: string;
    competition?: string;
    season?: number;
    venue?: string;
  },
  store: SoccerStore,
): Promise<ToolResult> {
  const stat = store.teamStats(args.team, {
    competition: args.competition,
    season: args.season,
    venue: args.venue as "home" | "away" | "all" | undefined,
  });
  if (stat.matches === 0) {
    return text(`No matches found for ${args.team} with the given filters.`);
  }
  const venueLabel = args.venue ? ` (${args.venue})` : " (all venues)";
  const compLabel = args.competition ? ` ${args.competition}` : "";
  const seasonLabel = args.season != null ? ` ${args.season}` : "";
  const body = [
    `${args.team}${venueLabel}${compLabel}${seasonLabel}:`,
    `- Matches: ${stat.matches}`,
    `- Wins: ${stat.wins}, Draws: ${stat.draws}, Losses: ${stat.losses}`,
    `- Goals For: ${stat.goalsFor}, Goals Against: ${stat.goalsAgainst}`,
    `- Win rate: ${(stat.winRate * 100).toFixed(1)}%`,
  ];
  return text(body.join("\n"));
}

export async function handleSearchPlayers(
  args: {
    name?: string;
    nationality?: string;
    club?: string;
    position?: string;
    positionGroup?: string;
    minOverall?: number;
    brazilianClubsOnly?: boolean;
    sort?: string;
    limit?: number;
  },
  store: SoccerStore,
): Promise<ToolResult> {
  const players = store.searchPlayers({
    name: args.name,
    sort: args.sort as "overall" | "potential" | "age" | "name" | undefined,
    position: args.position,
    positionGroup: args.positionGroup,
    minOverall: args.minOverall,
    brazilianClubsOnly: args.brazilianClubsOnly,
    limit: args.limit ?? 25,
  });
  if (players.length === 0) return text("No players found for the given criteria.");
  const lines = players.map(
    (p) =>
      `- ${p.name} - Overall: ${p.overall ?? "?"}, Potential: ${p.potential ?? "?"}, ` +
      `Position: ${p.position || "?"}, Club: ${p.club}, Nationality: ${p.nationality}`,
  );
  return text(`Found ${players.length} player(s):\n${lines.join("\n")}`);
}

export async function handleCompetitionStandings(
  args: { competition: string; season: number; limit?: number },
  store: SoccerStore,
): Promise<ToolResult> {
  const rows = store.standings(args.competition, args.season);
  if (rows.length === 0) {
    return text(`No standings data for ${args.competition} ${args.season}.`);
  }
  const limit = args.limit ?? 20;
  const shown = rows.slice(0, limit);
  const lines = shown.map((r, i) => {
    const champ = i === 0 ? " - Champion" : "";
    return `${i + 1}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L)${champ}`;
  });
  const header = `${args.season} ${args.competition} Standings (calculated from matches):`;
  let body = `${header}\n${lines.join("\n")}`;
  if (rows.length > limit) body += `\n... (${rows.length - limit} more teams)`;
  return text(body);
}

export async function handleBiggestWins(
  args: { competition?: string; season?: number; limit?: number },
  store: SoccerStore,
): Promise<ToolResult> {
  const matches = store.biggestWins({
    competition: args.competition,
    season: args.season,
    limit: args.limit ?? 10,
  });
  if (matches.length === 0) return text("No matches with scores found.");
  const lines = matches.map((m) => {
    const margin = Math.abs((m.homeGoal ?? 0) - (m.awayGoal ?? 0));
    return `- ${m.date ?? "?"}: ${m.homeTeam} ${m.homeGoal}-${m.awayGoal} ${m.awayTeam} (${m.competition}, margin ${margin})`;
  });
  return text(`Biggest victories:\n${lines.join("\n")}`);
}

export async function handleAverageGoals(
  args: { competition?: string; season?: number },
  store: SoccerStore,
): Promise<ToolResult> {
  const s = store.averageGoals({
    competition: args.competition,
    season: args.season,
  });
  if (s.matches === 0) return text("No matches with scores found for the given criteria.");
  const label =
    (args.competition ?? "All competitions") + (args.season != null ? ` ${args.season}` : "");
  const body = [
    `${label}:`,
    `- Matches: ${s.matches}`,
    `- Average goals per match: ${s.averageGoalsPerMatch.toFixed(2)}`,
    `- Home wins: ${s.homeWins} (${(s.homeWinRate * 100).toFixed(1)}%)`,
    `- Draws: ${s.draws} (${(s.drawRate * 100).toFixed(1)}%)`,
    `- Away wins: ${s.awayWins} (${(s.awayWinRate * 100).toFixed(1)}%)`,
  ];
  return text(body.join("\n"));
}

export async function handleListTeams(
  args: { competition?: string; season?: number; limit?: number },
  store: SoccerStore,
): Promise<ToolResult> {
  const teams = store.listTeams({ competition: args.competition, season: args.season });
  if (teams.length === 0) return text("No teams found for the given criteria.");
  const limit = args.limit ?? 200;
  const shown = teams.slice(0, limit);
  let body = `Teams (${teams.length}):\n${shown.join("\n")}`;
  if (teams.length > limit) body += `\n... (${teams.length - limit} more teams)`;
  return text(body);
}

export async function handleListCompetitions(_args: unknown, store: SoccerStore): Promise<ToolResult> {
  const lines = store.competitions.map((c) => {
    const count = store.competitionCounts[c] ?? 0;
    const seasons = store.competitionSeasons[c];
    const range = seasons ? `${seasons.min}-${seasons.max}` : "n/a";
    return `- ${c}: ${count} matches (seasons ${range})`;
  });
  return text(`Competitions in dataset:\n${lines.join("\n")}`);
}

export async function handleFindDerbies(
  args: { season?: number; competition?: string; limit?: number },
  store: SoccerStore,
): Promise<ToolResult> {
  const matches = store.findDerbies({
    season: args.season,
    competition: args.competition,
    limit: args.limit ?? 50,
  });
  if (matches.length === 0) return text("No derby matches found for the given criteria.");
  return text(`Derbies (${matches.length}):\n${formatMatchList(matches, args.limit ?? 50)}`);
}

// ---- Server wiring ------------------------------------------------------

const VenueSchema = z.enum(["home", "away", "all"]).optional();
const PlayerSortSchema = z.enum(["overall", "potential", "age", "name"]).optional();
const PosGroupSchema = z
  .enum(["goalkeeper", "defender", "midfielder", "forward"])
  .optional();

/** Create and register all tools on a fresh McpServer. */
export function createServer(store: SoccerStore): McpServer {
  const server = new McpServer({
    name: "brazilian-soccer-mcp",
    version: "1.0.0",
  });

  server.registerTool(
    "search_matches",
    {
      description:
        "Search Brazilian soccer matches by team, opponent, competition, season and/or date range. " +
        "Returns date, teams, score and competition for each match.",
      inputSchema: {
        team: z.string().optional().describe("Team name (home, away or either)"),
        opponent: z.string().optional().describe("Opponent team name (use with team)"),
        competition: z
          .string()
          .optional()
          .describe("Competition (Brasileirão, Copa do Brasil, Libertadores, ...)"),
        season: z.number().int().optional().describe("Season year, e.g. 2023"),
        from: z.string().optional().describe("Start date YYYY-MM-DD"),
        to: z.string().optional().describe("End date YYYY-MM-DD"),
        venue: VenueSchema,
        limit: z.number().int().min(1).max(500).optional().describe("Max results (default 50)"),
      },
    },
    async (args) => handleSearchMatches(args, store),
  );

  server.registerTool(
    "head_to_head",
    {
      description:
        "Compare two teams head-to-head: all matches between them plus win/draw/loss summary.",
      inputSchema: {
        team1: z.string(),
        team2: z.string(),
        competition: z.string().optional(),
        limit: z.number().int().min(1).max(500).optional(),
      },
    },
    async (args) => handleHeadToHead(args, store),
  );

  server.registerTool(
    "team_stats",
    {
      description:
        "Aggregate win/draw/loss, goals and win rate for a team, filterable by competition, season and venue.",
      inputSchema: {
        team: z.string(),
        competition: z.string().optional(),
        season: z.number().int().optional(),
        venue: VenueSchema,
      },
    },
    async (args) => handleTeamStats(args, store),
  );

  server.registerTool(
    "search_players",
    {
      description:
        "Search the FIFA player database by name, nationality, club, position, position group or minimum overall rating. " +
        "Brazilian clubs only filter available.",
      inputSchema: {
        name: z.string().optional(),
        nationality: z.string().optional().describe("e.g. Brazil"),
        club: z.string().optional(),
        position: z.string().optional().describe("Position code e.g. ST, GK, CDM"),
        positionGroup: PosGroupSchema,
        minOverall: z.number().int().min(0).max(99).optional(),
        brazilianClubsOnly: z.boolean().optional(),
        sort: PlayerSortSchema,
        limit: z.number().int().min(1).max(500).optional(),
      },
    },
    async (args) => handleSearchPlayers(args, store),
  );

  server.registerTool(
    "competition_standings",
    {
      description:
        "Compute a points-based standings table for a competition and season from match results. " +
        "Best suited to round-robin leagues like the Brasileirão.",
      inputSchema: {
        competition: z.string().describe('e.g. "Brasileirão"'),
        season: z.number().int(),
        limit: z.number().int().min(1).max(100).optional(),
      },
    },
    async (args) => handleCompetitionStandings(args, store),
  );

  server.registerTool(
    "biggest_wins",
    {
      description: "Largest victories (by goal margin) in the dataset, optionally filtered.",
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
        limit: z.number().int().min(1).max(200).optional(),
      },
    },
    async (args) => handleBiggestWins(args, store),
  );

  server.registerTool(
    "average_goals",
    {
      description:
        "Average goals per match plus home-win/draw/away-win rates for a competition and/or season.",
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
      },
    },
    async (args) => handleAverageGoals(args, store),
  );

  server.registerTool(
    "list_teams",
    {
      description: "List distinct teams, optionally filtered by competition and/or season.",
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
        limit: z.number().int().min(1).max(1000).optional(),
      },
    },
    async (args) => handleListTeams(args, store),
  );

  server.registerTool(
    "list_competitions",
    {
      description: "List all competitions in the dataset with match counts and season ranges.",
      inputSchema: {},
    },
    async (args) => handleListCompetitions(args, store),
  );

  server.registerTool(
    "find_derbies",
    {
      description:
        "Find matches between traditional Brazilian derby rivals (Fla-Flu, Majestoso, Grenal, ...), optionally by season/competition.",
      inputSchema: {
        season: z.number().int().optional(),
        competition: z.string().optional(),
        limit: z.number().int().min(1).max(500).optional(),
      },
    },
    async (args) => handleFindDerbies(args, store),
  );

  return server;
}
