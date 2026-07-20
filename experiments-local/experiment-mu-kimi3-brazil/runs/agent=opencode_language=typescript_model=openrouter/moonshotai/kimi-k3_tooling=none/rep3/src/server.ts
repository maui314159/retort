/**
 * MCP server exposing the Brazilian soccer knowledge graph as tools.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import type { Match, Player } from "./types.js";
import type { AppContext } from "./context.js";

/* ------------------------------------------------------------------ */
/* Formatting helpers                                                   */
/* ------------------------------------------------------------------ */

function fmtMatch(m: Match): Record<string, unknown> {
  return {
    date: m.date,
    season: m.season,
    competition: m.competition,
    round: m.round,
    stage: m.stage,
    home: m.homeTeam.name,
    away: m.awayTeam.name,
    score:
      m.homeGoals != null && m.awayGoals != null
        ? `${m.homeGoals}-${m.awayGoals}`
        : "not played",
    homeGoals: m.homeGoals,
    awayGoals: m.awayGoals,
    arena: m.arena,
  };
}

function fmtPlayer(p: Player): Record<string, unknown> {
  return {
    name: p.name,
    age: p.age,
    nationality: p.nationality,
    club: p.club,
    position: p.position,
    overall: p.overall,
    potential: p.potential,
    jerseyNumber: p.jerseyNumber,
  };
}

function ok(data: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
  };
}

function err(message: string) {
  return {
    isError: true,
    content: [{ type: "text" as const, text: message }],
  };
}

/* ------------------------------------------------------------------ */
/* Server factory                                                       */
/* ------------------------------------------------------------------ */

