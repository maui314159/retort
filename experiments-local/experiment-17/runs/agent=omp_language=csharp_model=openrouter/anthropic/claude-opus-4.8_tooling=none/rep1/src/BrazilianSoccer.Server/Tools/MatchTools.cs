// -----------------------------------------------------------------------------
// File: Tools/MatchTools.cs
// Project: BrazilianSoccer.Server
//
// Context:
//   MCP tools for the "Match Queries" and part of the "Team Queries" capabilities.
//   Each public method decorated with [McpServerTool] becomes a callable tool the
//   LLM can invoke; the [Description] text guides tool selection and argument
//   filling. Query services are injected per call by the SDK from DI.
//
//   Tools accept loose strings (team names, competition names) and delegate all
//   normalisation to the Core services (TeamName / Competitions). They return the
//   pre-formatted text blocks from ResponseFormatter so the model gets answers in
//   the shape TASK.md specifies. Competition strings that are non-empty but
//   unrecognised produce a clear error string instead of silently matching all.
// -----------------------------------------------------------------------------

using System.ComponentModel;
using BrazilianSoccer.Core;
using BrazilianSoccer.Core.Models;
using BrazilianSoccer.Core.Queries;
using ModelContextProtocol.Server;

namespace BrazilianSoccer.Server.Tools;

/// <summary>MCP tools that search matches and head-to-head records.</summary>
[McpServerToolType]
public sealed class MatchTools
{
    [McpServerTool(Name = "find_matches")]
    [Description("Find Brazilian soccer matches by team, optional opponent, competition, season, and date range. " +
                 "Searches Brasileirão Série A/B/C, Copa do Brasil and Copa Libertadores. Returns a dated list of results.")]
    public static string FindMatches(
        MatchQueryService matches,
        [Description("Team name to search for (matches home or away side; accent/case insensitive, e.g. 'Flamengo').")]
        string? team = null,
        [Description("Optional opponent team name; when set, only matches between 'team' and this opponent are returned.")]
        string? opponent = null,
        [Description("Optional competition filter: 'Serie A'/'Brasileirao', 'Serie B', 'Serie C', 'Copa do Brasil', or 'Libertadores'.")]
        string? competition = null,
        [Description("Optional season year, e.g. 2019.")]
        int? season = null,
        [Description("Optional inclusive start date (yyyy-MM-dd).")]
        string? fromDate = null,
        [Description("Optional inclusive end date (yyyy-MM-dd).")]
        string? toDate = null,
        [Description("Maximum number of matches to list (default 20).")]
        int limit = 20)
    {
        if (!ToolArgs.TryCompetition(competition, out var comp, out var error))
            return error!;

        var from = ToolArgs.ParseDate(fromDate);
        var to = ToolArgs.ParseDate(toDate);

        var results = matches.Find(team, opponent, comp, season, from, to, limit: null);

        var header = ToolArgs.MatchHeader(team, opponent, comp, season);
        return ResponseFormatter.MatchList(header, results, show: limit);
    }

    [McpServerTool(Name = "head_to_head")]
    [Description("Summarise the head-to-head record between two teams across the datasets: wins, draws, goals, and recent meetings.")]
    public static string HeadToHead(
        MatchQueryService matches,
        [Description("First team name.")] string teamA,
        [Description("Second team name.")] string teamB,
        [Description("Optional competition filter (e.g. 'Libertadores'). Omit for all competitions.")]
        string? competition = null)
    {
        if (string.IsNullOrWhiteSpace(teamA) || string.IsNullOrWhiteSpace(teamB))
            return "Both teamA and teamB are required.";
        if (!ToolArgs.TryCompetition(competition, out var comp, out var error))
            return error!;

        var h2h = matches.HeadToHeadOf(teamA, teamB, comp);
        return ResponseFormatter.HeadToHead(h2h);
    }

    [McpServerTool(Name = "last_meeting")]
    [Description("Find the most recent decided match between two teams and report the date, score and competition.")]
    public static string LastMeeting(
        MatchQueryService matches,
        [Description("First team name.")] string teamA,
        [Description("Second team name.")] string teamB)
    {
        if (string.IsNullOrWhiteSpace(teamA) || string.IsNullOrWhiteSpace(teamB))
            return "Both teamA and teamB are required.";

        var m = matches.LastMeeting(teamA, teamB);
        return m is null
            ? $"No decided match between {teamA} and {teamB} found in the dataset."
            : $"Most recent {teamA} vs {teamB} meeting:\n- {ResponseFormatter.MatchLine(m)}";
    }

    [McpServerTool(Name = "team_competitions")]
    [Description("List the competitions a team has appeared in across all datasets.")]
    public static string TeamCompetitions(
        MatchQueryService matches,
        [Description("Team name.")] string team)
    {
        if (string.IsNullOrWhiteSpace(team))
            return "A team name is required.";

        var comps = matches.CompetitionsFor(team);
        if (comps.Count == 0)
            return $"No matches found for {team} in the dataset.";

        var names = comps.Select(Competitions.DisplayName);
        return $"{team} appears in: {string.Join(", ", names)}.";
    }
}
