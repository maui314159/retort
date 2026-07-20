using System.ComponentModel;
using System.Text;
using BrazilianSoccerMcp.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

[McpServerToolType]
public class StatisticsTools(SoccerDataService dataService)
{
    [McpServerTool(Name = "get_aggregate_stats"), Description(
        "Get aggregate statistics: total matches, average goals per match, home/draw/away win rates. " +
        "Optionally filter by competition.")]
    public string GetAggregateStats(
        [Description("Competition filter (optional): 'brasileirao', 'copa do brasil', 'libertadores'")]
        string? competition = null)
    {
        var stats = dataService.GetGlobalStats(competition);

        if (stats.TotalMatches == 0)
            return $"No match data found{(competition != null ? $" for '{competition}'" : "")}.";

        var sb = new StringBuilder();
        var header = competition != null ? $"Statistics for {competition}" : "Overall Statistics (all competitions)";
        sb.AppendLine(header);
        sb.AppendLine($"Total Matches: {stats.TotalMatches:N0}");
        sb.AppendLine($"Average Goals per Match: {stats.AvgGoalsPerMatch:F2}");
        sb.AppendLine($"Home Wins: {stats.HomeWins:N0} ({stats.HomeWinRate:F1}%)");
        sb.AppendLine($"Draws: {stats.Draws:N0} ({stats.DrawRate:F1}%)");
        sb.AppendLine($"Away Wins: {stats.AwayWins:N0} ({stats.AwayWinRate:F1}%)");

        return sb.ToString().TrimEnd();
    }

    [McpServerTool(Name = "get_biggest_wins"), Description(
        "Find the biggest victories (largest goal differences) in the dataset. " +
        "Optionally filter by competition.")]
    public string GetBiggestWins(
        [Description("Competition filter (optional): 'brasileirao', 'copa do brasil', 'libertadores'")]
        string? competition = null,
        [Description("Number of biggest wins to return (default 10)")]
        int count = 10)
    {
        count = Math.Clamp(count, 1, 50);
        var matches = dataService.GetBiggestWins(competition, count);

        if (matches.Count == 0)
            return $"No matches found{(competition != null ? $" for '{competition}'" : "")}.";

        var sb = new StringBuilder();
        sb.AppendLine($"Biggest wins{(competition != null ? $" in {competition}" : "")} ({matches.Count} results):");
        for (int i = 0; i < matches.Count; i++)
        {
            var m = matches[i];
            var dateStr = m.DateTime?.ToString("yyyy-MM-dd") ?? "unknown";
            var diff = Math.Abs(m.HomeGoal - m.AwayGoal);
            sb.AppendLine($"  {i + 1}. {dateStr}: {m.HomeTeam} {m.HomeGoal}-{m.AwayGoal} {m.AwayTeam} (diff: {diff}, {m.Competition})");
        }
        return sb.ToString().TrimEnd();
    }

    [McpServerTool(Name = "get_top_scoring_teams"), Description(
        "Find the teams that scored the most goals in a given season and competition.")]
    public string GetTopScoringTeams(
        [Description("Season year (e.g., 2023)")]
        int? season = null,
        [Description("Competition: 'brasileirao', 'copa do brasil', 'libertadores'. Omit for all.")]
        string? competition = null,
        [Description("Number of top teams to return (default 10)")]
        int count = 10)
    {
        count = Math.Clamp(count, 1, 30);
        var matches = dataService.FindMatches(season: season, competition: competition, limit: int.MaxValue);

        if (matches.Count == 0)
            return $"No matches found for the given filters.";

        var teamGoals = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);

        foreach (var m in matches)
        {
            var home = TeamNameNormalizer.Normalize(m.HomeTeam);
            var away = TeamNameNormalizer.Normalize(m.AwayTeam);

            teamGoals.TryGetValue(home, out var hg);
            teamGoals[home] = hg + m.HomeGoal;

            teamGoals.TryGetValue(away, out var ag);
            teamGoals[away] = ag + m.AwayGoal;
        }

        var top = teamGoals
            .OrderByDescending(kv => kv.Value)
            .Take(count)
            .ToList();

        var sb = new StringBuilder();
        var header = $"Top Scoring Teams{(competition != null ? $" in {competition}" : "")}{(season != null ? $" {season}" : "")}:";
        sb.AppendLine(header);
        for (int i = 0; i < top.Count; i++)
            sb.AppendLine($"  {i + 1}. {top[i].Key}: {top[i].Value} goals");

        return sb.ToString().TrimEnd();
    }
}
