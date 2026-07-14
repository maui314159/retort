/**
 * Brazilian Soccer MCP Server — Tool registry.
 *
 * Context block
 * -------------
 * Exposes the five required query categories as MCP tools. Each tool is a thin
 * wrapper around an exported, pure handler function (`*Handler`) that takes a
 * typed args object plus the loaded `Dataset` and returns the answer text.
 * Keeping handlers separate from the MCP `server.tool()` registration means
 * the BDD suite can exercise the exact tool logic without spinning up a
 * transport, while `registerTools` wires them to the MCP server for real
 * clients (Claude Desktop, etc.).
 *
 * Tools:
 *   - search_matches        : find matches by team / opponent / competition / season / date range
 *   - team_statistics       : win/loss/draw record, goals, optional venue + competition split
 *   - compare_teams         : head-to-head + parallel record comparison
 *   - search_players        : FIFA player search by name/nationality/club/position/rating
 *   - competition_standings : computed standings, champion, relegation
 *   - match_statistics      : avg goals, home/away win rates, biggest victories
 *   - list_teams            : enumerate known teams (helps LLM disambiguate names)
 *   - list_competitions     : enumerate competitions + seasons present in data
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { Dataset } from "./data/loader.js";
import {
  biggestWins,
  findMatches,
  findPlayers,
  formatHeadToHead,
  formatMatch,
  formatPlayer,
  formatStandings,
  formatTeamRecord,
  headToHead,
  matchStats,
  resolveTeam,
  standings,
  teamRecord,
} from "./data/query.js";
import type { Competition } from "./data/types.js";

const COMPETITIONS: Competition[] = [
  "Brasileirão",
  "Copa do Brasil",
  "Copa Libertadores",
  "Historical Brasileirão",
  "Other",
];

/** Shared zod enum for competition filters across tools. */
const competitionEnum = z.enum([
  "Brasileirão",
  "Copa do Brasil",
  "Copa Libertadores",
  "Historical Brasileirão",
  "Other",
  "all",
]);

function asComp(v: string | undefined): Competition | "all" {
  return (v as Competition | "all") ?? "all";
}

/** Wrap a plain-text answer as an MCP CallToolResult payload. */
function textResult(text: string): { content: [{ type: "text"; text: string }] } {
  return { content: [{ type: "text", text }] };
}

// ---- search_matches ---------------------------------------------------------

export interface SearchMatchesArgs {
  team?: string;
  opponent?: string;
  competition?: string;
  season?: number;
  start_date?: string;
  end_date?: string;
  limit?: number;
}

export function searchMatchesHandler(ds: Dataset, args: SearchMatchesArgs): string {
  const results = findMatches(ds, {
    team: args.team,
    opponent: args.opponent,
    competition: asComp(args.competition),
    season: args.season,
    startDate: args.start_date,
    endDate: args.end_date,
    limit: args.limit ?? 50,
  });
  if (results.length === 0) return "No matches found for the given criteria.";
  return `Found ${results.length} match(es):\n` + results.map(formatMatch).join("\n");
}

// ---- team_statistics --------------------------------------------------------

export interface TeamStatisticsArgs {
  team: string;
  competition?: string;
  season?: number;
  venue?: "home" | "away" | "any";
}

export function teamStatisticsHandler(ds: Dataset, args: TeamStatisticsArgs): string {
  const matches = findMatches(ds, {
    team: args.team,
    competition: asComp(args.competition),
    season: args.season,
  });
  const resolved = resolveTeam(ds, args.team) ?? args.team;
  const rec = teamRecord(matches, resolved, args.venue === "any" || !args.venue ? undefined : args.venue);
  const labelParts = [
    resolved,
    args.season ? String(args.season) : undefined,
    args.competition && args.competition !== "all" ? args.competition : undefined,
    args.venue && args.venue !== "any" ? `${args.venue} record` : "record",
  ];
  return formatTeamRecord(rec, labelParts.filter(Boolean).join(" — "));
}

// ---- compare_teams ----------------------------------------------------------

export interface CompareTeamsArgs {
  team_a: string;
  team_b: string;
  competition?: string;
}

