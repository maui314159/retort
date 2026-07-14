/**
 * Brazilian Soccer MCP Server - Entry Point
 *
 * Implements an MCP server exposing tools for querying Brazilian soccer data:
 * search_matches, team_stats, head_to_head, search_players, competition_standings,
 * and match_statistics. Uses stdio transport for communication with MCP clients.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { DataLoader } from "./loader.js";
import {
  searchMatches,
  getTeamRecord,
  getHeadToHead,
  searchPlayers,
  getStandings,
  getMatchStats,
  getBestTeamRecord,
} from "./query.js";

const data = new DataLoader();

const server = new McpServer({
  name: "brazilian-soccer",
  version: "1.0.0",
});

// ── Tool: search_matches ───────────────────────────────────────────

server.tool(
  "search_matches",
  "Search for Brazilian soccer matches by team, opponent, competition, season, or date range",
  {
    team: z.string().optional().describe("Team name to search for (home or away)"),
    opponent: z.string().optional().describe("Opponent team name"),
    competition: z.string().optional().describe("Competition name (e.g., Brasileirão, Copa do Brasil, Libertadores)"),
    season: z.number().optional().describe("Season year"),
    date_from: z.string().optional().describe("Start date (YYYY-MM-DD)"),
    date_to: z.string().optional().describe("End date (YYYY-MM-DD)"),
    limit: z.number().optional().describe("Max results to return (default 50)"),
  },
  async (params) => {
    const results = searchMatches(data.matches, {
      team: params.team,
      opponent: params.opponent,
      competition: params.competition,
      season: params.season,
      dateFrom: params.date_from,
      dateTo: params.date_to,
      limit: params.limit ?? 50,
    });

    const lines = results.map(
      (m) =>
        `- ${m.date}: ${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam} (${m.competition}${m.round ? ` Round ${m.round}` : ""}${m.stage ? ` ${m.stage}` : ""})`
    );

    const text =
      lines.length > 0
        ? `Found ${results.length} matches:\n${lines.join("\n")}`
        : "No matches found for the given criteria.";

    return { content: [{ type: "text", text }] };
  }
);

// ── Tool: team_stats ───────────────────────────────────────────────

server.tool(
  "team_stats",
  "Get win/draw/loss record and goal statistics for a team",
  {
    team: z.string().describe("Team name"),
    season: z.number().optional().describe("Season year filter"),
    competition: z.string().optional().describe("Competition filter"),
    home_only: z.boolean().optional().describe("Home matches only"),
    away_only: z.boolean().optional().describe("Away matches only"),
  },
  async (params) => {
    const record = getTeamRecord(data.matches, params.team, {
      season: params.season,
      competition: params.competition,
      homeOnly: params.home_only,
      awayOnly: params.away_only,
    });

    const winRate =
      record.matches > 0
        ? ((record.wins / record.matches) * 100).toFixed(1)
        : "0.0";

    const text = `${record.team} record${params.season ? ` (${params.season})` : ""}${params.competition ? ` ${params.competition}` : ""}:
- Matches: ${record.matches}
- Wins: ${record.wins}, Draws: ${record.draws}, Losses: ${record.losses}
- Goals For: ${record.goalsFor}, Goals Against: ${record.goalsAgainst}
- Points: ${record.points}
- Win rate: ${winRate}%`;

    return { content: [{ type: "text", text }] };
  }
);

// ── Tool: head_to_head ─────────────────────────────────────────────

server.tool(
  "head_to_head",
  "Compare two teams head-to-head: wins, draws, losses, and match list",
  {
    team1: z.string().describe("First team name"),
    team2: z.string().describe("Second team name"),
  },
  async (params) => {
    const h2h = getHeadToHead(data.matches, params.team1, params.team2);
    const matchLines = h2h.matches
      .slice(0, 30)
      .map(
        (m) =>
          `- ${m.date}: ${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam} (${m.competition})`
      );

    const text = `Head-to-head: ${h2h.team1} vs ${h2h.team2}
- ${h2h.team1} wins: ${h2h.team1Wins}
- ${h2h.team2} wins: ${h2h.team2Wins}
- Draws: ${h2h.draws}
- Total matches: ${h2h.matches.length}

Recent matches:
${matchLines.join("\n")}`;

    return { content: [{ type: "text", text }] };
  }
);

// ── Tool: search_players ───────────────────────────────────────────

server.tool(
  "search_players",
  "Search FIFA player database by name, nationality, club, or position",
  {
    name: z.string().optional().describe("Player name (partial match)"),
    nationality: z.string().optional().describe("Nationality (e.g., Brazil)"),
    club: z.string().optional().describe("Club name (partial match)"),
    position: z.string().optional().describe("Position (e.g., ST, LW, GK)"),
    min_overall: z.number().optional().describe("Minimum overall rating"),
    limit: z.number().optional().describe("Max results (default 20)"),
    sort_by: z.string().optional().describe("Sort field (default: overall)"),
  },
  async (params) => {
    const results = searchPlayers(data.players, {
      name: params.name,
      nationality: params.nationality,
      club: params.club,
      position: params.position,
      minOverall: params.min_overall,
      limit: params.limit ?? 20,
      sortBy: params.sort_by,
    });

    const lines = results.map(
      (p, i) =>
        `${i + 1}. ${p.name} - Overall: ${p.overall}, Position: ${p.position}, Club: ${p.club}, Age: ${p.age}`
    );

    const text =
      lines.length > 0
        ? `Found ${results.length} players:\n${lines.join("\n")}`
        : "No players found for the given criteria.";

    return { content: [{ type: "text", text }] };
  }
);

// ── Tool: competition_standings ─────────────────────────────────────

server.tool(
  "competition_standings",
  "Get calculated standings for a competition in a given season",
  {
    competition: z.string().describe("Competition name (e.g., Brasileirão)"),
    season: z.number().describe("Season year"),
  },
  async (params) => {
    const standings = getStandings(
      data.matches,
      params.competition,
      params.season
    );

    const lines = standings.map(
      (e) =>
        `${e.position}. ${e.team} - ${e.points} pts (${e.wins}W, ${e.draws}D, ${e.losses}L) GF:${e.goalsFor} GA:${e.goalsAgainst} GD:${e.goalDifference >= 0 ? "+" : ""}${e.goalDifference}`
    );

    const text =
      lines.length > 0
        ? `${params.competition} ${params.season} Standings:\n${lines.join("\n")}`
        : `No standings data found for ${params.competition} ${params.season}.`;

    return { content: [{ type: "text", text }] };
  }
);

// ── Tool: match_statistics ─────────────────────────────────────────

server.tool(
  "match_statistics",
  "Get aggregated match statistics: avg goals, home/away win rates, biggest victories",
  {
    competition: z.string().optional().describe("Competition filter"),
    season: z.number().optional().describe("Season filter"),
  },
  async (params) => {
    const stats = getMatchStats(data.matches, {
      competition: params.competition,
      season: params.season,
    });

    const biggestHome = stats.biggestHomeWins.slice(0, 5).map(
      (m) =>
        `${m.date}: ${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam} (${m.competition})`
    );

    const biggestAway = stats.biggestAwayWins.slice(0, 5).map(
      (m) =>
        `${m.date}: ${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam} (${m.competition})`
    );

    const text = `Match Statistics${params.competition ? ` - ${params.competition}` : ""}${params.season ? ` ${params.season}` : ""}:
- Total matches: ${stats.totalMatches}
- Total goals: ${stats.totalGoals}
- Average goals per match: ${stats.avgGoalsPerMatch}
- Home wins: ${stats.homeWins} (${stats.homeWinRate}%)
- Away wins: ${stats.awayWins} (${stats.awayWinRate}%)
- Draws: ${stats.draws} (${stats.drawRate}%)

Biggest home victories:
${biggestHome.join("\n") || "None"}

Biggest away victories:
${biggestAway.join("\n") || "None"}`;

    return { content: [{ type: "text", text }] };
  }
);

// ── Tool: best_teams ───────────────────────────────────────────────

server.tool(
  "best_teams",
  "Rank teams by record in a competition/season (points, wins, goals, etc.)",
  {
    competition: z.string().optional().describe("Competition filter"),
    season: z.number().optional().describe("Season filter"),
    home_only: z.boolean().optional().describe("Home matches only"),
    away_only: z.boolean().optional().describe("Away matches only"),
    sort_by: z.enum(["points", "wins", "goalsFor", "goalDifference"]).optional().describe("Sort criterion (default: points)"),
    limit: z.number().optional().describe("Max results (default 20)"),
  },
  async (params) => {
    const records = getBestTeamRecord(data.matches, {
      competition: params.competition,
      season: params.season,
      homeOnly: params.home_only,
      awayOnly: params.away_only,
      sortBy: params.sort_by,
    });

    const limit = params.limit ?? 20;
    const lines = records.slice(0, limit).map(
      (r, i) =>
        `${i + 1}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L) GF:${r.goalsFor} GA:${r.goalsAgainst}`
    );

    const text =
      lines.length > 0
        ? `Team rankings:\n${lines.join("\n")}`
        : "No team records found for the given criteria.";

    return { content: [{ type: "text", text }] };
  }
);

// ── Start ──────────────────────────────────────────────────────────

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Brazilian Soccer MCP server running on stdio");
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
