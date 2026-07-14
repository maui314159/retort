// -----------------------------------------------------------------------------
// File: Tools/TeamTools.cs
// Project: BrazilianSoccer.Server
//
// Context:
//   MCP tools for "Team Queries" and "Competition Queries": a team's W/D/L record
//   (optionally scoped by competition, season, and home/away), a side-by-side
//   comparison of two teams, calculated league standings, the season champion,
//   and the relegation zone. All numbers are derived from match results in the
//   deduplicated canonical dataset; tool output notes that tables are calculated.
// -----------------------------------------------------------------------------

using System.ComponentModel;
using BrazilianSoccer.Core;
using BrazilianSoccer.Core.Models;
using BrazilianSoccer.Core.Queries;
using ModelContextProtocol.Server;

namespace BrazilianSoccer.Server.Tools;

/// <summary>MCP tools for team records and competition standings.</summary>
[McpServerToolType]
public sealed class TeamTools
{
    [McpServerTool(Name = "team_record")]
    [Description("Get a team's win/draw/loss record, goals for/against and win rate, " +
                 "optionally scoped by competition, season, and venue (home or away).")]
    public static string TeamRecord(
        TeamQueryService teams,
        [Description("Team name, e.g. 'Corinthians'.")] string team,
        [Description("Optional competition filter (e.g. 'Serie A', 'Libertadores').")]
        string? competition = null,
        [Description("Optional season year, e.g. 2022.")] int? season = null,
        [Description("Venue filter: 'all' (default), 'home', or 'away'.")] string venue = "all")
    {
        if (string.IsNullOrWhiteSpace(team))
            return "A team name is required.";
        if (!ToolArgs.TryCompetition(competition, out var comp, out var error))
            return error!;

        var v = ParseVenue(venue);
        var record = teams.RecordFor(team, comp, season, v);

        var scope = BuildScope(comp, season, v);
        return ResponseFormatter.Record(record, scope);
    }

    [McpServerTool(Name = "compare_teams")]
    [Description("Compare two teams' records side by side over an optional competition and season scope.")]
    public static string CompareTeams(
        TeamQueryService teams,
        [Description("First team name.")] string teamA,
        [Description("Second team name.")] string teamB,
        [Description("Optional competition filter.")] string? competition = null,
        [Description("Optional season year.")] int? season = null)
    {
        if (string.IsNullOrWhiteSpace(teamA) || string.IsNullOrWhiteSpace(teamB))
            return "Both teamA and teamB are required.";
        if (!ToolArgs.TryCompetition(competition, out var comp, out var error))
            return error!;

        var (a, b) = teams.Compare(teamA, teamB, comp, season);
        var scope = BuildScope(comp, season, Venue.All);
        return ResponseFormatter.Record(a, scope) + "\n\n" + ResponseFormatter.Record(b, scope);
    }

    [McpServerTool(Name = "standings")]
    [Description("Calculate the league table for a competition and season from match results " +
                 "(points, W/D/L, goal difference), ordered best to worst.")]
    public static string Standings(
        CompetitionQueryService competitions,
        [Description("Competition: 'Serie A'/'Brasileirao', 'Serie B', 'Serie C', 'Copa do Brasil', or 'Libertadores'.")]
        string competition,
        [Description("Season year, e.g. 2019.")] int season,
        [Description("Maximum number of table rows to show (default 20).")] int limit = 20)
    {
        if (!ToolArgs.TryCompetition(competition, out var comp, out var error))
            return error!;
        if (comp is null)
            return "A competition is required for standings.";

        var table = competitions.Table(comp.Value, season);
        return ResponseFormatter.StandingsTable(table, show: limit);
    }

    [McpServerTool(Name = "champion")]
    [Description("Report the champion (table-topper) of a competition and season, calculated from match results.")]
    public static string Champion(
        CompetitionQueryService competitions,
        [Description("Competition name.")] string competition,
        [Description("Season year, e.g. 2019.")] int season)
    {
        if (!ToolArgs.TryCompetition(competition, out var comp, out var error))
            return error!;
        if (comp is null)
            return "A competition is required.";

        var champ = competitions.Champion(comp.Value, season);
        if (champ is null)
            return $"No {Competitions.DisplayName(comp.Value)} {season} matches found in the dataset.";

        return $"{season} {Competitions.DisplayName(comp.Value)} champion (calculated from matches): " +
               $"{champ.Team} - {champ.Points} pts ({champ.Wins}W {champ.Draws}D {champ.Losses}L, " +
               $"GD {champ.GoalDifference:+0;-0;0}).";
    }

    [McpServerTool(Name = "relegation_zone")]
    [Description("List the bottom teams (relegation zone) of a competition and season's calculated table.")]
    public static string RelegationZone(
        CompetitionQueryService competitions,
        [Description("Competition name (typically 'Serie A').")] string competition,
        [Description("Season year, e.g. 2020.")] int season,
        [Description("Number of bottom teams to list (default 4).")] int count = 4)
    {
        if (!ToolArgs.TryCompetition(competition, out var comp, out var error))
            return error!;
        if (comp is null)
            return "A competition is required.";

        var rows = competitions.Relegated(comp.Value, season, count);
        if (rows.Count == 0)
            return $"No {Competitions.DisplayName(comp.Value)} {season} matches found in the dataset.";

        var lines = rows.Select(r =>
            $"{r.Position}. {r.Record.Team} - {r.Record.Points} pts " +
            $"({r.Record.Wins}W {r.Record.Draws}D {r.Record.Losses}L)");
        return $"{season} {Competitions.DisplayName(comp.Value)} bottom {rows.Count} " +
               $"(calculated from matches):\n" + string.Join("\n", lines);
    }

    private static Venue ParseVenue(string? venue) => venue?.Trim().ToLowerInvariant() switch
    {
        "home" => Venue.Home,
        "away" => Venue.Away,
        _ => Venue.All,
    };

    private static string BuildScope(Competition? comp, int? season, Venue venue)
    {
        var parts = new List<string>();
        if (venue == Venue.Home) parts.Add("home");
        else if (venue == Venue.Away) parts.Add("away");
        if (season is not null) parts.Add(season.Value.ToString(System.Globalization.CultureInfo.InvariantCulture));
        if (comp is not null) parts.Add(Competitions.DisplayName(comp.Value));
        return parts.Count == 0 ? "(all competitions)" : "(" + string.Join(" ", parts) + ")";
    }
}