export function compareTeamsHandler(ds: Dataset, args: CompareTeamsArgs): string {
  const h2h = headToHead(ds, args.team_a, args.team_b);
  const comp = asComp(args.competition);
  const recA = teamRecord(findMatches(ds, { team: args.team_a, competition: comp }), h2h.teamA);
  const recB = teamRecord(findMatches(ds, { team: args.team_b, competition: comp }), h2h.teamB);
  return [
    formatHeadToHead(h2h),
    "",
    formatTeamRecord(recA, `${h2h.teamA} overall`),
    "",
    formatTeamRecord(recB, `${h2h.teamB} overall`),
  ].join("\n");
}

// ---- search_players ---------------------------------------------------------

export interface SearchPlayersArgs {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  min_overall?: number;
  sort_by?: "overall" | "potential" | "age" | "name";
  limit?: number;
}

export function searchPlayersHandler(ds: Dataset, args: SearchPlayersArgs): string {
  const results = findPlayers(ds, {
    name: args.name,
    nationality: args.nationality,
    club: args.club,
    position: args.position,
    minOverall: args.min_overall,
    sortBy: args.sort_by,
    limit: args.limit ?? 25,
  });
  if (results.length === 0) return "No players found matching the criteria.";
  return `Found ${results.length} player(s):\n` + results.map(formatPlayer).join("\n");
}

// ---- competition_standings --------------------------------------------------

export interface CompetitionStandingsArgs {
  competition: string;
  season: number;
  limit?: number;
}

export function competitionStandingsHandler(ds: Dataset, args: CompetitionStandingsArgs): string {
  const full = standings(ds, asComp(args.competition), args.season);
  if (full.length === 0) return `No standings data for ${args.competition} ${args.season}.`;
  const rows = full.slice(0, args.limit ?? 30);
  return formatStandings(rows, `${args.season} ${args.competition} Standings (computed)`, full.length);
}

// ---- match_statistics -------------------------------------------------------

export interface MatchStatisticsArgs {
  competition?: string;
  season?: number;
  biggest_wins?: number;
}

export function matchStatisticsHandler(ds: Dataset, args: MatchStatisticsArgs): string {
  const matches = findMatches(ds, {
    competition: asComp(args.competition),
    season: args.season,
  });
  const stats = matchStats(matches);
  const pct = (x: number) => (x * 100).toFixed(1) + "%";
  const lines = [
    `Statistics for ${args.competition ?? "all"}${args.season ? " " + args.season : ""}:`,
    `- Matches with scores: ${stats.matches}`,
    `- Total goals: ${stats.totalGoals}`,
    `- Average goals per match: ${stats.avgGoalsPerMatch.toFixed(2)}`,
    `- Home win rate: ${pct(stats.homeWinRate)}`,
    `- Draw rate: ${pct(stats.drawRate)}`,
    `- Away win rate: ${pct(stats.awayWinRate)}`,
  ];
  const n = args.biggest_wins ?? 5;
  if (n > 0) {
    const wins = biggestWins(matches, n);
    if (wins.length > 0) {
      lines.push("", "Biggest victories:");
      wins.forEach((m, i) => lines.push(`${i + 1}. ${formatMatch(m).slice(2)}`));
    }
  }
  return lines.join("\n");
}

// ---- list_teams -------------------------------------------------------------

export interface ListTeamsArgs {
  query?: string;
  limit?: number;
}

export function listTeamsHandler(ds: Dataset, args: ListTeamsArgs): string {
  let teams = ds.teams.all().sort((a, b) => a.localeCompare(b));
  if (args.query) {
    const q = args.query.toLowerCase();
    teams = teams.filter((t) => t.toLowerCase().includes(q));
  }
  teams = teams.slice(0, args.limit ?? 100);
  return `Known teams (${teams.length} shown):\n${teams.join("\n")}`;
}

// ---- list_competitions ------------------------------------------------------

export function listCompetitionsHandler(ds: Dataset): string {
  const lines = ["Competitions in dataset:"];
  for (const c of COMPETITIONS) {
    const seasons = (ds.seasonsByCompetition.get(c) ?? []).sort((a, b) => a - b);
    const count = ds.matchesByCompetition.get(c)?.length ?? 0;
    lines.push(`- ${c}: ${count} matches, seasons: ${seasons.length ? seasons.join(", ") : "n/a"}`);
  }
  return lines.join("\n");
}

