/**
 * Brazilian Soccer MCP Server - MCP Tool Layer
 * --------------------------------------------
 * Context: This module wires the query layer into the Model Context Protocol.
 * It registers seven MCP tools that an LLM agent can invoke to answer natural
 * language questions about Brazilian soccer:
 *
 *   search_matches      - Find matches by team/opponent/competition/season/date
 *   head_to_head        - Compare two teams head-to-head
 *   team_statistics     - Win/loss/draw record for a team (per season/competition)
 *   search_players      - Filter & sort the FIFA player database
 *   competition_table   - Computed league standings for a season
 *   aggregate_stats     - Average goals / win rates / biggest victories
 *   list_reference      - List teams, seasons, and competitions in the dataset
 *
 * Each tool returns a plain JSON object so the host LLM can format the answer
 * in natural language (e.g. the example answer formats in the spec).
 *
 * Transport: stdio (the default MCP transport for local tools). The server is
 * started by `node dist/server.js` and is suitable for registration in an MCP
 * client config.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";
import { loadData } from "./loader.js";
import { normalizeTeamName } from "./normalize.js";
import {
  averageGoals,
  bestTeamRecord,
  biggestWins,
  competitionsForTeam,
  findMatches,
  findPlayers,
  findHeadToHeadMatches,
  headToHead,
  standings,
  teamStats,
} from "./queries.js";

/** Tool name constants. */
export const TOOLS = {
  searchMatches: "search_matches",
  headToHead: "head_to_head",
  teamStatistics: "team_statistics",
  searchPlayers: "search_players",
  competitionTable: "competition_table",
  aggregateStats: "aggregate_stats",
  listReference: "list_reference",
} as const;

const COMPETITIONS = [
  "brasileirao",
  "copa-do-brasil",
  "libertadores",
  "brasileirao-historico",
  "ext-stats",
  "any",
] as const;

const searchMatchesSchema = z.object({
  team: z.string().optional(),
  opponent: z.string().optional(),
  competition: z.enum(COMPETITIONS).optional(),
  season: z.number().int().optional(),
  startDate: z.string().optional().describe("ISO date YYYY-MM-DD"),
  endDate: z.string().optional().describe("ISO date YYYY-MM-DD"),
  limit: z.number().int().positive().optional(),
});

const headToHeadSchema = z.object({
  teamA: z.string(),
  teamB: z.string(),
});

const teamStatsSchema = z.object({
  team: z.string(),
  season: z.number().int().optional(),
  competition: z.enum(COMPETITIONS).optional(),
});

const searchPlayersSchema = z.object({
  name: z.string().optional(),
  nationality: z.string().optional(),
  club: z.string().optional(),
  position: z.string().optional(),
  minOverall: z.number().int().optional(),
  limit: z.number().int().positive().optional(),
  sortBy: z.enum(["overall", "potential", "age", "name"]).optional(),
  descending: z.boolean().optional(),
});

const competitionTableSchema = z.object({
  competition: z.enum(COMPETITIONS),
  season: z.number().int(),
  limit: z.number().int().positive().optional(),
});

const aggregateStatsSchema = z.object({
  competition: z.enum(COMPETITIONS).optional(),
  season: z.number().int().optional(),
  team: z.string().optional(),
  metric: z
    .enum(["averages", "biggest_wins", "best_record"])
    .optional()
    .describe("Which aggregate to return. Defaults to 'averages'."),
  venue: z.enum(["home", "away"]).optional(),
  limit: z.number().int().positive().optional(),
});

const listReferenceSchema = z.object({
  kind: z
    .enum(["teams", "seasons", "competitions"])
    .optional()
    .describe("Which reference list to return. Defaults to 'teams'."),
  query: z.string().optional().describe("Substring filter for teams."),
});

