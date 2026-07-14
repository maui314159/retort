using System.ComponentModel;
using System.Text;
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

[McpServerToolType]
public sealed class StatisticsTools
{
    private readonly MatchDataLoader _matchLoader;

    public StatisticsTools(MatchDataLoader matchLoader) => _matchLoader = matchLoader;

    [McpServerTool, Description(
        "Get the biggest victories (largest goal margins) in the dataset. " +
        "Returns matches with the highest goal differentials.")]
    public string get_biggest_wins(
        [Description("Competition filter. Optional. Options: 'Brasileirão', 'Copa do Brasil', 'Copa Libertadores'")]
        string? competition = null,
        [Description("Season/year filter. Optional.")]
        int? season = null,
        [Description("Maximum number of results to return. Default 10.")]
        int limit = 10)
    {
        var matches = _matchLoader.Matches.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(competition))
            matches = matches.Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));

        if (season.HasValue)
            matches = matches.Where(m => m.Season == season.Value);

        var biggest = matches
            .Where(m => m.HomeGoals != m.AwayGoals) // exclude draws
            .OrderByDescending(m => Math.Abs(m.HomeGoals - m.AwayGoals))
            .ThenByDescending(m => m.HomeGoals + m.AwayGoals)
            .Take(limit)
            .ToList();

        if (biggest.Count == 0)
            return "No matches found with the specified filters.";

        var sb = new StringBuilder();
        sb.AppendLine($"Biggest victories{(string.IsNullOrWhiteSpace(competition) ? "" : $" in {competition}")}{(season.HasValue ? $" {season.Value}" : "")}:");
        sb.AppendLine();

        for (int i = 0; i < biggest.Count; i++)
        {
            var m = biggest[i];
            var diff = Math.Abs(m.HomeGoals - m.AwayGoals);
            sb.AppendLine($"{i + 1}. {m.Date:yyyy-MM-dd}: {m.HomeTeam} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeam} ({m.Competition}, diff: {diff})");
        }

        return sb.ToString();
    }

    [McpServerTool, Description(
        "Get average goals per match and home/away win rates. " +
        "Provides statistical overview of scoring patterns.")]
    public string get_average_goals(
        [Description("Competition filter. Optional.")]
        string? competition = null,
        [Description("Season/year filter. Optional.")]
        int? season = null)
    {
        var matches = _matchLoader.Matches.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(competition))
            matches = matches.Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));

        if (season.HasValue)
            matches = matches.Where(m => m.Season == season.Value);

        var matchList = matches.ToList();

        if (matchList.Count == 0)
            return "No matches found with the specified filters.";

        var totalGoals = matchList.Sum(m => m.HomeGoals + m.AwayGoals);
        var avgGoals = Math.Round((double)totalGoals / matchList.Count, 2);
        var homeWins = matchList.Count(m => m.IsHomeWin);
        var awayWins = matchList.Count(m => m.IsAwayWin);
        var draws = matchList.Count(m => m.IsDraw);
        var avgHomeGoals = Math.Round(matchList.Average(m => m.HomeGoals), 2);
        var avgAwayGoals = Math.Round(matchList.Average(m => m.AwayGoals), 2);

        var sb = new StringBuilder();
        sb.AppendLine($"Statistics{(string.IsNullOrWhiteSpace(competition) ? "" : $" for {competition}")}{(season.HasValue ? $" {season.Value}" : "")}:");
        sb.AppendLine($"  Total matches: {matchList.Count}");
        sb.AppendLine($"  Total goals: {totalGoals}");
        sb.AppendLine($"  Average goals per match: {avgGoals}");
        sb.AppendLine($"  Average home goals: {avgHomeGoals}");
        sb.AppendLine($"  Average away goals: {avgAwayGoals}");
        sb.AppendLine($"  Home win rate: {Math.Round((double)homeWins / matchList.Count * 100, 1)}% ({homeWins}/{matchList.Count})");
        sb.AppendLine($"  Away win rate: {Math.Round((double)awayWins / matchList.Count * 100, 1)}% ({awayWins}/{matchList.Count})");
        sb.AppendLine($"  Draw rate: {Math.Round((double)draws / matchList.Count * 100, 1)}% ({draws}/{matchList.Count})");

        // Top scoring teams
        var teamGoals = new Dictionary<string, (int goals, int matches)>(StringComparer.OrdinalIgnoreCase);
        foreach (var m in matchList)
        {
            var homeNorm = TeamNameNormalizer.Normalize(m.HomeTeam);
            var awayNorm = TeamNameNormalizer.Normalize(m.AwayTeam);

            if (!teamGoals.ContainsKey(homeNorm))
                teamGoals[homeNorm] = (0, 0);
            if (!teamGoals.ContainsKey(awayNorm))
                teamGoals[awayNorm] = (0, 0);

            teamGoals[homeNorm] = (teamGoals[homeNorm].goals + m.HomeGoals, teamGoals[homeNorm].matches + 1);
            teamGoals[awayNorm] = (teamGoals[awayNorm].goals + m.AwayGoals, teamGoals[awayNorm].matches + 1);
        }

        var topScoring = teamGoals
            .Where(kvp => kvp.Value.matches >= 5)
            .OrderByDescending(kvp => (double)kvp.Value.goals / kvp.Value.matches)
            .Take(5)
            .ToList();

        if (topScoring.Count > 0)
        {
            sb.AppendLine();
            sb.AppendLine("  Top scoring teams (goals per match, min 5 matches):");
            foreach (var (team, (goals, matchCount)) in topScoring)
            {
                sb.AppendLine($"    {team}: {Math.Round((double)goals / matchCount, 2)} goals/match ({goals} goals in {matchCount} matches)");
            }
        }

        return sb.ToString();
    }
}
