/**
 * Brazilian Soccer MCP Server — MCP tool layer
 * --------------------------------------------
 * Context block:
 *   Pure, side-effect-free module that defines the MCP tool schemas and a
 *   dispatcher mapping tool names + arguments to query-engine calls. Split out
 *   of index.ts so unit tests can exercise dispatch without starting the stdio
 *   transport. index.ts imports `createDispatcher`/`toolDefinitions` here and
 *   wires them to the Server.
 */

import type { Dataset } from "./loader.js";
import {
  bestRecord,
  goalStats,
  headToHead,
  queryMatches,
  queryPlayers,
  resolveTeam,
  standings,
  teamStats,
  topScoringTeams,
} from "./queries.js";

export interface ToolDef {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
}

/** The nine MCP tools exposed to the LLM. */
export function toolDefinitions(): ToolDef[] {
  return [
    {
      name: "search_matches",
      description:
        "Search Brazilian soccer match data by team, opponent, home/away team, competition, season, date range, stage or round. Returns a list of matches with date, scores, competition and round.",
      inputSchema: {
        type: "object",
        properties: {
          team: { type: "string", description: "Team name (home or away)." },
          opponent: { type: "string", description: "Opponent team name; pair with team for head-to-head match lists." },
          homeTeam: { type: "string" },
          awayTeam: { type: "string" },
          competition: { type: "string", description: "e.g. Brasileirão, Copa do Brasil, Copa Libertadores, Serie A, Serie B." },
          season: { type: "integer", description: "Year, e.g. 2023." },
          startDate: { type: "string", description: "ISO date YYYY-MM-DD." },
          endDate: { type: "string", description: "ISO date YYYY-MM-DD." },
          stage: { type: "string", description: "Tournament stage (Libertadores), e.g. final, semifinals, group stage." },
          round: { type: "string" },
          limit: { type: "integer", description: "Max results (default 50)." },
        },
      },
    },
    {
      name: "team_statistics",
      description:
        "Return aggregate statistics (wins, draws, losses, goals for/against, points) for a team, optionally filtered by season, competition and home/away.",
      inputSchema: {
        type: "object",
        properties: {
          team: { type: "string" },
          season: { type: "integer" },
          competition: { type: "string" },
          homeAway: { type: "string", enum: ["home", "away", "all"] },
        },
        required: ["team"],
      },
    },
    {
      name: "head_to_head",
      description: "Compare two teams head-to-head: wins, draws, goals across all matches (optionally a single season).",
      inputSchema: {
        type: "object",
        properties: {
          teamA: { type: "string" },
          teamB: { type: "string" },
          season: { type: "integer" },
        },
        required: ["teamA", "teamB"],
      },
    },
    {
      name: "search_players",
      description: "Search the FIFA player dataset by name, nationality, club, position and minimum overall rating. Sort by overall/potential/age/name.",
      inputSchema: {
        type: "object",
        properties: {
          name: { type: "string" },
          nationality: { type: "string", description: "e.g. Brazil." },
          club: { type: "string" },
          position: { type: "string", description: "e.g. ST, LW, GK, CDM." },
          minOverall: { type: "integer" },
          sortBy: { type: "string", enum: ["overall", "potential", "age", "name"] },
          limit: { type: "integer" },
        },
      },
    },
    {
      name: "competition_standings",
      description: "Compute a league table (standings) for a competition and season from match results. Points are 3-for-a-win; sorted by points, goal difference, goals for.",
      inputSchema: {
        type: "object",
        properties: {
          competition: { type: "string" },
          season: { type: "integer" },
        },
      },
    },
    {
      name: "goal_statistics",
      description: "Aggregate goal statistics: average goals per match, home/away/draw win rates, and biggest victories (margin >= 4).",
      inputSchema: {
        type: "object",
        properties: {
          competition: { type: "string" },
          season: { type: "integer" },
          team: { type: "string" },
        },
      },
    },
    {
      name: "best_record",
      description: "Top 5 teams by record in a competition/season, split by home or away.",
      inputSchema: {
        type: "object",
        properties: {
          competition: { type: "string" },
          season: { type: "integer" },
          homeAway: { type: "string", enum: ["home", "away"] },
        },
        required: ["homeAway"],
      },
    },
    {
      name: "top_scoring_teams",
      description: "Teams ranked by total goals scored in a competition/season.",
      inputSchema: {
        type: "object",
        properties: {
          competition: { type: "string" },
          season: { type: "integer" },
          limit: { type: "integer" },
        },
      },
    },
    {
      name: "resolve_team",
      description: "Normalise a free-text team name to its canonical key and display name. Useful to confirm a team exists before deeper queries.",
      inputSchema: {
        type: "object",
        properties: { name: { type: "string" } },
        required: ["name"],
      },
    },
  ];
}

function asString(v: unknown): string | undefined {
  return typeof v === "string" && v.length > 0 ? v : undefined;
}

function asInt(v: unknown): number | undefined {
  if (typeof v === "number") return v;
  if (typeof v === "string" && /^\d+$/.test(v)) return parseInt(v, 10);
  return undefined;
}

/** Create a dispatcher bound to a dataset. Returns JSON-serialisable results. */
export function createDispatcher(ds: Dataset) {
  return function handleTool(name: string, args: Record<string, unknown>): unknown {
    switch (name) {
      case "search_matches":
        return queryMatches(ds, {
          team: asString(args.team),
          opponent: asString(args.opponent),
          homeTeam: asString(args.homeTeam),
          awayTeam: asString(args.awayTeam),
          competition: asString(args.competition),
          season: asInt(args.season),
          startDate: asString(args.startDate),
          endDate: asString(args.endDate),
          stage: asString(args.stage),
          round: asString(args.round),
          limit: asInt(args.limit) ?? 50,
        });
      case "team_statistics":
        return teamStats(ds, {
          team: asString(args.team) ?? "",
          season: asInt(args.season),
          competition: asString(args.competition),
          homeAway: (asString(args.homeAway) as "home" | "away" | "all") ?? "all",
        });
      case "head_to_head":
        return headToHead(ds, asString(args.teamA) ?? "", asString(args.teamB) ?? "", asInt(args.season));
      case "search_players":
        return queryPlayers(ds, {
          name: asString(args.name),
          nationality: asString(args.nationality),
          club: asString(args.club),
          position: asString(args.position),
          minOverall: asInt(args.minOverall),
          sortBy: asString(args.sortBy) as "overall" | "potential" | "age" | "name" | undefined,
          limit: asInt(args.limit) ?? 20,
        });
      case "competition_standings":
        return standings(ds, {
          competition: asString(args.competition),
          season: asInt(args.season),
        });
      case "goal_statistics":
        return goalStats(ds, {
          competition: asString(args.competition),
          season: asInt(args.season),
          team: asString(args.team),
        });
      case "best_record":
        return bestRecord(ds, {
          competition: asString(args.competition),
          season: asInt(args.season),
          homeAway: (asString(args.homeAway) as "home" | "away") ?? "home",
        });
      case "top_scoring_teams":
        return topScoringTeams(ds, {
          competition: asString(args.competition),
          season: asInt(args.season),
          limit: asInt(args.limit) ?? 10,
        });
      case "resolve_team":
        return resolveTeam(ds, asString(args.name) ?? "");
      default:
        return { error: `Unknown tool: ${name}` };
    }
  };
}