export function createServer(ctx: AppContext): McpServer {
  const q = ctx.queries;
  const server = new McpServer({
    name: "brazilian-soccer-mcp",
    version: "1.0.0",
  });

  server.registerResource(
    "dataset-overview",
    "soccer://overview",
    { description: "Summary of the loaded Brazilian soccer datasets", mimeType: "application/json" },
    async (uri) => ({
      contents: [
        {
          uri: uri.href,
          mimeType: "application/json",
          text: JSON.stringify(
            q.overview(ctx.dataset.sourceRowCounts, ctx.dataset.duplicateCounts),
            null,
            2,
          ),
        },
      ],
    }),
  );

  server.registerTool(
    "dataset_overview",
    {
      description:
        "Overview of the loaded Brazilian soccer datasets: row counts per source CSV, unique match count, team/player counts, competitions and season coverage.",
      inputSchema: {},
    },
    async () => ok(q.overview(ctx.dataset.sourceRowCounts, ctx.dataset.duplicateCounts)),
  );

  server.registerTool(
    "find_matches",
    {
      description:
        "Find soccer matches by team, opponent, competition, season, date range, venue, round or stage. Examples: 'Flamengo vs Fluminense' -> team=Flamengo, opponent=Fluminense; 'Palmeiras in 2023' -> team=Palmeiras, season=2023.",
      inputSchema: {
        team: z.string().optional().describe("Team name (any naming variant, e.g. 'Flamengo', 'Flamengo-RJ')"),
        opponent: z.string().optional().describe("Second team for head-to-head style filtering"),
        competition: z.string().optional().describe("Competition: 'Brasileirão Série A/B/C', 'Copa do Brasil', 'Copa Libertadores' (loose matching)"),
        season: z.number().int().optional().describe("Season year, e.g. 2023"),
        from: z.string().optional().describe("Start date inclusive, ISO yyyy-mm-dd"),
        to: z.string().optional().describe("End date inclusive, ISO yyyy-mm-dd"),
        venue: z.enum(["home", "away", "any"]).optional().describe("Restrict to home or away matches of `team`"),
        round: z.string().optional().describe("Round number as string (league/cup)"),
        stage: z.string().optional().describe("Libertadores stage: 'group stage', 'round of 16', 'quarterfinals', 'semifinals', 'final'"),
        limit: z.number().int().optional().describe("Max matches to return (default 50, max 500)"),
      },
    },
    async (args) => {
      const matches = q.findMatches(args);
      return ok({ count: matches.length, matches: matches.map(fmtMatch) });
    },
  );

  server.registerTool(
    "head_to_head",
    {
      description:
        "Head-to-head record between two teams across all (or one) competitions: match list plus wins/draws/losses and goals summary.",
      inputSchema: {
        teamA: z.string().describe("First team name"),
        teamB: z.string().describe("Second team name"),
        competition: z.string().optional().describe("Optional competition filter"),
      },
    },
    async ({ teamA, teamB, competition }) => {
      const h2h = q.headToHead(teamA, teamB, competition);
      return ok({
        ...h2h.summary,
        teamA: h2h.teamA,
        teamB: h2h.teamB,
        matches: h2h.matches.map(fmtMatch),
      });
    },
  );

  server.registerTool(
    "team_record",
    {
      description:
        "Win/draw/loss record for a team, optionally filtered by season, competition and venue (home/away). Answers questions like 'Corinthians home record in 2022'.",
      inputSchema: {
        team: z.string().describe("Team name"),
        season: z.number().int().optional(),
        competition: z.string().optional(),
        venue: z.enum(["home", "away", "any"]).optional(),
      },
    },
    async ({ team, season, competition, venue }) =>
      ok(q.teamRecord(team, { season, competition, venue })),
  );

  server.registerTool(
    "team_competitions",
    {
      description:
        "List the competitions (with seasons and match counts) a team has played in, e.g. 'What competitions has Palmeiras played in?'.",
      inputSchema: { team: z.string().describe("Team name") },
    },
    async ({ team }) => ok(q.teamCompetitions(team)),
  );

  server.registerTool(
    "league_standings",
    {
      description:
        "Calculate a league table (points, W/D/L, goals) from match results for a season. Default competition: Brasileirão Série A. Marks champion and relegation zone (Série A, 20-team seasons).",
      inputSchema: {
        season: z.number().int().describe("Season year, e.g. 2019"),
        competition: z.string().optional().describe("Competition (default 'Brasileirão Série A')"),
      },
    },
    async ({ season, competition }) => {
      const table = q.standings(season, competition);
      if (table.length === 0) return err(`No played matches found for season ${season} in ${competition ?? "Brasileirão Série A"}.`);
      return ok(table);
    },
  );

  server.registerTool(
    "cup_finals",
    {
      description:
        "Copa do Brasil final-round matches per season (the last round played that season, usually two legs).",
      inputSchema: { season: z.number().int().optional() },
    },
    async ({ season }) => {
      const finals = q.cupFinals(season);
      return ok({ count: finals.length, matches: finals.map(fmtMatch) });
    },
  );

  server.registerTool(
    "search_players",
    {
      description:
        "Search FIFA players by name, nationality, club and/or position. Position accepts FIFA codes (ST, CAM, GK...) or groups: forward, midfielder, defender, goalkeeper.",
      inputSchema: {
        name: z.string().optional().describe("Substring of player name (accent-insensitive)"),
        nationality: z.string().optional().describe("e.g. 'Brazil'"),
        club: z.string().optional().describe("Club name (e.g. 'Flamengo', 'Grêmio')"),
        position: z.string().optional().describe("FIFA position code or group (forward/midfielder/defender/goalkeeper)"),
        minOverall: z.number().int().optional().describe("Minimum FIFA overall rating"),
        brazilianClubsOnly: z.boolean().optional().describe("Only players at Brazilian clubs"),
        limit: z.number().int().optional().describe("Max results (default 20)"),
      },
    },
    async (args) => {
      const players = q.searchPlayers(args);
      return ok({ count: players.length, players: players.map(fmtPlayer) });
    },
  );

  server.registerTool(
    "top_players",
    {
      description:
        "Highest-rated FIFA players, filterable by nationality, club or position. Example: 'top Brazilian players' -> nationality=Brazil.",
      inputSchema: {
        nationality: z.string().optional(),
        club: z.string().optional(),
        position: z.string().optional(),
        brazilianClubsOnly: z.boolean().optional(),
        limit: z.number().int().optional().describe("Max results (default 10)"),
      },
    },
    async (args) => {
      const players = q.searchPlayers({ ...args, limit: args.limit ?? 10, sortByOverall: true });
      return ok({ count: players.length, players: players.map(fmtPlayer) });
    },
  );

  server.registerTool(
    "players_by_club_summary",
    {
      description:
        "Count and average rating of players of a nationality grouped by club (e.g. 'Brazilian players at Brazilian clubs').",
      inputSchema: {
        nationality: z.string().describe("e.g. 'Brazil'"),
        brazilianClubsOnly: z.boolean().optional(),
      },
    },
    async ({ nationality, brazilianClubsOnly }) =>
      ok(q.playersByClubSummary(nationality, brazilianClubsOnly ?? true)),
  );

  server.registerTool(
    "competition_stats",
    {
      description:
        "Aggregate statistics for a competition/season: matches played, total/average goals, home/draw/away win rates.",
      inputSchema: {
        competition: z.string().optional().describe("Omit for all competitions combined"),
        season: z.number().int().optional(),
      },
    },
    async (args) => ok(q.competitionStats(args)),
  );

  server.registerTool(
    "biggest_wins",
    {
      description: "Largest victory margins in the dataset, optionally filtered by competition/season.",
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
        limit: z.number().int().optional().describe("Default 10"),
      },
    },
    async (args) => ok(q.biggestWins(args).map(fmtMatch)),
  );

  server.registerTool(
    "best_home_records",
    {
      description: "Teams with the best home records (by win rate, min 10 home matches).",
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
        limit: z.number().int().optional(),
        minMatches: z.number().int().optional(),
      },
    },
    async (args) => ok(q.bestHomeRecords(args)),
  );

  server.registerTool(
    "best_away_records",
    {
      description: "Teams with the best away records (by win rate, min 10 away matches).",
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
        limit: z.number().int().optional(),
        minMatches: z.number().int().optional(),
      },
    },
    async (args) => ok(q.bestAwayRecords(args)),
  );

  server.registerTool(
    "top_scoring_teams",
    {
      description: "Teams with the most goals scored in a season/competition (e.g. 'Which team scored the most goals in Série A 2023?').",
      inputSchema: {
        season: z.number().int().optional(),
        competition: z.string().optional(),
        limit: z.number().int().optional().describe("Default 10"),
      },
    },
    async (args) => ok(q.topScoringTeams(args)),
  );

  return server;
}
