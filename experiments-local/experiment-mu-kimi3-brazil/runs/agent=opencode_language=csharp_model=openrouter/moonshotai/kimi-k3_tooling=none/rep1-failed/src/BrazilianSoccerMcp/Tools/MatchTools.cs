using System.ComponentModel;
using System.Text;
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

/// <summary>MCP tools answering questions about matches (category 1 of the spec).</summary>
[McpServerToolType]
public sealed class MatchTools
{
    private readonly SoccerDataService _data;
    public MatchTools(SoccerDataService data) => _data = data;

    [McpServerTool(Name = "find_matches"),
     Description("Find matches by team(s), competition, season and/or date range. " +
                 "Team names may be given with or without state suffix or accents " +
                 "(e.g. 'Flamengo', 'Palmeiras-SP', 'Sao Paulo'). " +
                 "Competition examples: 'Brasileirão', 'Copa do Brasil', 'Libertadores'. " +
                 "Dates in ISO format yyyy-MM-dd. Returns the most recent matches first.")]
    public string FindMatches(
        [Description("First team name (optional)")] string? team1 = null,
        [Description("Second team name (optional)")] string? team2 = null,
        [Description("Competition filter (optional)")] string? competition = null,
        [Description("Season year, e.g. 2023 (optional)")] int? season = null,
        [Description("Start of date range, yyyy-MM-dd (optional)")] string? from_date = null,
        [Description("End of date range, yyyy-MM-dd (optional)")] string? to_date = null,
        [Description("Max matches to return (default 20)")] int limit = 20)
    {
        var from = DataLoader.ParseDate(from_date);
        var to = DataLoader.ParseDate(to_date);
        var games = _data.FindMatches(team1, team2, competition, season, from, to, limit);

        if (games.Count == 0)
            return "No matches found for the given criteria.";

        var title = (team1, team2) switch
        {
            (not null, not null) => $"{team1} vs {team2}",
            (not null, null) => $"{team1} matches",
            _ => "Matches",
        };
        if (season is not null) title += $" ({season})";
        if (competition is not null) title += $" [{competition}]";

        var sb = new StringBuilder($"{title}:\n");
        foreach (var m in games) sb.AppendLine($"- {m}");
        return sb.ToString();
    }

    [McpServerTool(Name = "get_head_to_head"),
     Description("Compare two teams head-to-head across the whole dataset: " +
                 "wins, draws, goals and the list of matches. " +
                 "Example: 'Compare Palmeiras and Santos head-to-head'.")]
    public string GetHeadToHead(
        [Description("First team name")] string team1,
        [Description("Second team name")] string team2,
        [Description("Max matches to list (default 15)")] int limit = 15)
    {
        var h2h = _data.GetHeadToHead(team1, team2);
        if (h2h.Matches.Count == 0)
            return $"No matches between {team1} and {team2} found in the dataset.";

        var sb = new StringBuilder();
        sb.AppendLine($"{team1} vs {team2}:");
        foreach (var m in h2h.Matches.Take(limit)) sb.AppendLine($"- {m}");
        if (h2h.Matches.Count > limit)
            sb.AppendLine($"... ({h2h.Matches.Count - limit} more matches in dataset)");
        sb.AppendLine();
        sb.AppendLine($"Head-to-head in dataset: {team1} {h2h.Team1Wins} wins, " +
                      $"{team2} {h2h.Team2Wins} wins, {h2h.Draws} draws. " +
                      $"Goals: {h2h.Team1Goals}-{h2h.Team2Goals}.");
        return sb.ToString();
    }

    [McpServerTool(Name = "find_derbies"),
     Description("Find classic Brazilian derby matches (Fla-Flu, Grenal, Derby Paulista, Majestoso, " +
                 "Choque-Rei, Ba-Vi and others), optionally filtered by season.")]
    public string FindDerbies(
        [Description("Season year, e.g. 2023 (optional)")] int? season = null,
        [Description("Max matches to return (default 30)")] int limit = 30)
    {
        var derbies = _data.FindDerbies(season, limit);
        if (derbies.Count == 0)
            return season is null ? "No derby matches found in the dataset."
                                  : $"No derby matches found for season {season}.";

        var sb = new StringBuilder(season is null ? "Classic derbies:\n" : $"Classic derbies in {season}:\n");
        foreach (var (m, name) in derbies)
            sb.AppendLine($"- {m} [{name}]");
        return sb.ToString();
    }

    [McpServerTool(Name = "get_team_competitions"),
     Description("List every competition a team appears in across all datasets. " +
                 "Example: 'What competitions has Palmeiras played in?'")]
    public string GetTeamCompetitions(
        [Description("Team name")] string team)
    {
        var comps = _data.GetCompetitionsForTeam(team);
        if (comps.Count == 0) return $"No data found for team '{team}'.";
        var sb = new StringBuilder($"{team} appears in these competitions:\n");
        foreach (var c in comps) sb.AppendLine($"- {c}");
        return sb.ToString();
    }
}
