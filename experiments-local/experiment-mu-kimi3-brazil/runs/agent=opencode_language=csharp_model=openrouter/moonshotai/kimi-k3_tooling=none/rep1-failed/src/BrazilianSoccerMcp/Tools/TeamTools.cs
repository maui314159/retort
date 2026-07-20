using System.ComponentModel;
using System.Text;
using BrazilianSoccerMcp.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

/// <summary>MCP tools answering questions about teams (category 2 of the spec).</summary>
[McpServerToolType]
public sealed class TeamTools
{
    private readonly SoccerDataService _data;
    public TeamTools(SoccerDataService data) => _data = data;

    [McpServerTool(Name = "get_team_record"),
     Description("Get a team's win/draw/loss record with goals scored/conceded and win rate. " +
                 "Filter by season and/or competition and by venue: 'home', 'away' or 'all'. " +
                 "Example: 'What is Corinthians' home record in 2022?' -> team='Corinthians', season=2022, venue='home'.")]
    public string GetTeamRecord(
        [Description("Team name")] string team,
        [Description("Season year, e.g. 2022 (optional)")] int? season = null,
        [Description("Competition filter (optional)")] string? competition = null,
        [Description("Venue: 'home', 'away' or 'all' (default 'all')")] string venue = "all")
    {
        var r = _data.GetTeamRecord(team, season, competition, venue);
        if (r.Matches == 0)
            return $"No matches found for '{team}' with the given filters.";

        var scope = new StringBuilder(team);
        scope.Append($" {venue} record");
        if (season is not null) scope.Append($" ({season}");
        if (competition is not null) scope.Append(season is null ? $" ({competition}" : $" {competition}");
        if (season is not null || competition is not null) scope.Append(')');

        var sb = new StringBuilder($"{scope}:\n");
        sb.AppendLine($"- Matches: {r.Matches}");
        sb.AppendLine($"- Wins: {r.Wins}, Draws: {r.Draws}, Losses: {r.Losses}");
        sb.AppendLine($"- Goals For: {r.GoalsFor}, Goals Against: {r.GoalsAgainst}");
        sb.AppendLine($"- Win rate: {r.WinRate:F1}%");
        return sb.ToString();
    }

    [McpServerTool(Name = "list_teams"),
     Description("List all team names present in the dataset, optionally filtered by competition. " +
                 "Useful to discover the exact spelling used in the data.")]
    public string ListTeams(
        [Description("Competition filter (optional)")] string? competition = null,
        [Description("Max teams to list (default 100)")] int limit = 100)
    {
        var teams = _data.GetTeams(competition);
        if (teams.Count == 0) return "No teams found.";
        var sb = new StringBuilder(competition is null
            ? $"Teams in dataset ({teams.Count}):\n"
            : $"Teams in '{competition}' ({teams.Count}):\n");
        foreach (var t in teams.Take(limit)) sb.AppendLine($"- {t}");
        if (teams.Count > limit) sb.AppendLine($"... ({teams.Count - limit} more)");
        return sb.ToString();
    }

    [McpServerTool(Name = "get_best_records"),
     Description("Rank teams by best home or away record (win rate, minimum 10 matches). " +
                 "Example: 'Which team has the best away record?' -> venue='away'.")]
    public string GetBestRecords(
        [Description("Venue: 'home' or 'away'")] string venue,
        [Description("Season year (optional)")] int? season = null,
        [Description("Max teams to return (default 10)")] int limit = 10)
    {
        var venueKey = venue.Trim().ToLowerInvariant() is "away" ? "away" : "home";
        var rows = _data.GetBestRecords(venueKey, season, limit);
        if (rows.Count == 0) return "No data for the given filters.";

        var sb = new StringBuilder(season is null
            ? $"Best {venueKey} records (all seasons, min 10 matches):\n"
            : $"Best {venueKey} records in {season} (min 10 matches):\n");
        var i = 1;
        foreach (var (team, r) in rows)
        {
            sb.AppendLine($"{i}. {team} - {r.WinRate:F1}% win rate " +
                          $"({r.Wins}W, {r.Draws}D, {r.Losses}L in {r.Matches} matches, " +
                          $"{r.GoalsFor} GF / {r.GoalsAgainst} GA)");
            i++;
        }
        return sb.ToString();
    }
}