// ---- registration -----------------------------------------------------------

/** Register all Brazilian-soccer tools on the given server. */
export function registerTools(server: McpServer, ds: Dataset): void {
  server.tool(
    "search_matches",
    "Find Brazilian soccer matches by team, opponent, competition, season, and/or date range. " +
      "Returns a formatted list of matches with date, score, and competition context.",
    {
      team: z.string().optional().describe("Team name (home, away, or either). Accepts variants like 'Palmeiras-SP'."),
      opponent: z.string().optional().describe("Opponent team — when set with `team`, returns only matches between the two."),
      competition: competitionEnum.optional().describe("Competition filter; 'all' searches every source."),
      season: z.number().int().optional().describe("Season year, e.g. 2023."),
      start_date: z.string().optional().describe("ISO date lower bound, e.g. '2023-01-01'."),
      end_date: z.string().optional().describe("ISO date upper bound, e.g. '2023-12-31'."),
      limit: z.number().int().min(1).max(500).default(50).describe("Max matches to return."),
    },
    (args) => textResult(searchMatchesHandler(ds, args)),
  );

  server.tool(
    "team_statistics",
    "Compute win/loss/draw record, goals for/against, and points for a team, optionally filtered by competition, season, and venue (home/away).",
    {
      team: z.string().describe("Team name (variants accepted, e.g. 'Corinthians-SP')."),
      competition: competitionEnum.optional(),
      season: z.number().int().optional(),
      venue: z.enum(["home", "away", "any"]).optional().describe("Restrict to home or away matches."),
    },
    (args) => textResult(teamStatisticsHandler(ds, args)),
  );

  server.tool(
    "compare_teams",
    "Compare two teams head-to-head: number of meetings, wins each, draws, and goals. Also returns each team's overall record.",
    {
      team_a: z.string(),
      team_b: z.string(),
      competition: competitionEnum.optional(),
    },
    (args) => textResult(compareTeamsHandler(ds, args)),
  );

  server.tool(
    "search_players",
    "Search the FIFA player database by name, nationality, club, position, and/or minimum overall rating. Returns players sorted by overall rating by default.",
    {
      name: z.string().optional(),
      nationality: z.string().optional().describe("e.g. 'Brazil', 'Argentina'."),
      club: z.string().optional().describe("Club name substring, e.g. 'Flamengo'."),
      position: z.string().optional().describe("Position code, e.g. 'ST', 'LW', 'GK', 'CDM'."),
      min_overall: z.number().int().min(0).max(99).optional(),
      sort_by: z.enum(["overall", "potential", "age", "name"]).optional(),
      limit: z.number().int().min(1).max(200).default(25),
    },
    (args) => textResult(searchPlayersHandler(ds, args)),
  );

  server.tool(
    "competition_standings",
    "Compute the standings table for a competition season from match results (3 pts/win, 1/draw). Returns ranked table; first row is champion, bottom four are in the relegation zone.",
    {
      competition: competitionEnum.describe("Competition. Use 'Brasileirão' for Série A."),
      season: z.number().int().describe("Season year, e.g. 2019."),
      limit: z.number().int().min(1).max(100).default(30),
    },
    (args) => textResult(competitionStandingsHandler(ds, args)),
  );

  server.tool(
    "match_statistics",
    "Aggregate statistics over a match set: average goals per match, home/draw/away win rates, total goals, and the biggest victories. Filter by competition and/or season.",
    {
      competition: competitionEnum.optional(),
      season: z.number().int().optional(),
      biggest_wins: z.number().int().min(0).max(50).default(5).describe("How many biggest victories to list."),
    },
    (args) => textResult(matchStatisticsHandler(ds, args)),
  );

  server.tool(
    "list_teams",
    "List known teams in the dataset, optionally filtered by a name substring. Use to resolve team name variants before querying.",
    {
      query: z.string().optional().describe("Substring filter (case-insensitive)."),
      limit: z.number().int().min(1).max(1000).default(100),
    },
    (args) => textResult(listTeamsHandler(ds, args)),
  );

  server.tool(
    "list_competitions",
    "List the competitions present in the dataset and the seasons available for each.",
    {},
    () => textResult(listCompetitionsHandler(ds)),
  );
}
