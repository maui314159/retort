using System.ComponentModel;
using System.Globalization;
using System.Text;
using BrazilianSoccerMcp.Models;
using BrazilianSoccerMcp.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

[McpServerToolType]
public sealed class MatchTools
{
    private readonly DataService _data;

    public MatchTools(DataService data) => _data = data;

    private static bool CompetitionMatches(string competition, string filter)
    {
        var comparer = CultureInfo.InvariantCulture.CompareInfo;
        return comparer.IndexOf(competition, filter, CompareOptions.IgnoreCase | CompareOptions.IgnoreNonSpace) >= 0;
    }

    [McpServerTool]
    [Description("Search for soccer matches by team, competition, season, or date range. Returns a formatted list of matches with scores and competition details.")]
    public string SearchMatches(
        [Description("Team name to search for (home or away). Supports partial names like 'Flamengo', 'Palmeiras', 'Corinthians'.")] string? team = null,
        [Description("Opponent team name (optional, use together with 'team' to find head-to-head matches).")] string? opponent = null,
        [Description("Competition name filter: 'Brasileirao', 'Copa do Brasil', 'Libertadores', or leave empty for all.")] string? competition = null,
        [Description("Season year (e.g. 2023, 2019).")] int? season = null,
        [Description("Start date filter (ISO format: 2023-01-01).")] string? dateFrom = null,
        [Description("End date filter (ISO format: 2023-12-31).")] string? dateTo = null,
        [Description("Maximum number of results to return (default 20, max 100).")] int limit = 20)
    {
        limit = Math.Clamp(limit, 1, 100);

        DateTime? from = dateFrom != null && DateTime.TryParse(dateFrom, out var df) ? df : null;
        DateTime? to = dateTo != null && DateTime.TryParse(dateTo, out var dt) ? dt : null;

        var matches = _data.Matches.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(team))
            matches = matches.Where(m =>
                TeamNameNormalizer.Matches(m.HomeTeam, team) ||
                TeamNameNormalizer.Matches(m.AwayTeam, team));

        if (!string.IsNullOrWhiteSpace(opponent))
            matches = matches.Where(m =>
                TeamNameNormalizer.Matches(m.HomeTeam, opponent) ||
                TeamNameNormalizer.Matches(m.AwayTeam, opponent));

        if (!string.IsNullOrWhiteSpace(competition))
            matches = matches.Where(m => CompetitionMatches(m.Competition, competition));

        if (season.HasValue)
            matches = matches.Where(m => m.Season == season);

        if (from.HasValue)
            matches = matches.Where(m => m.Date >= from);

        if (to.HasValue)
            matches = matches.Where(m => m.Date <= to);

        var results = matches.OrderByDescending(m => m.Date).Take(limit).ToList();

        if (results.Count == 0)
            return "No matches found for the given criteria.";

        var sb = new StringBuilder();
        sb.AppendLine($"Found {results.Count} match(es):");
        sb.AppendLine();

        foreach (var m in results)
        {
            var dateStr = m.Date?.ToString("yyyy-MM-dd") ?? "Unknown date";
            var score = m.HomeGoal.HasValue && m.AwayGoal.HasValue
                ? $"{m.HomeGoal}-{m.AwayGoal}"
                : "vs";
            var round = m.Round != null ? $" (Round {m.Round})" : "";
            var stage = m.Stage != null ? $" [{m.Stage}]" : "";
            sb.AppendLine($"- {dateStr}: {m.HomeTeam} {score} {m.AwayTeam} | {m.Competition}{round}{stage} | Season: {m.Season}");
        }

