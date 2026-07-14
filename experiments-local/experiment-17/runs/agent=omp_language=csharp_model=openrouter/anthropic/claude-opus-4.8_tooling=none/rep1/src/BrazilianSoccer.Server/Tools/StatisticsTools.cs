// -----------------------------------------------------------------------------
// File: Tools/StatisticsTools.cs
// Project: BrazilianSoccer.Server
//
// Context:
//   MCP tools for "Statistical Analysis": average goals per match and home/away/
//   draw rates over an optional competition+season scope, the biggest victories
//   (largest goal margins), and the teams with the best home/away records. All
//   figures come from the deduplicated canonical match set so overlapping source
//   files never distort the aggregates.
// -----------------------------------------------------------------------------

using System.ComponentModel;
using BrazilianSoccer.Core;
using BrazilianSoccer.Core.Models;
using BrazilianSoccer.Core.Queries;
using ModelContextProtocol.Server;

namespace BrazilianSoccer.Server.Tools;

/// <summary>MCP tools for aggregate statistical analysis.</summary>
[McpServerToolType]
public sealed class StatisticsTools
{
    [McpServerTool(Name = "match_statistics")]
    [Description("Aggregate statistics over matches: average goals per match, home/away/draw rates and totals, " +
                 "optionally scoped to a competition and/or season.")]
    public static string MatchStatistics(
        StatisticsService stats,
        [Description("Optional competition filter (e.g. 'Serie A', 'Libertadores').")]
        string? competition = null,
        [Description("Optional season year.")] int? season = null)
    {
        if (!ToolArgs.TryCompetition(competition, out var comp, out var error))
            return error!;

        var summary = stats.Summary(comp, season);
        var header = "Match statistics" + Scope(comp, season);
        return ResponseFormatter.Summary(header, summary);
    }

    [McpServerTool(Name = "biggest_victories")]
    [Description("List the matches with the largest goal margins (biggest wins), optionally scoped to a " +
                 "competition and/or season.")]
    public static string BiggestVictories(
        StatisticsService stats,
        [Description("Optional competition filter.")] string? competition = null,
        [Description("Optional season year.")] int? season = null,
        [Description("Maximum number of matches to list (default 10).")] int limit = 10)
    {
        if (!ToolArgs.TryCompetition(competition, out var comp, out var error))
            return error!;

        var matches = stats.BiggestVictories(comp, season, limit);
        var header = "Biggest victories" + Scope(comp, season) + ":";
        return ResponseFormatter.MatchList(header, matches, show: limit);
    }

    [McpServerTool(Name = "best_records")]
    [Description("Rank teams by their record at a venue (all/home/away), best win rate first, among teams with " +
                 "enough matches. Answers 'which team has the best home/away record?'.")]
    public static string BestRecords(
        StatisticsService stats,
        [Description("Venue: 'all' (default), 'home', or 'away'.")] string venue = "all",
        [Description("Optional competition filter.")] string? competition = null,
        [Description("Optional season year.")] int? season = null,
        [Description("Minimum matches a team must have played to be ranked (default 5).")] int minMatches = 5,
        [Description("Maximum number of teams to list (default 10).")] int limit = 10)
    {
        if (!ToolArgs.TryCompetition(competition, out var comp, out var error))
            return error!;

        var v = venue?.Trim().ToLowerInvariant() switch
        {
            "home" => Venue.Home,
            "away" => Venue.Away,
            _ => Venue.All,
        };

        var records = stats.BestRecords(v, comp, season, minMatches, limit);
        if (records.Count == 0)
            return "No teams matched that scope with the required minimum matches.";

        var venueLabel = v == Venue.Home ? "home" : v == Venue.Away ? "away" : "overall";
        var header = $"Best {venueLabel} records{Scope(comp, season)}:";
        var lines = records.Select((r, i) =>
            $"{i + 1}. {r.Team} - {(r.WinRate * 100):0.0}% win rate " +
            $"({r.Wins}W {r.Draws}D {r.Losses}L over {r.Played}, {r.Points} pts)");
        return header + "\n" + string.Join("\n", lines);
    }

    private static string Scope(Competition? comp, int? season)
    {
        var parts = new List<string>();
        if (comp is not null) parts.Add(Competitions.DisplayName(comp.Value));
        if (season is not null) parts.Add(season.Value.ToString(System.Globalization.CultureInfo.InvariantCulture));
        return parts.Count == 0 ? " (all data)" : " (" + string.Join(", ", parts) + ")";
    }
}
