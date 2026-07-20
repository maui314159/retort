using System.ComponentModel;
using System.Text;
using BrazilianSoccerMcp.Models;
using BrazilianSoccerMcp.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

[McpServerToolType]
public class MatchTools(SoccerDataService dataService)
{
    [McpServerTool(Name = "find_matches"), Description(
        "Find soccer matches. Search by team name(s), season year, and/or competition. " +
        "Competitions: 'brasileirao', 'copa do brasil', 'libertadores'. " +
        "Returns match results with dates, scores, and competition info.")]
    public string FindMatches(
        [Description("Team name to search for (e.g., 'Flamengo', 'Palmeiras')")]
        string? team = null,
        [Description("Second team name for head-to-head search (e.g., 'Fluminense')")]
        string? team2 = null,
        [Description("Season year (e.g., 2023)")]
        int? season = null,
        [Description("Competition filter: 'brasileirao', 'copa do brasil', 'libertadores'")]
        string? competition = null,
        [Description("Maximum number of results (default 50, max 200)")]
        int limit = 50)
    {
        limit = Math.Clamp(limit, 1, 200);
        var matches = dataService.FindMatches(team, team2, season, competition, limit);

        if (matches.Count == 0)
        {
            var filters = BuildFilterDescription(team, team2, season, competition);
            return $"No matches found{filters}.";
        }

        var sb = new StringBuilder();

        if (team != null && team2 != null)
        {
            var h2h = dataService.GetHeadToHead(team, team2);
            sb.AppendLine($"Head-to-Head: {team} vs {team2} ({h2h.TotalMatches} total matches in dataset)");
            sb.AppendLine($"Record: {team} {h2h.Team1Wins}W - {h2h.Draws}D - {h2h.Team2Wins}W {team2}");
            sb.AppendLine($"Goals: {team} {h2h.Team1Goals} - {h2h.Team2Goals} {team2}");
            sb.AppendLine();
        }

        sb.AppendLine($"Showing {matches.Count} matches:");
        foreach (var m in matches)
        {
            var dateStr = m.DateTime?.ToString("yyyy-MM-dd") ?? "unknown date";
            var roundInfo = m.Round != null ? $" | Round {m.Round}" : "";
            var stageInfo = m.Stage != null ? $" | {m.Stage}" : "";
            sb.AppendLine($"  {dateStr}: {m.HomeTeam} {m.HomeGoal}-{m.AwayGoal} {m.AwayTeam} ({m.Competition}{roundInfo}{stageInfo}) Season {m.Season}");
        }

        return sb.ToString().TrimEnd();
    }

    [McpServerTool(Name = "get_recent_matches"), Description(
        "Get the most recent matches for a team across all competitions.")]
    public string GetRecentMatches(
        [Description("Team name (e.g., 'Corinthians')")]
        string team,
        [Description("Number of recent matches to return (default 10)")]
        int count = 10)
    {
        count = Math.Clamp(count, 1, 50);
        var matches = dataService.FindMatches(team, limit: count);

        if (matches.Count == 0)
            return $"No matches found for '{team}'.";

        var sb = new StringBuilder();
        sb.AppendLine($"Recent matches for {team}:");
        foreach (var m in matches)
        {
            var dateStr = m.DateTime?.ToString("yyyy-MM-dd") ?? "unknown";
            var result = GetResultLabel(team, m);
            sb.AppendLine($"  [{result}] {dateStr}: {m.HomeTeam} {m.HomeGoal}-{m.AwayGoal} {m.AwayTeam} ({m.Competition})");
        }
        return sb.ToString().TrimEnd();
    }

    private static string GetResultLabel(string team, UnifiedMatch m)
    {
        bool isHome = Services.TeamNameNormalizer.Matches(m.HomeTeam, team);
        var teamGoals = isHome ? m.HomeGoal : m.AwayGoal;
        var oppGoals = isHome ? m.AwayGoal : m.HomeGoal;
        if (teamGoals > oppGoals) return "W";
        if (teamGoals == oppGoals) return "D";
        return "L";
    }

    private static string BuildFilterDescription(string? team, string? team2, int? season, string? competition)
    {
        var parts = new List<string>();
        if (team != null) parts.Add($"team='{team}'");
        if (team2 != null) parts.Add($"team2='{team2}'");
        if (season != null) parts.Add($"season={season}");
        if (competition != null) parts.Add($"competition='{competition}'");
        return parts.Count > 0 ? $" with filters: {string.Join(", ", parts)}" : "";
    }
}