        return sb.ToString();
    }

    [McpServerTool]
    [Description("Get head-to-head record between two teams including all matches in the dataset.")]
    public string GetHeadToHead(
        [Description("First team name.")] string team1,
        [Description("Second team name.")] string team2,
        [Description("Competition filter (optional).")] string? competition = null,
        [Description("Maximum number of matches to show (default 10).")] int limit = 10)
    {
        limit = Math.Clamp(limit, 1, 50);

        var matches = _data.Matches
            .Where(m =>
                (TeamNameNormalizer.Matches(m.HomeTeam, team1) && TeamNameNormalizer.Matches(m.AwayTeam, team2)) ||
                (TeamNameNormalizer.Matches(m.HomeTeam, team2) && TeamNameNormalizer.Matches(m.AwayTeam, team1)))
            .ToList();

        if (!string.IsNullOrWhiteSpace(competition))
            matches = matches.Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase)).ToList();

        if (matches.Count == 0)
            return $"No matches found between '{team1}' and '{team2}'.";

        int team1Wins = 0, team2Wins = 0, draws = 0;
        int team1Goals = 0, team2Goals = 0;

        foreach (var m in matches)
        {
            if (!m.HomeGoal.HasValue || !m.AwayGoal.HasValue) continue;

            bool team1IsHome = TeamNameNormalizer.Matches(m.HomeTeam, team1);
            int t1Goals = team1IsHome ? m.HomeGoal.Value : m.AwayGoal.Value;
            int t2Goals = team1IsHome ? m.AwayGoal.Value : m.HomeGoal.Value;

            team1Goals += t1Goals;
            team2Goals += t2Goals;

            if (t1Goals > t2Goals) team1Wins++;
            else if (t2Goals > t1Goals) team2Wins++;
            else draws++;
        }

        var sb = new StringBuilder();
        sb.AppendLine($"Head-to-Head: {team1} vs {team2}");
        sb.AppendLine($"Total matches: {matches.Count}");
        sb.AppendLine($"{team1}: {team1Wins} wins | {team2}: {team2Wins} wins | Draws: {draws}");
        sb.AppendLine($"Goals: {team1} {team1Goals} - {team2Goals} {team2}");
        sb.AppendLine();
        sb.AppendLine($"Recent matches (last {Math.Min(limit, matches.Count)}):");

        foreach (var m in matches.OrderByDescending(m => m.Date).Take(limit))
        {
            var dateStr = m.Date?.ToString("yyyy-MM-dd") ?? "Unknown";
            var score = m.HomeGoal.HasValue && m.AwayGoal.HasValue ? $"{m.HomeGoal}-{m.AwayGoal}" : "vs";
            sb.AppendLine($"- {dateStr}: {m.HomeTeam} {score} {m.AwayTeam} | {m.Competition} | Season: {m.Season}");
        }

        return sb.ToString();
    }

    [McpServerTool]
    [Description("Get standings/table for a competition in a given season, calculated from match results.")]
    public string GetStandings(
        [Description("Season year (e.g. 2019, 2023).")] int season,
        [Description("Competition: 'Brasileirao', 'Copa do Brasil', 'Libertadores'. Defaults to Brasileirao.")] string competition = "Brasileirao")
    {
        var matches = _data.Matches
            .Where(m => m.Season == season
                && CompetitionMatches(m.Competition, competition)
                && m.HomeGoal.HasValue && m.AwayGoal.HasValue)
            .ToList();

        if (matches.Count == 0)
            return $"No match data found for {competition} season {season}.";

        var table = new Dictionary<string, TeamStats>(StringComparer.OrdinalIgnoreCase);

        foreach (var m in matches)
        {
            var home = m.NormalizedHomeTeam.Length > 0 ? m.NormalizedHomeTeam : m.HomeTeam;
            var away = m.NormalizedAwayTeam.Length > 0 ? m.NormalizedAwayTeam : m.AwayTeam;

            if (!table.ContainsKey(home)) table[home] = new TeamStats { Name = home };
            if (!table.ContainsKey(away)) table[away] = new TeamStats { Name = away };

            var hg = m.HomeGoal!.Value;
            var ag = m.AwayGoal!.Value;

            table[home].Played++;
            table[away].Played++;
            table[home].GoalsFor += hg;
            table[home].GoalsAgainst += ag;
            table[away].GoalsFor += ag;
            table[away].GoalsAgainst += hg;

            if (hg > ag) { table[home].Wins++; table[away].Losses++; }
            else if (hg < ag) { table[away].Wins++; table[home].Losses++; }
            else { table[home].Draws++; table[away].Draws++; }
        }

        var sorted = table.Values
            .OrderByDescending(t => t.Points)
            .ThenByDescending(t => t.GoalDiff)
            .ThenByDescending(t => t.GoalsFor)
            .ToList();

        var sb = new StringBuilder();
        sb.AppendLine($"{competition} {season} Standings (calculated from {matches.Count} matches):");
        sb.AppendLine();
        sb.AppendLine($"{"Pos",-4} {"Team",-30} {"P",-4} {"W",-4} {"D",-4} {"L",-4} {"GF",-4} {"GA",-4} {"GD",-5} {"Pts",-4}");
        sb.AppendLine(new string('-', 70));

        for (int i = 0; i < sorted.Count; i++)
        {
            var t = sorted[i];
            sb.AppendLine($"{i + 1,-4} {t.Name,-30} {t.Played,-4} {t.Wins,-4} {t.Draws,-4} {t.Losses,-4} {t.GoalsFor,-4} {t.GoalsAgainst,-4} {t.GoalDiff,-5} {t.Points,-4}");
        }

        return sb.ToString();
    }

    private class TeamStats
    {
        public string Name { get; set; } = "";
        public int Played { get; set; }
        public int Wins { get; set; }
        public int Draws { get; set; }
        public int Losses { get; set; }
        public int GoalsFor { get; set; }
        public int GoalsAgainst { get; set; }
        public int GoalDiff => GoalsFor - GoalsAgainst;
        public int Points => Wins * 3 + Draws;
    }
}
