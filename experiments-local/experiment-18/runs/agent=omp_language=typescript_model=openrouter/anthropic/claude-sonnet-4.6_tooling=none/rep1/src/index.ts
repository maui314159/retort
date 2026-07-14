#!/usr/bin/env node
/**
 * Brazilian Soccer MCP Server
 *
 * Provides tools for querying Brazilian soccer data:
 * matches, players, team stats, standings, and statistical analysis.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import {
  findMatches,
  getHeadToHead,
  getTeamStats,
  getStandings,
  findPlayers,
  getCompetitionStats,
  getBestHomeRecord,
  getBiggestWins,
  getTeamCompetitions,
} from "./queries.js";
import type { Match, Player, TeamRecord } from "./types.js";

// ─── formatting helpers ──────────────────────────────────────────────────────

function fmtMatch(m: Match): string {
  const score = `${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam}`;
  const round = m.round ? ` (Round ${m.round})` : m.stage ? ` (${m.stage})` : "";
  return `${m.date}: ${score} [${m.competition}${round}]`;
}

function fmtRecord(r: TeamRecord, rank?: number): string {
  const prefix = rank !== undefined ? `${rank}. ` : "";
  const winRate = r.matches > 0 ? ((r.wins / r.matches) * 100).toFixed(1) : "0.0";
  const gd = r.goalsFor - r.goalsAgainst;
  const gdStr = gd >= 0 ? `+${gd}` : String(gd);
  return (
    `${prefix}${r.team} — ${r.points}pts ` +
    `(${r.wins}W/${r.draws}D/${r.losses}L) ` +
    `GF:${r.goalsFor} GA:${r.goalsAgainst} GD:${gdStr} ` +
    `WinRate:${winRate}%`
  );
}

function fmtPlayer(p: Player, rank?: number): string {
  const prefix = rank !== undefined ? `${rank}. ` : "";
  const jersey = p.jerseyNumber !== undefined ? ` #${p.jerseyNumber}` : "";
  return `${prefix}${p.name}${jersey} — Overall:${p.overall} Pos:${p.position} Club:${p.club} Nat:${p.nationality} Age:${p.age}`;
}

// ─── Server ──────────────────────────────────────────────────────────────────

const server = new McpServer({
  name: "brazilian-soccer-mcp-server",
  version: "1.0.0",
});

// ── 1. find_matches ──────────────────────────────────────────────────────────

server.registerTool(
  "find_matches",
  {
    title: "Find Soccer Matches",
    description: `Search Brazilian soccer match records across all available datasets.

Searches Brasileirão Serie A, Copa do Brasil, Copa Libertadores, and extended statistics datasets.

Args:
  - team: Filter matches involving this team (home or away). Partial name ok ("Flamengo" matches "Flamengo-RJ").
  - team1 + team2: Find head-to-head matches between two specific teams.
  - competition: Filter by competition name. Values: "Brasileirao", "Copa do Brasil", "Libertadores", "Extended". Partial match ok.
  - season: Filter by year (e.g. 2023).
  - date_from / date_to: ISO date strings YYYY-MM-DD.
  - limit: Max results (default 50, max 200).

Returns text listing matches sorted by date descending.`,
    inputSchema: z.object({
      team: z.string().optional().describe("Team name substring (home or away)"),
      team1: z.string().optional().describe("First team for head-to-head"),
      team2: z.string().optional().describe("Second team for head-to-head"),
      competition: z
        .string()
        .optional()
        .describe('Competition filter: "Brasileirao", "Copa do Brasil", "Libertadores"'),
      season: z.number().int().min(1900).max(2100).optional().describe("Season year"),
      date_from: z.string().optional().describe("Start date YYYY-MM-DD"),
      date_to: z.string().optional().describe("End date YYYY-MM-DD"),
      limit: z.number().int().min(1).max(200).default(50).describe("Max results"),
    }),
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: false,
    },
  },
  (params) => {
    const matches = findMatches({
      team: params.team,
      team1: params.team1,
      team2: params.team2,
      competition: params.competition,
      season: params.season,
      dateFrom: params.date_from,
      dateTo: params.date_to,
      limit: params.limit,
    });

    if (matches.length === 0) {
      return { content: [{ type: "text", text: "No matches found for those criteria." }] };
    }

    const lines = [`Found ${matches.length} match(es):\n`];
    for (const m of matches) lines.push(fmtMatch(m));
    return { content: [{ type: "text", text: lines.join("\n") }] };
  }
);

// ── 2. head_to_head ──────────────────────────────────────────────────────────

server.registerTool(
  "head_to_head",
  {
    title: "Head-to-Head Record",
    description: `Get complete head-to-head history between two teams across all competitions.

Args:
  - team1: First team name (partial ok).
  - team2: Second team name (partial ok).
  - limit: Max individual match results to show (default 20).

Returns summary stats and match list sorted most recent first.`,
    inputSchema: z.object({
      team1: z.string().min(1).describe("First team name"),
      team2: z.string().min(1).describe("Second team name"),
      limit: z.number().int().min(1).max(100).default(20).describe("Max matches to list"),
    }),
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: false,
    },
  },
  (params) => {
    const h2h = getHeadToHead(params.team1, params.team2);

    if (h2h.matches.length === 0) {
      return {
        content: [
          {
            type: "text",
            text: `No matches found between "${params.team1}" and "${params.team2}".`,
          },
        ],
      };
    }

    const shown = h2h.matches.slice(0, params.limit);
    const lines = [
      `Head-to-head: ${params.team1} vs ${params.team2}`,
      `Total: ${h2h.matches.length} matches`,
      `${params.team1} wins: ${h2h.team1Wins} | ${params.team2} wins: ${h2h.team2Wins} | Draws: ${h2h.draws}`,
      `Goals: ${params.team1} ${h2h.team1Goals} – ${h2h.team2Goals} ${params.team2}`,
      "",
      `Recent matches (${shown.length}):`,
    ];
    for (const m of shown) lines.push(fmtMatch(m));
    if (h2h.matches.length > params.limit) {
      lines.push(`... and ${h2h.matches.length - params.limit} more.`);
    }

    return { content: [{ type: "text", text: lines.join("\n") }] };
  }
);

// ── 3. team_stats ────────────────────────────────────────────────────────────

server.registerTool(
  "team_stats",
  {
    title: "Team Statistics",
    description: `Get win/loss/draw statistics for a team, optionally filtered by competition, season, or home/away.

Args:
  - team: Team name (partial match ok).
  - competition: Optional competition filter.
  - season: Optional season year.
  - home_only: Only count home matches.
  - away_only: Only count away matches.

Returns: matches, wins, draws, losses, goals for/against, win rate.`,
    inputSchema: z.object({
      team: z.string().min(1).describe("Team name"),
      competition: z.string().optional().describe("Competition filter"),
      season: z.number().int().optional().describe("Season year"),
      home_only: z.boolean().default(false).describe("Only home matches"),
      away_only: z.boolean().default(false).describe("Only away matches"),
    }),
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: false,
    },
  },
  (params) => {
    const rec = getTeamStats({
      team: params.team,
      competition: params.competition,
      season: params.season,
      homeOnly: params.home_only,
      awayOnly: params.away_only,
    });

    if (rec.matches === 0) {
      return {
        content: [
          { type: "text", text: `No match data found for "${params.team}" with those filters.` },
        ],
      };
    }

    const context: string[] = [];
    if (params.competition) context.push(params.competition);
    if (params.season) context.push(String(params.season));
    if (params.home_only) context.push("home only");
    if (params.away_only) context.push("away only");

    const label = context.length > 0 ? ` (${context.join(", ")})` : "";
    const winRate = ((rec.wins / rec.matches) * 100).toFixed(1);
    const gd = rec.goalsFor - rec.goalsAgainst;

    const text = [
      `${rec.team}${label}:`,
      `  Matches: ${rec.matches}`,
      `  Record: ${rec.wins}W / ${rec.draws}D / ${rec.losses}L`,
      `  Points: ${rec.points}`,
      `  Goals For: ${rec.goalsFor}  Goals Against: ${rec.goalsAgainst}  GD: ${gd >= 0 ? "+" : ""}${gd}`,
      `  Win Rate: ${winRate}%`,
    ].join("\n");

    return { content: [{ type: "text", text }] };
  }
);

// ── 4. standings ─────────────────────────────────────────────────────────────

server.registerTool(
  "standings",
  {
    title: "Competition Standings",
    description: `Calculate standings table for a competition and season from match results.

Args:
  - competition: Competition name ("Brasileirao", "Libertadores", "Copa do Brasil", or "all").
  - season: Season year (required).
  - top_n: Number of teams to return (default 20).

Returns ranked table sorted by points, then goal difference.`,
    inputSchema: z.object({
      competition: z
        .string()
        .min(1)
        .describe('Competition: "Brasileirao", "Libertadores", "Copa do Brasil", "all"'),
      season: z.number().int().min(1900).max(2100).describe("Season year"),
      top_n: z.number().int().min(1).max(100).default(20).describe("Number of teams"),
    }),
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: false,
    },
  },
  (params) => {
    const records = getStandings(params.competition, params.season);
    const shown = records.slice(0, params.top_n);

    if (shown.length === 0) {
      return {
        content: [
          {
            type: "text",
            text: `No data found for ${params.competition} ${params.season}.`,
          },
        ],
      };
    }

    const lines = [
      `${params.competition} ${params.season} — Standings (${shown.length} teams):`,
      "",
    ];
    shown.forEach((r, i) => lines.push(fmtRecord(r, i + 1)));

    return { content: [{ type: "text", text: lines.join("\n") }] };
  }
);

// ── 5. find_players ──────────────────────────────────────────────────────────

server.registerTool(
  "find_players",
  {
    title: "Find FIFA Players",
    description: `Search FIFA player database by name, nationality, club, or position.

Args:
  - name: Partial player name.
  - nationality: Country name ("Brazil", "Argentina", …).
  - club: Club name substring ("Flamengo", "Palmeiras", …).
  - position: Position substring ("GK", "ST", "LW", …).
  - min_overall: Minimum FIFA overall rating.
  - max_age: Maximum player age.
  - limit: Max results (default 30, max 100).

Returns players sorted by overall rating descending.`,
    inputSchema: z.object({
      name: z.string().optional().describe("Player name substring"),
      nationality: z.string().optional().describe("Nationality (e.g. \"Brazil\")"),
      club: z.string().optional().describe("Club name substring"),
      position: z.string().optional().describe("Position code or substring (\"GK\", \"ST\", etc.)"),
      min_overall: z.number().int().min(0).max(100).optional().describe("Minimum overall rating"),
      max_age: z.number().int().min(10).max(60).optional().describe("Maximum age"),
      limit: z.number().int().min(1).max(100).default(30).describe("Max results"),
    }),
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: false,
    },
  },
  (params) => {
    const players = findPlayers({
      name: params.name,
      nationality: params.nationality,
      club: params.club,
      position: params.position,
      minOverall: params.min_overall,
      maxAge: params.max_age,
      limit: params.limit,
    });

    if (players.length === 0) {
      return { content: [{ type: "text", text: "No players found for those criteria." }] };
    }

    const lines = [`Found ${players.length} player(s):\n`];
    players.forEach((p, i) => lines.push(fmtPlayer(p, i + 1)));
    return { content: [{ type: "text", text: lines.join("\n") }] };
  }
);

// ── 6. competition_stats ─────────────────────────────────────────────────────

server.registerTool(
  "competition_stats",
  {
    title: "Competition Statistics",
    description: `Aggregate statistics for a competition and/or season.

Args:
  - competition: Optional competition filter. Omit for all competitions.
  - season: Optional season year.

Returns: total matches, goals, avg goals per match, home/away win rates, biggest win.`,
    inputSchema: z.object({
      competition: z.string().optional().describe("Competition name (partial ok)"),
      season: z.number().int().optional().describe("Season year"),
    }),
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: false,
    },
  },
  (params) => {
    const stats = getCompetitionStats(params.competition, params.season);

    const homeWinPct = (stats.homeWinRate * 100).toFixed(1);
    const awayWinPct =
      stats.totalMatches > 0
        ? ((stats.awayWins / stats.totalMatches) * 100).toFixed(1)
        : "0.0";
    const drawPct =
      stats.totalMatches > 0
        ? ((stats.draws / stats.totalMatches) * 100).toFixed(1)
        : "0.0";

    const lines = [
      `Stats — ${stats.competition}${params.season ? " " + params.season : ""}:`,
      `  Total matches: ${stats.totalMatches}`,
      `  Total goals: ${stats.totalGoals}`,
      `  Avg goals/match: ${stats.avgGoalsPerMatch.toFixed(2)}`,
      `  Home wins: ${stats.homeWins} (${homeWinPct}%)`,
      `  Away wins: ${stats.awayWins} (${awayWinPct}%)`,
      `  Draws: ${stats.draws} (${drawPct}%)`,
    ];

    if (stats.biggestWin) {
      const { match: m, goalDiff } = stats.biggestWin;
      lines.push(
        `  Biggest win (${goalDiff} goals): ${fmtMatch(m)}`
      );
    }

    return { content: [{ type: "text", text: lines.join("\n") }] };
  }
);

// ── 7. biggest_wins ──────────────────────────────────────────────────────────

server.registerTool(
  "biggest_wins",
  {
    title: "Biggest Wins",
    description: `List the largest-margin victories across all datasets.

Args:
  - limit: Number of results to return (default 10, max 50).

Returns matches sorted by goal difference descending.`,
    inputSchema: z.object({
      limit: z.number().int().min(1).max(50).default(10).describe("Number of results"),
    }),
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: false,
    },
  },
  (params) => {
    const wins = getBiggestWins(params.limit);

    if (wins.length === 0) {
      return { content: [{ type: "text", text: "No match data available." }] };
    }

    const lines = [`Top ${wins.length} biggest victories:\n`];
    wins.forEach(({ match: m, goalDiff }, i) => {
      lines.push(`${i + 1}. (${goalDiff}-goal margin) ${fmtMatch(m)}`);
    });

    return { content: [{ type: "text", text: lines.join("\n") }] };
  }
);

// ── 8. best_home_record ──────────────────────────────────────────────────────

server.registerTool(
  "best_home_record",
  {
    title: "Best Home Record",
    description: `Rank teams by home win rate (minimum 5 home matches).

Args:
  - competition: Optional competition filter.
  - season: Optional season year.
  - top_n: Number of teams (default 10).

Returns team rankings by home win percentage.`,
    inputSchema: z.object({
      competition: z.string().optional().describe("Competition filter"),
      season: z.number().int().optional().describe("Season year"),
      top_n: z.number().int().min(1).max(50).default(10).describe("Number of teams"),
    }),
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: false,
    },
  },
  (params) => {
    const teams = getBestHomeRecord(params.competition, params.season, params.top_n);

    if (teams.length === 0) {
      return {
        content: [{ type: "text", text: "Not enough home match data for those filters." }],
      };
    }

    const lines = [
      `Best home record${params.competition ? ` (${params.competition})` : ""}${params.season ? ` ${params.season}` : ""}:\n`,
    ];
    teams.forEach(({ record }, i) => lines.push(fmtRecord(record, i + 1)));

    return { content: [{ type: "text", text: lines.join("\n") }] };
  }
);

// ── 9. team_competitions ─────────────────────────────────────────────────────

server.registerTool(
  "team_competitions",
  {
    title: "Team Competition History",
    description: `List all competitions a team has participated in across all datasets.

Args:
  - team: Team name (partial match ok).

Returns sorted list of competition names.`,
    inputSchema: z.object({
      team: z.string().min(1).describe("Team name"),
    }),
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: false,
    },
  },
  (params) => {
    const comps = getTeamCompetitions(params.team);

    if (comps.length === 0) {
      return {
        content: [{ type: "text", text: `No competition data found for "${params.team}".` }],
      };
    }

    const text = `Competitions for "${params.team}":\n${comps.map((c) => `  - ${c}`).join("\n")}`;
    return { content: [{ type: "text", text }] };
  }
);

// ─── Main ────────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  process.stderr.write("Brazilian Soccer MCP Server running via stdio\n");
}

main().catch((err: unknown) => {
  process.stderr.write(`Server error: ${err instanceof Error ? err.message : String(err)}\n`);
  process.exit(1);
});
