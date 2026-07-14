import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { loadData } from "./loaders.js";
import * as Q from "./queries.js";
import * as Fmt from "./format.js";

const competitionEnum = z.enum([
  "All",
  "Brasileirao",
  "CopaDoBrasil",
  "Libertadores",
  "BRFootball",
  "BrasileiraoHistorico",
]);

const venueEnum = z.enum(["all", "home", "away"]);

const asText = (text: string) => ({
  content: [{ type: "text" as const, text }],
});

export const createServer = (dataDir?: string): McpServer => {
  const data = loadData(dataDir);
  const server = new McpServer({
    name: "brazilian-soccer-mcp",
    version: "2.0.0",
  });

  server.tool(
    "find_matches",
    "Find matches by team, opponent, competition, season, or date range. Returns formatted list of matches.",
    {
      team: z.string().optional().describe("Team name to search for (home or away)"),
      opponent: z.string().optional().describe("Opponent team name (used with team)"),
      home_team: z.string().optional(),
      away_team: z.string().optional(),
      competition: competitionEnum.optional(),
      season: z.union([z.number(), z.literal("All")]).optional(),
      from_date: z.string().optional().describe("ISO date YYYY-MM-DD"),
      to_date: z.string().optional().describe("ISO date YYYY-MM-DD"),
      round: z.string().optional(),
      stage: z.string().optional(),
      limit: z.number().optional().describe("Max results, default 50"),
    },
    async (args) => {
      const matches = Q.filterMatches(data.matches, {
        team: args.team,
        opponent: args.opponent,
        homeTeam: args.home_team,
        awayTeam: args.away_team,
        competition: args.competition as any,
        season: args.season as any,
        fromDate: args.from_date,
        toDate: args.to_date,
        round: args.round,
        stage: args.stage,
        limit: args.limit ?? 50,
      });
      let title = "Matches";
      if (args.team && args.opponent) title = `${args.team} vs ${args.opponent}`;
      else if (args.team) title = `Matches involving ${args.team}`;
      else if (args.competition && args.competition !== "All") title = `Matches in ${args.competition}`;
      return asText(Fmt.formatMatchList(title, matches, matches.length));
    }
  );

  server.tool(
    "get_team_statistics",
    "Get win/loss/draw record, goals, and win rate for a team in a competition, season, and/or venue.",
    {
      team: z.string().describe("Team name"),
      competition: competitionEnum.optional(),
      season: z.union([z.number(), z.literal("All")]).optional(),
      venue: venueEnum.optional(),
    },
    async (args) => {
      const stats = Q.computeTeamStats(data.matches, args.team, {
        competition: args.competition as any,
        season: args.season as any,
        venue: args.venue as any,
      });
      return asText(Fmt.formatTeamStats(stats));
    }
  );

  server.tool(
    "head_to_head",
    "Compare two teams head-to-head: list of matches and aggregate wins/draws/goals.",
    {
      team_a: z.string(),
      team_b: z.string(),
      competition: competitionEnum.optional(),
      season: z.union([z.number(), z.literal("All")]).optional(),
    },
    async (args) => {
      const h = Q.headToHead(data.matches, args.team_a, args.team_b, {
        competition: args.competition as any,
        season: args.season as any,
      });
      return asText(Fmt.formatHeadToHead(h));
    }
  );

  server.tool(
    "last_match_between",
    "Find the most recent match between two teams in the dataset.",
    {
      team_a: z.string(),
      team_b: z.string(),
    },
    async (args) => {
      const m = Q.lastMatchBetween(data.matches, args.team_a, args.team_b);
      return asText(Fmt.formatLastMatch(args.team_a, args.team_b, m));
    }
  );

  server.tool(
    "standings",
    "Calculate competition standings for a season from match results. Points: 3 win / 1 draw.",
    {
      competition: z.enum(["Brasileirao", "CopaDoBrasil", "Libertadores", "BRFootball", "BrasileiraoHistorico"]),
      season: z.number(),
      limit: z.number().optional(),
    },
    async (args) => {
      const standing = Q.calculateStandings(data.matches, args.competition as any, args.season);
      return asText(Fmt.formatStanding(standing, args.limit ?? 20));
    }
  );

  server.tool(
    "biggest_wins",
    "Return the biggest victories (largest goal margins) in the dataset.",
    {
      competition: competitionEnum.optional(),
      season: z.union([z.number(), z.literal("All")]).optional(),
      limit: z.number().optional(),
    },
    async (args) => {
      const matches = Q.biggestWins(data.matches, {
        competition: args.competition as any,
        season: args.season as any,
        limit: args.limit ?? 10,
      });
      return asText(Fmt.formatBiggestWins(matches, args.limit ?? 10));
    }
  );

  server.tool(
    "average_goals",
    "Calculate average goals per match plus home/draw/away win rates for a competition/season.",
    {
      competition: competitionEnum.optional(),
      season: z.union([z.number(), z.literal("All")]).optional(),
    },
    async (args) => {
      const data2 = Q.averageGoals(data.matches, {
        competition: args.competition as any,
        season: args.season as any,
      });
      return asText(Fmt.formatAverageGoals(data2));
    }
  );

  server.tool(
    "search_players",
    "Search FIFA player data by name, nationality, club, position, or minimum overall rating.",
    {
      name: z.string().optional(),
      nationality: z.string().optional(),
      club: z.string().optional(),
      position: z.string().optional().describe("Position code like ST, LW, GK, CDM"),
      min_overall: z.number().optional(),
      limit: z.number().optional().describe("Default 25"),
      sort_by: z.enum(["overall", "potential", "age", "name"]).optional(),
      desc: z.boolean().optional(),
    },
    async (args) => {
      const players = Q.filterPlayers(data.players, {
        name: args.name,
        nationality: args.nationality,
        club: args.club,
        position: args.position,
        minOverall: args.min_overall,
        limit: args.limit ?? 25,
        sortBy: args.sort_by as any,
        desc: args.desc ?? true,
      });
      let title = "Players";
      if (args.nationality) title = `Players from ${args.nationality}`;
      else if (args.club) title = `Players at ${args.club}`;
      else if (args.name) title = `Players matching "${args.name}"`;
      return asText(Fmt.formatPlayerList(title, players));
    }
  );

  server.tool(
    "club_roster",
    "List all FIFA players at a given club with summary statistics.",
    {
      club: z.string(),
      limit: z.number().optional(),
    },
    async (args) => {
      const players = Q.filterPlayers(data.players, {
        club: args.club,
        limit: args.limit ?? 100,
        sortBy: "overall",
        desc: true,
      });
      return asText(Fmt.formatClubRoster(args.club, players));
    }
  );

  server.tool(
    "list_competitions",
    "List all competitions available in the dataset with their seasons and match counts.",
    {},
    async () => {
      const list = Q.listCompetitions(data.matches);
      const lines = list.map(
        (c) => `- ${c.competition} (${c.label}): ${c.matchCount} matches, seasons ${c.seasons.join(", ")}`
      );
      return asText(`Competitions in dataset:\n\n${lines.join("\n")}`);
    }
  );

  server.tool(
    "list_teams",
    "List all team names known in the dataset (normalized).",
    {},
    async () => {
      const teams = Q.listTeams(data.matches);
      return asText(`Teams in dataset (${teams.length}):\n\n${teams.join(", ")}`);
    }
  );

  return server;
};
