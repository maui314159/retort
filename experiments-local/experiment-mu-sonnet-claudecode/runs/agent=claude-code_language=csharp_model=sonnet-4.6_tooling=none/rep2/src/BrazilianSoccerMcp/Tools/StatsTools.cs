using System.ComponentModel;
using System.Globalization;
using System.Text;
using BrazilianSoccerMcp.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

[McpServerToolType]
public sealed class StatsTools
{
    private readonly DataService _data;

    public StatsTools(DataService data) => _data = data;

    private static bool CompetitionMatches(string competition, string filter)
    {
        var comparer = CultureInfo.InvariantCulture.CompareInfo;
        return comparer.IndexOf(competition, filter, CompareOptions.IgnoreCase | CompareOptions.IgnoreNonSpace) >= 0;
    }

    [McpServerTool]
    [Description("Find the biggest victories (largest goal difference) in the dataset.")]
    public string GetBiggestWins(
        [Description("Competition filter (optional).")] string? competition = null,
        [Description("Season year filter (optional).")] int? season = null,
        [Description("Number of results to return (default 10, max 50).")] int limit = 10)
    {
        limit = Math.Clamp(limit, 1, 50);

        var matches = _data.Matches
            .Where(m => m.HomeGoal.HasValue && m.AwayGoal.HasValue)
            .AsEnumerable();

        if (!string.IsNullOrWhiteSpace(competition))
            matches = matches.Where(m => CompetitionMatches(m.Competition, competition));

        if (season.HasValue)
            matches = matches.Where(m => m.Season == season);

        var results = matches
            .Select(m => new
            {
                Match = m,
                GoalDiff = Math.Abs(m.HomeGoal!.Value - m.AwayGoal!.Value)
            })
            .OrderByDescending(x => x.GoalDiff)
            .ThenByDescending(x => x.Match.HomeGoal!.Value + x.Match.AwayGoal!.Value)
            .Take(limit)
            .ToList();

        if (results.Count == 0)
            return "No matches found for the given criteria.";

        var sb = new StringBuilder();
        sb.AppendLine($"Biggest victories{(competition != null ? $" in {competition}" : "")}{(season.HasValue ? $" ({season})" : "")}:");
        sb.AppendLine();

        for (int i = 0; i < results.Count; i++)
        {
            var m = results[i].Match;
            var dateStr = m.Date?.ToString("yyyy-MM-dd") ?? "Unknown";
            sb.AppendLine($"{i + 1}. {dateStr}: {m.HomeTeam} {m.HomeGoal}-{m.AwayGoal} {m.AwayTeam} | {m.Competition} | Season: {m.Season}");
        }

        return sb.ToString();
    }

    [McpServerTool]
    [Description("Get aggregate statistics for a competition or all competitions: goals per match, home win rate, etc.")]
    public string GetCompetitionStats(
        [Description("Competition name filter (optional, e.g. 'Brasileirao', 'Copa do Brasil').")] string? competition = null,
        [Description("Season year filter (optional).")] int? season = null)
    {
        var matches = _data.Matches
            .Where(m => m.HomeGoal.HasValue && m.AwayGoal.HasValue)
            .AsEnumerable();

        if (!string.IsNullOrWhiteSpace(competition))
            matches = matches.Where(m => CompetitionMatches(m.Competition, competition));

        if (season.HasValue)
            matches = matches.Where(m => m.Season == season);

        var matchList = matches.ToList();

        if (matchList.Count == 0)
            return "No matches found for the given criteria.";

        int totalGoals = matchList.Sum(m => m.HomeGoal!.Value + m.AwayGoal!.Value);
        int homeWins = matchList.Count(m => m.HomeGoal > m.AwayGoal);
        int awayWins = matchList.Count(m => m.AwayGoal > m.HomeGoal);
        int draws = matchList.Count(m => m.HomeGoal == m.AwayGoal);
        double goalsPerMatch = matchList.Count > 0 ? (double)totalGoals / matchList.Count : 0;

        var sb = new StringBuilder();
        sb.AppendLine($"Statistics{(competition != null ? $" for {competition}" : " (all competitions)")}{(season.HasValue ? $" | Season: {season}" : "")}:");
        sb.AppendLine();
        sb.AppendLine($"Total matches: {matchList.Count}");
        sb.AppendLine($"Total goals: {totalGoals}");
        sb.AppendLine($"Goals per match: {goalsPerMatch:F2}");
        sb.AppendLine($"Home wins: {homeWins} ({(double)homeWins / matchList.Count * 100:F1}%)");
        sb.AppendLine($"Away wins: {awayWins} ({(double)awayWins / matchList.Count * 100:F1}%)");
        sb.AppendLine($"Draws: {draws} ({(double)draws / matchList.Count * 100:F1}%)");

        if (!season.HasValue)
        {
            var bySeason = matchList
                .Where(m => m.Season.HasValue)
                .GroupBy(m => m.Season!.Value)
                .OrderBy(g => g.Key)
                .Select(g => new { Season = g.Key, Count = g.Count(), Goals = g.Sum(m => m.HomeGoal!.Value + m.AwayGoal!.Value) })
                .ToList();

            if (bySeason.Count > 0)
            {
                sb.AppendLine();
                sb.AppendLine("Matches by season:");
                foreach (var s in bySeason.TakeLast(10))
                    sb.AppendLine($"  {s.Season}: {s.Count} matches, {s.Goals} goals ({(double)s.Goals / s.Count:F2} per match)");
            }
        }

        return sb.ToString();
    }