/** Build the MCP server with all tools registered. */
export function createServer() {
  const data = loadData();

  const server = new Server(
    { name: "brazilian-soccer-mcp", version: "2.0.0" },
    { capabilities: { tools: {} } },
  );

  server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: [
      {
        name: TOOLS.searchMatches,
        description:
          "Search Brazilian soccer matches across all datasets (Brasileirão, Copa do Brasil, Libertadores, historical Brasileirão, extended stats). Supports filtering by team, opponent, competition, season, and date range.",
        inputSchema: {
          type: "object",
          properties: {
            team: { type: "string" },
            opponent: { type: "string" },
            competition: {
              type: "string",
              enum: COMPETITIONS,
              description:
                "brasileirao | copa-do-brasil | libertadores | brasileirao-historico | ext-stats | any",
            },
            season: { type: "integer" },
            startDate: { type: "string" },
            endDate: { type: "string" },
            limit: { type: "integer" },
          },
        },
      },
      {
        name: TOOLS.headToHead,
        description:
          "Compare two teams head-to-head across all matches in the dataset.",
        inputSchema: {
          type: "object",
          required: ["teamA", "teamB"],
          properties: {
            teamA: { type: "string" },
            teamB: { type: "string" },
          },
        },
      },
      {
        name: TOOLS.teamStatistics,
        description:
          "Compute win/loss/draw, goals, and points for a team, optionally filtered by season or competition.",
        inputSchema: {
          type: "object",
          required: ["team"],
          properties: {
            team: { type: "string" },
            season: { type: "integer" },
            competition: { type: "string", enum: COMPETITIONS },
          },
        },
      },
      {
        name: TOOLS.searchPlayers,
        description:
          "Search the FIFA player database. Filter by name, nationality (e.g. 'Brazil'), club, position, or minimum overall rating; sort by overall/potential/age/name.",
        inputSchema: {
          type: "object",
          properties: {
            name: { type: "string" },
            nationality: { type: "string" },
            club: { type: "string" },
            position: { type: "string" },
            minOverall: { type: "integer" },
            limit: { type: "integer" },
            sortBy: { type: "string", enum: ["overall", "potential", "age", "name"] },
            descending: { type: "boolean" },
          },
        },
      },
      {
        name: TOOLS.competitionTable,
        description:
          "Compute the standings table for a competition season from match results (points = 3*W + D, sorted by points, wins, goal difference, goals for).",
        inputSchema: {
          type: "object",
          required: ["competition", "season"],
          properties: {
            competition: { type: "string", enum: COMPETITIONS },
            season: { type: "integer" },
            limit: { type: "integer" },
          },
        },
      },
      {
        name: TOOLS.aggregateStats,
        description:
          "Aggregate statistics: 'averages' (avg goals/match, home/draw/away win rates), 'biggest_wins' (largest victory margins), or 'best_record' (team with the most points).",
        inputSchema: {
          type: "object",
          properties: {
            competition: { type: "string", enum: COMPETITIONS },
            season: { type: "integer" },
            team: { type: "string" },
            metric: {
              type: "string",
              enum: ["averages", "biggest_wins", "best_record"],
            },
            venue: { type: "string", enum: ["home", "away"] },
            limit: { type: "integer" },
          },
        },
      },
      {
        name: TOOLS.listReference,
        description:
          "List reference data: 'teams' (all known teams, optional substring filter), 'seasons', or 'competitions'.",
        inputSchema: {
          type: "object",
          properties: {
            kind: { type: "string", enum: ["teams", "seasons", "competitions"] },
            query: { type: "string" },
          },
        },
      },
    ],
  }));

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    try {
      switch (name) {
        case TOOLS.searchMatches: {
          const parsed = searchMatchesSchema.parse(args ?? {});
          const matches = findMatches(data, parsed);
          return text({
            count: matches.length,
            matches: matches.map(summarizeMatch),
          });
        }
        case TOOLS.headToHead: {
          const parsed = headToHeadSchema.parse(args ?? {});
          const h2h = headToHead(data, parsed.teamA, parsed.teamB);
          return text({
            teamA: h2h.teamA,
            teamB: h2h.teamB,
            matches: h2h.matches,
            teamAWins: h2h.teamAWins,
            teamBWins: h2h.teamBWins,
            draws: h2h.draws,
            teamAGoals: h2h.teamAGoals,
            teamBGoals: h2h.teamBGoals,
            recent: h2h.recent.slice(0, 20).map(summarizeMatch),
          });
        }
        case TOOLS.teamStatistics: {
          const parsed = teamStatsSchema.parse(args ?? {});
          const stats = teamStats(data, parsed.team, {
            season: parsed.season,
            competition: parsed.competition && parsed.competition !== "any" ? parsed.competition : undefined,
          });
          return text({
            team: stats.team,
            displayName: data.teamDisplay.get(stats.team) ?? stats.team,
            matches: stats.matches,
            wins: stats.wins,
            draws: stats.draws,
            losses: stats.losses,
            goalsFor: stats.goalsFor,
            goalsAgainst: stats.goalsAgainst,
            goalDifference: stats.goalDifference,
            points: stats.points,
            home: stats.home,
            away: stats.away,
          });
        }
        case TOOLS.searchPlayers: {
          const parsed = searchPlayersSchema.parse(args ?? {});
          const players = findPlayers(data, parsed);
          return text({
            count: players.length,
            players: players.map((p) => ({
              id: p.id,
              name: p.name,
              age: p.age,
              nationality: p.nationality,
              overall: p.overall,
              potential: p.potential,
              club: p.club,
              position: p.position,
              jerseyNumber: p.jerseyNumber,
            })),
          });
        }
        case TOOLS.competitionTable: {
          const parsed = competitionTableSchema.parse(args ?? {});
          const table = standings(
            data,
            parsed.competition,
            parsed.season,
            parsed.limit,
          );
          return text({
            competition: parsed.competition,
            season: parsed.season,
            standings: table.map((s) => ({
              ...s,
              displayName: data.teamDisplay.get(s.team) ?? s.team,
            })),
          });
        }
        case TOOLS.aggregateStats: {
          const parsed = aggregateStatsSchema.parse(args ?? {});
          const metric = parsed.metric ?? "averages";
          let matches = data.matches;
          if (parsed.competition && parsed.competition !== "any")
            matches = matches.filter((m) => m.competition === parsed.competition);
          if (parsed.season) matches = matches.filter((m) => m.season === parsed.season);
          if (parsed.team) {
            const t = normalizeTeamName(parsed.team);
            matches = matches.filter(
              (m) => m.homeTeam === t || m.awayTeam === t,
            );
          }
          if (metric === "averages") {
            return text(averageGoals(matches));
          }
          if (metric === "biggest_wins") {
            const bw = biggestWins(matches, parsed.limit ?? 10);
            return text({
              biggestWins: bw.map((b) => ({
                goalDifference: b.goalDifference,
                match: summarizeMatch(b.match),
              })),
            });
          }
          // best_record
          const best = bestTeamRecord(data, matches, parsed.venue);
          return text(
            best
              ? {
                  team: best.team,
                  displayName: data.teamDisplay.get(best.team) ?? best.team,
                  stats: best.stats,
                }
              : { team: null, stats: null },
          );
        }
        case TOOLS.listReference: {
          const parsed = listReferenceSchema.parse(args ?? {});
          const kind = parsed.kind ?? "teams";
          if (kind === "teams") {
            const q = parsed.query?.toLowerCase() ?? "";
            const teams = data.teams.filter((t) => !q || t.includes(q));
            return text({
              kind: "teams",
              count: teams.length,
              teams: teams.map((t) => ({
                key: t,
                displayName: data.teamDisplay.get(t) ?? t,
              })),
            });
          }
          if (kind === "seasons") {
            return text({ kind: "seasons", seasons: data.seasons });
          }
          return text({ kind: "competitions", competitions: data.competitions });
        }
        default:
          return text({ error: `Unknown tool: ${name}` }, true);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return text({ error: message }, true);
    }
  });

  return server;
}

function summarizeMatch(m: import("./types.js").Match) {
  return {
    date: m.date,
    homeTeam: m.homeTeam,
    awayTeam: m.awayTeam,
    homeTeamRaw: m.homeTeamRaw,
    awayTeamRaw: m.awayTeamRaw,
    homeGoal: m.homeGoal,
    awayGoal: m.awayGoal,
    season: m.season,
    competition: m.competition,
    competitionLabel: m.competitionLabel,
    round: m.round,
    stadium: m.stadium,
    winner: m.winner,
  };
}

function text(obj: unknown, isError = false) {
  return {
    content: [
      {
        type: "text" as const,
        text: JSON.stringify(obj, null, 2),
      },
    ],
    isError,
  };
}

/** Entry point: connect a stdio transport to the server. */
export async function runStdio() {
  const server = createServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
}
