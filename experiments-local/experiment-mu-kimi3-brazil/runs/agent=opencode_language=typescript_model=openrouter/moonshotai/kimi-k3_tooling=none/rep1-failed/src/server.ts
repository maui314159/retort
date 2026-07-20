/**
 * MCP server factory.
 *
 * Exposes the Brazilian-soccer knowledge graph as MCP tools covering the
 * five capability categories from the specification:
 *   1. Match queries        -> search_matches, head_to_head
 *   2. Team queries         -> team_statistics, team_competitions, top_scoring_teams
 *   3. Player queries       -> search_players, player_details, players_per_club
 *   4. Competition queries  -> competition_standings, competition_finals, dataset_summary
 *   5. Statistical analysis -> competition_stats, biggest_wins, best_venue_records
 *
 * The server is transport-agnostic: `createServer()` returns a configured
 * McpServer which `index.ts` wires to stdio; tests wire it to
 * InMemoryTransport instead.
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import type { Dataset } from "./types.js";
import {
  findMatches,
  headToHead,
  lastMeeting,
} from "./services/matches.js";
import { mostGoalsScored, teamCompetitions, teamStats } from "./services/teams.js";
import { playersPerClub, searchPlayers } from "./services/players.js";
import {
  competitionSeasons,
  findFinals,
  standings,
} from "./services/competitions.js";
import {
  aggregateStats,
  bestVenueRecords,
  biggestWins,
} from "./services/stats.js";
import {
  formatHeadToHead,
  formatMatchLine,
  formatMatchList,
  formatPlayer,
  formatPlayerDetail,
  formatStandings,
  formatStats,
  formatTeamStats,
} from "./format.js";

const text = (t: string) => ({ content: [{ type: "text" as const, text: t }] });

const isoDate = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, "expected YYYY-MM-DD")
  .optional();

export function createServer(ds: Dataset): McpServer {
  const server = new McpServer({
    name: "brazilian-soccer-mcp",
    version: "1.0.0",
  });

  /* ---------------- 1. Match queries ---------------- */

  server.tool(
    "search_matches",
    "Find soccer matches by team (home/away/either), opponent, competition (Brasileirão Série A/B/C, Copa do Brasil, Copa Libertadores), season and/or date range. Use for questions like 'Show all Flamengo vs Fluminense matches', 'What matches did Palmeiras play in 2023?', 'When did Flamengo last play Corinthians?'.",
    {
      team: z.string().optional().describe("Team name, e.g. 'Flamengo' (matches home or away, any naming variant)"),
      opponent: z.string().optional().describe("Second team for head-to-head listings, e.g. 'Fluminense'"),
      competition: z.string().optional().describe("Competition filter: 'Brasileirão', 'Série A', 'Copa do Brasil', 'Libertadores'..."),
      season: z.number().int().optional().describe("Season year, e.g. 2023"),
      from_date: isoDate.describe("Start date (YYYY-MM-DD, inclusive)"),
      to_date: isoDate.describe("End date (YYYY-MM-DD, inclusive)"),
      stage: z.string().optional().describe("Round/stage filter, e.g. 'final', 'group stage', 'semi'"),
      limit: z.number().int().min(1).max(200).optional().describe("Max matches to return (default 30)"),
    },
    async ({ team, opponent, competition, season, from_date, to_date, stage, limit }) => {
      const matches = findMatches(ds, {
        team,
        opponent,
        competition,
        season,
        fromDate: from_date,
        toDate: to_date,
        stage,
        limit: limit ?? 30,
      });
      const title =
        team && opponent
          ? `${team} vs ${opponent}`
          : team
            ? `Matches involving ${team}`
            : "Matches";
      return text(formatMatchList(title, matches));
    },
  );

  server.tool(
    "head_to_head",
    "Compare two teams' all-time record in the dataset: wins, draws, goals and the most recent meetings. Use for 'Compare Palmeiras and Santos head-to-head'.",
    {
      team_a: z.string().describe("First team, e.g. 'Palmeiras'"),
      team_b: z.string().describe("Second team, e.g. 'Santos'"),
    },
    async ({ team_a, team_b }) => text(formatHeadToHead(headToHead(ds, team_a, team_b))),
  );

  server.tool(
    "last_meeting",
    "Return the most recent match between two teams, with date and score. Use for 'When did Flamengo last play Corinthians? What was the score?'.",
    {
      team_a: z.string(),
      team_b: z.string(),
    },
    async ({ team_a, team_b }) => {
      const m = lastMeeting(ds, team_a, team_b);
      return text(
        m
          ? `Last meeting: ${formatMatchLine(m)}`
          : `No meeting between ${team_a} and ${team_b} found in dataset.`,
      );
    },
  );

  /* ---------------- 2. Team queries ---------------- */

  server.tool(
    "team_statistics",
    "Win/draw/loss record, goals for/against and home/away splits for a team, optionally filtered by season and/or competition. Use for 'What is Corinthians' home record in 2022?'.",
    {
      team: z.string().describe("Team name, e.g. 'Corinthians'"),
      season: z.number().int().optional(),
      competition: z.string().optional(),
    },
    async ({ team, season, competition }) => {
      const s = teamStats(ds, team, { season, competition });
      const scope = [competition ?? "all competitions", season ?? "all seasons"].join(", ");
      return text(formatTeamStats(s, scope));
    },
  );

  server.tool(
    "team_competitions",
    "List the competitions a team has played in within the dataset, with match counts. Use for 'What competitions has Palmeiras played in?'.",
    { team: z.string() },
    async ({ team }) => {
      const comps = teamCompetitions(ds, team);
      if (!comps.size) return text(`No matches found for ${team} in dataset.`);
      const lines = [...comps.entries()]
        .sort((a, b) => b[1] - a[1])
        .map(([c, n]) => `- ${c}: ${n} matches`);
      return text(`${team} competitions in dataset:\n${lines.join("\n")}`);
    },
  );

  server.tool(
    "top_scoring_teams",
    "Rank teams by goals scored in a competition/season. Use for 'Which team scored the most goals in Serie A 2023?'.",
    {
      competition: z.string().optional(),
      season: z.number().int().optional(),
      limit: z.number().int().min(1).max(50).optional(),
    },
    async ({ competition, season, limit }) => {
      const rows = mostGoalsScored(ds, { competition, season, limit: limit ?? 10 });
      if (!rows.length) return text("No matches found for that filter.");
      const scope = [competition ?? "all competitions", season ?? "all seasons"].join(", ");
      const lines = rows.map(
        (r, i) => `${i + 1}. ${r.team} — ${r.goalsFor} goals in ${r.matches} matches`,
      );
      return text(`Top scoring teams (${scope}):\n${lines.join("\n")}`);
    },
  );

  /* ---------------- 3. Player queries ---------------- */

  server.tool(
    "search_players",
    "Search the FIFA player database by name, nationality, club and/or position; results sorted by overall rating. Use for 'Find Brazilian players', 'Who are the highest-rated players at Flamengo?', 'Show me forwards from São Paulo', 'Who is Gabriel Barbosa?'.",
    {
      name: z.string().optional().describe("Player name substring, e.g. 'Gabriel Barbosa'"),
      nationality: z.string().optional().describe("Nationality substring, e.g. 'Brazil'"),
      club: z.string().optional().describe("Club substring, e.g. 'Flamengo'"),
      position: z
        .string()
        .optional()
        .describe("Position code ('ST','LW','GK',...) or group: forward | midfielder | defender | goalkeeper"),
      min_overall: z.number().int().optional().describe("Minimum FIFA overall rating"),
      limit: z.number().int().min(1).max(100).optional(),
    },
    async ({ name, nationality, club, position, min_overall, limit }) => {
      const players = searchPlayers(ds, {
        name,
        nationality,
        club,
        position,
        minOverall: min_overall,
        limit: limit ?? 20,
      });
      if (!players.length) return text("No players found for that filter.");
      const lines = players.map((p, i) => `${i + 1}. ${formatPlayer(p)}`);
      return text(`Players found (${players.length}):\n${lines.join("\n")}`);
    },
  );

  server.tool(
    "player_details",
    "Full profile of the best-matching player by name: ratings, skills, physical attributes. Use for 'Who is Gabriel Barbosa?'.",
    { name: z.string().describe("Player name, e.g. 'Gabriel Barbosa'") },
    async ({ name }) => {
      const hits = searchPlayers(ds, { name, limit: 5 });
      if (!hits.length) return text(`No player named like '${name}' found in dataset.`);
      const lines = hits.map((p) => formatPlayerDetail(p));
      return text(lines.join("\n---\n"));
    },
  );

  server.tool(
    "players_per_club",
    "Count players per club for a nationality (default Brazil), with average rating. Use for 'How many Brazilian players are at each club in the dataset?'.",
    {
      nationality: z.string().optional(),
      min_players: z.number().int().optional(),
      limit: z.number().int().min(1).max(100).optional(),
    },
    async ({ nationality, min_players, limit }) => {
      const rows = playersPerClub(ds, {
        nationality: nationality ?? "Brazil",
        minPlayers: min_players ?? 1,
        limit: limit ?? 20,
      });
      if (!rows.length) return text("No players found for that filter.");
      const lines = rows.map(
        (r) => `- ${r.club}: ${r.players} players (avg rating: ${r.avgOverall.toFixed(0)})`,
      );
      return text(
        `Players per club (${nationality ?? "Brazil"}):\n${lines.join("\n")}`,
      );
    },
  );

  /* ---------------- 4. Competition queries ---------------- */

  server.tool(
    "competition_standings",
    "League table for a season calculated from match results (3-1-0 points, CBF tie-breaks). Use for 'Who won the 2019 Brasileirão?', 'Show the 2018 standings', 'Which teams were relegated in 2020?'.",
    {
      competition: z.string().describe("'Brasileirão Série A' (default), 'Série B', 'Série C'..."),
      season: z.number().int().describe("Season year, e.g. 2019"),
      limit: z.number().int().min(1).max(60).optional(),
    },
    async ({ competition, season, limit }) => {
      const rows = standings(ds, { competition, season });
      const relegated = rows.slice(-4);
      const table = formatStandings(`${competition} ${season} standings`, rows, limit ?? 20);
      const extra =
        rows.length >= 4
          ? `\nBottom 4 (relegation zone): ${relegated.map((r) => r.team).join(", ")}`
          : "";
      return text(table + extra);
    },
  );

  server.tool(
    "competition_finals",
    "List cup final matches (Copa do Brasil, Copa Libertadores), optionally per season. Use for 'Find all Copa do Brasil finals'.",
    {
      competition: z.string().describe("'Copa do Brasil' or 'Copa Libertadores'"),
      season: z.number().int().optional(),
    },
    async ({ competition, season }) => {
      const finals = findFinals(ds, { competition, season });
      return text(
        formatMatchList(`${competition} finals${season ? ` (${season})` : ""}`, finals),
      );
    },
  );

  server.tool(
    "competition_seasons",
    "List the seasons available for a competition in the dataset.",
    { competition: z.string() },
    async ({ competition }) => {
      const seasons = competitionSeasons(ds, competition);
      return text(
        seasons.length
          ? `${competition} seasons in dataset: ${seasons.join(", ")}`
          : `No matches found for ${competition}.`,
      );
    },
  );

  /* ---------------- 5. Statistical analysis ---------------- */

  server.tool(
    "competition_stats",
    "Aggregate statistics: average goals per match, home/draw/away win rates. Use for 'What's the average goals per match in the Brasileirão?', 'Compare the 2018 and 2019 seasons'.",
    {
      competition: z.string().optional(),
      season: z.number().int().optional(),
    },
    async ({ competition, season }) => {
      const s = aggregateStats(ds, { competition, season });
      const scope = [competition ?? "All competitions", season ?? "all seasons"].join(", ");
      return text(formatStats(scope, s));
    },
  );

  server.tool(
    "biggest_wins",
    "Largest-margin victories in the dataset. Use for 'Show me the biggest wins in the dataset'.",
    {
      competition: z.string().optional(),
      season: z.number().int().optional(),
      limit: z.number().int().min(1).max(50).optional(),
    },
    async ({ competition, season, limit }) => {
      const wins = biggestWins(ds, { competition, season, limit: limit ?? 10 });
      const scope = [competition ?? "all competitions", season ?? "all seasons"].join(", ");
      const lines = wins.map(
        (m, i) =>
          `${i + 1}. ${m.date}: ${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam} (${m.competition})`,
      );
      return text(`Biggest victories (${scope}):\n${lines.join("\n")}`);
    },
  );

  server.tool(
    "best_venue_records",
    "Teams with the best home (or away) records by win rate. Use for 'Which team has the best away record?', 'Which team has the best home record?'.",
    {
      venue: z.enum(["home", "away"]),
      competition: z.string().optional(),
      season: z.number().int().optional(),
      min_matches: z.number().int().optional().describe("Minimum matches to qualify (default 10)"),
      limit: z.number().int().min(1).max(50).optional(),
    },
    async ({ venue, competition, season, min_matches, limit }) => {
      const rows = bestVenueRecords(ds, venue, {
        competition,
        season,
        minMatches: min_matches ?? 10,
        limit: limit ?? 10,
      });
      if (!rows.length) return text("No teams qualify for that filter.");
      const scope = [competition ?? "all competitions", season ?? "all seasons"].join(", ");
      const lines = rows.map(
        (r, i) =>
          `${i + 1}. ${r.team} — ${(r.winRate * 100).toFixed(1)}% wins (${r.wins}W ${r.draws}D ${r.losses}L in ${r.played} ${venue} matches)`,
      );
      return text(`Best ${venue} records (${scope}):\n${lines.join("\n")}`);
    },
  );

  /* ---------------- meta ---------------- */

  server.tool(
    "dataset_summary",
    "Overview of the loaded knowledge graph: files, row counts, match/player totals, competitions and season coverage.",
    {},
    async () => {
      const comps = new Map<string, number>();
      for (const m of ds.matches) comps.set(m.competition, (comps.get(m.competition) ?? 0) + 1);
      const seasons = ds.matches
        .map((m) => m.season)
        .filter((s): s is number => s !== null);
      const lines = [
        "Brazilian Soccer knowledge graph — loaded data:",
        ...ds.loadedFiles.map((f) => `- ${f.file}: ${f.rows} rows`),
        "",
        `Totals: ${ds.matches.length} matches, ${ds.players.length} players, ${ds.teamIndex.size} distinct teams.`,
        `Seasons covered: ${Math.min(...seasons)}–${Math.max(...seasons)}.`,
        "Competitions:",
        ...[...comps.entries()].sort().map(([c, n]) => `- ${c}: ${n} matches`),
      ];
      return text(lines.join("\n"));
    },
  );

  return server;
}