    [McpServerTool]
    [Description("Get the top scoring teams or teams with best records across a competition and season.")]
    public string GetTopTeams(
        [Description("Ranking criteria: 'goals' (most goals scored), 'wins' (most wins), 'undefeated' (fewest losses), 'home' (best home record), 'away' (best away record).")] string criteria = "goals",
        [Description("Competition filter (optional).")] string? competition = null,
        [Description("Season year filter (optional).")] int? season = null,
        [Description("Number of top teams to return (default 10).")] int limit = 10)
    {
        limit = Math.Clamp(limit, 1, 30);

        var matches = _data.Matches
            .Where(m => m.HomeGoal.HasValue && m.AwayGoal.HasValue)
            .AsEnumerable();

        if (!string.IsNullOrWhiteSpace(competition))
            matches = matches.Where(m => CompetitionMatches(m.Competition, competition));

        if (season.HasValue)
            matches = matches.Where(m => m.Season == season);

        var matchList = matches.ToList();

        if (matchList.Count == 0)
            return "No matches found for the given criteria.";

        var teamStats = new Dictionary<string, (int Goals, int Wins, int Losses, int Played, int HomeWins, int HomePlayed, int AwayWins, int AwayPlayed)>(StringComparer.OrdinalIgnoreCase);

        foreach (var m in matchList)
        {
            var home = m.NormalizedHomeTeam.Length > 0 ? m.NormalizedHomeTeam : m.HomeTeam;
            var away = m.NormalizedAwayTeam.Length > 0 ? m.NormalizedAwayTeam : m.AwayTeam;

            if (!teamStats.ContainsKey(home)) teamStats[home] = default;
            if (!teamStats.ContainsKey(away)) teamStats[away] = default;

            var hs = teamStats[home];
            var as_ = teamStats[away];

            hs.Goals += m.HomeGoal!.Value;
            as_.Goals += m.AwayGoal!.Value;
            hs.Played++; as_.Played++;
            hs.HomePlayed++; as_.AwayPlayed++;

            if (m.HomeGoal > m.AwayGoal) { hs.Wins++; as_.Losses++; hs.HomeWins++; }
            else if (m.AwayGoal > m.HomeGoal) { as_.Wins++; hs.Losses++; as_.AwayWins++; }

            teamStats[home] = hs;
            teamStats[away] = as_;
        }

        var sorted = criteria.ToLowerInvariant() switch
        {
            "wins" => teamStats.OrderByDescending(t => t.Value.Wins).ThenByDescending(t => t.Value.Goals),
            "undefeated" => teamStats.OrderBy(t => t.Value.Losses).ThenByDescending(t => t.Value.Wins),
            "home" => teamStats.Where(t => t.Value.HomePlayed > 0).OrderByDescending(t => (double)t.Value.HomeWins / t.Value.HomePlayed),
            "away" => teamStats.Where(t => t.Value.AwayPlayed > 0).OrderByDescending(t => (double)t.Value.AwayWins / t.Value.AwayPlayed),
            _ => teamStats.OrderByDescending(t => t.Value.Goals).ThenByDescending(t => t.Value.Wins),
        };

        var results = sorted.Take(limit).ToList();

        var sb = new StringBuilder();
        sb.AppendLine($"Top teams by {criteria}{(competition != null ? $" | {competition}" : "")}{(season.HasValue ? $" | Season: {season}" : "")}:");
        sb.AppendLine();

        for (int i = 0; i < results.Count; i++)
        {
            var (name, s) = results[i];
            var homeRate = s.HomePlayed > 0 ? $"{(double)s.HomeWins / s.HomePlayed * 100:F0}%" : "N/A";
            var awayRate = s.AwayPlayed > 0 ? $"{(double)s.AwayWins / s.AwayPlayed * 100:F0}%" : "N/A";
            sb.AppendLine($"{i + 1}. {name,-30} W:{s.Wins,-4} L:{s.Losses,-4} P:{s.Played,-4} G:{s.Goals,-5} Home%:{homeRate,-6} Away%:{awayRate}");
        }

        return sb.ToString();
    }

    [McpServerTool]
    [Description("Get a summary of all data loaded in the server: counts of matches and players per dataset.")]
    public string GetDataSummary()
    {
        if (!_data.IsLoaded)
            return "Data is not loaded yet.";

        var byComp = _data.Matches
            .GroupBy(m => m.Competition)
            .OrderByDescending(g => g.Count())
            .ToList();

        var sb = new StringBuilder();
        sb.AppendLine("Brazilian Soccer MCP Server - Data Summary");
        sb.AppendLine(new string('=', 45));
        sb.AppendLine($"Total matches: {_data.Matches.Count}");
        sb.AppendLine($"Total players (FIFA): {_data.Players.Count}");
        sb.AppendLine();
        sb.AppendLine("Matches by competition:");
        foreach (var c in byComp)
            sb.AppendLine($"  - {c.Key}: {c.Count()} matches");

        var seasons = _data.Matches
            .Where(m => m.Season.HasValue)
            .Select(m => m.Season!.Value)
            .Distinct()
            .OrderBy(s => s)
            .ToList();

        if (seasons.Count > 0)
        {
            sb.AppendLine();
            sb.AppendLine($"Seasons covered: {seasons.Min()} - {seasons.Max()} ({seasons.Count} seasons)");
        }

        return sb.ToString();
    }
}
