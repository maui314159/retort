using System.ComponentModel;
using System.Text;
using BrazilianSoccerMcp.Data;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

/// <summary>
/// MCP tools for searching and querying match data.
/// </summary>
[McpServerToolType]
public static class MatchTools
{
    private static DataLoader Data => DataStore.Loader;

    [McpServerTool, Description("Search matches by team, season, competition, date range, or any combination. Returns formatted match list with head-to-head summary.")]
    public static string SearchMatches(
        [Description("Team name to search for (home, away, or either). Examples: 'Flamengo', 'Palmeiras'.")] string? team = null,
        [Description("Second team name for head-to-head queries. Use with 'team' to find matches between two specific teams.")] string? team2 = null,
        [Description("Competition filter: 'Brasileirão', 'Copa do Brasil', or 'Libertadores'.")] string? competition = null,
        [Description("Season year filter, e.g. '2023'.")] int? season = null,
        [Description("Start date in yyyy-MM-dd format.")] string? dateFrom = null,
        [Description("End date in yyyy-MM-dd format.")] string? dateTo = null,
        [Description("Maximum number of matches to return (default 25).")] int limit = 25)
    {
        var query = Data.Matches.AsEnumerable();

        // Filter by team
        bool hasTeam1 = !string.IsNullOrWhiteSpace(team);
        bool hasTeam2 = !string.IsNullOrWhiteSpace(team2);

        if (hasTeam1 && hasTeam2)
        {
            query = query.Where(m =>
                (TeamNormalizer.Matches(m.HomeTeam, team!) && TeamNormalizer.Matches(m.AwayTeam, team2!)) ||
                (TeamNormalizer.Matches(m.HomeTeam, team2!) && TeamNormalizer.Matches(m.AwayTeam, team!)));
        }
        else if (hasTeam1)
        {
            query = query.Where(m =>
                TeamNormalizer.Matches(m.HomeTeam, team!) ||
                TeamNormalizer.Matches(m.AwayTeam, team!));
        }

        if (!string.IsNullOrWhiteSpace(competition))
            query = query.Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));

        if (season.HasValue)
            query = query.Where(m => m.Season == season.Value);

        if (DateTime.TryParse(dateFrom, out var df))
            query = query.Where(m => m.Date >= df);

        if (DateTime.TryParse(dateTo, out var dt))
            query = query.Where(m => m.Date <= dt);

        var matches = query.OrderByDescending(m => m.Date).Take(limit).ToList();
        var totalCount = query.Count();

        if (matches.Count == 0)
            return "No matches found matching the criteria.";

        var sb = new StringBuilder();

        // If head-to-head, compute stats
        if (hasTeam1 && hasTeam2)
        {
            AppendHeadToHead(sb, matches, team!, team2!, totalCount);
        }

        sb.AppendLine($"Matches ({Math.Min(limit, totalCount)} of {totalCount} shown):");
        sb.AppendLine();

        foreach (var m in matches)
        {
            var roundInfo = m.Round != null ? $"Round {m.Round}" : m.Stage != null ? m.Stage : "";
            sb.AppendLine($"  {m.Date:yyyy-MM-dd}: {m.HomeTeam} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeam} ({m.Competition} {roundInfo})".TrimEnd());
        }

        return sb.ToString().TrimEnd();
    }

    [McpServerTool, Description("Get head-to-head record between two teams across all competitions. Shows wins, draws, and goals for each team.")]
    public static string GetHeadToHead(
        [Description("First team name.")] string team1,
        [Description("Second team name.")] string team2)
    {
        var matches = Data.Matches
            .Where(m =>
                (TeamNormalizer.Matches(m.HomeTeam, team1) && TeamNormalizer.Matches(m.AwayTeam, team2)) ||
                (TeamNormalizer.Matches(m.HomeTeam, team2) && TeamNormalizer.Matches(m.AwayTeam, team1)))
            .OrderByDescending(m => m.Date)
            .ToList();

        if (matches.Count == 0)
            return $"No matches found between {team1} and {team2}.";

        var sb = new StringBuilder();
        AppendHeadToHead(sb, matches, team1, team2, matches.Count);

        // Last 10 matches
        sb.AppendLine();
        sb.AppendLine("Recent matches:");
        foreach (var m in matches.Take(10))
        {
            var roundInfo = m.Round != null ? $"Round {m.Round}" : m.Stage != null ? m.Stage : "";
            sb.AppendLine($"  {m.Date:yyyy-MM-dd}: {m.HomeTeam} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeam} ({m.Competition} {roundInfo})".TrimEnd());
        }

        return sb.ToString().TrimEnd();
    }

    [McpServerTool, Description("Get all matches for a specific competition in a given season. Returns ordered by round or date.")]
    public static string GetCompetitionMatches(
        [Description("Competition name: 'Brasileirão', 'Copa do Brasil', or 'Libertadores'.")] string competition,
        [Description("Season year, e.g. 2023.")] int season,
        [Description("Maximum matches to return (default 50).")] int limit = 50)
    {
        var matches = Data.Matches
            .Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase) && m.Season == season)
            .OrderBy(m => m.Date)
            .Take(limit)
            .ToList();

        if (matches.Count == 0)
            return $"No matches found for {competition} in {season}.";

        var sb = new StringBuilder();
        sb.AppendLine($"{competition} {season} - Matches ({matches.Count} shown):");
        sb.AppendLine();

        foreach (var m in matches)
        {
            var extra = m.Round != null ? $"(Round {m.Round})" : m.Stage != null ? $"({m.Stage})" : "";
            sb.AppendLine($"  {m.Date:yyyy-MM-dd}: {m.HomeTeam} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeam} {extra}".TrimEnd());
        }

        return sb.ToString().TrimEnd();
    }

    private static void AppendHeadToHead(StringBuilder sb, List<MatchRecord> matches, string team1, string team2, int total)
    {
        // Compute from full dataset, not just the limited page
        var allMatches = Data.Matches
            .Where(m =>
                (TeamNormalizer.Matches(m.HomeTeam, team1) && TeamNormalizer.Matches(m.AwayTeam, team2)) ||
                (TeamNormalizer.Matches(m.HomeTeam, team2) && TeamNormalizer.Matches(m.AwayTeam, team1)))
            .ToList();

        int t1Wins = 0, t2Wins = 0, draws = 0;
        int t1Goals = 0, t2Goals = 0;

        foreach (var m in allMatches)
        {
            bool t1IsHome = TeamNormalizer.Matches(m.HomeTeam, team1);
            int t1G = t1IsHome ? m.HomeGoals : m.AwayGoals;
            int t2G = t1IsHome ? m.AwayGoals : m.HomeGoals;

            t1Goals += t1G;
            t2Goals += t2G;

            if (t1G > t2G) t1Wins++;
            else if (t2G > t1G) t2Wins++;
            else draws++;
        }

        sb.AppendLine($"{team1} vs {team2} - Head-to-Head:");
        sb.AppendLine($"  Total matches: {total}");
        sb.AppendLine($"  {team1} wins: {t1Wins}, {team2} wins: {t2Wins}, Draws: {draws}");
        sb.AppendLine($"  {team1} goals: {t1Goals}, {team2} goals: {t2Goals}");
        sb.AppendLine();
    }
}