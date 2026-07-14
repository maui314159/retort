// ============================================================================
// File: Tools/StatisticsTools.cs
// ----------------------------------------------------------------------------
// Context: MCP tools for the "Statistical Analysis" category: average goals
// per match, biggest victories, home vs away win rates, and the team with the
// best away record. These aggregate across the unified match collection and
// can be filtered by competition/season.
// ============================================================================

using System.ComponentModel;
using System.Globalization;
using System.Text;
using BrazilianSoccerMcp.Data;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

[McpServerToolType]
public sealed class StatisticsTools
{
    private readonly SoccerDataStore _store;
    public StatisticsTools(SoccerDataStore store) => _store = store;

    /// <summary>Average goals per match and home/away/draw rates.</summary>
    [McpServerTool, Description(
        "Aggregate statistics for a competition/season: average goals per match, " +
        "and home-win / draw / away-win rates.")]
    public string AverageGoals(
        [Description("Competition filter (optional).")] string? competition = null,
        [Description("Season year (optional).")] int? season = null)
    {
        var matches = SoccerDataStore.Dedupe(_store.Matches
            .Where(m => competition is null || SoccerDataStore.CompetitionMatches(m.Competition, competition!))
            .Where(m => season is null || m.Season == season)
            .Where(m => m.HomeGoals is not null && m.AwayGoals is not null))
            .ToList();

        if (matches.Count == 0)
            return "No scored matches found for the given criteria.";

        int totalGoals = matches.Sum(m => m.HomeGoals!.Value + m.AwayGoals!.Value);
        int homeWins = matches.Count(m => m.HomeGoals > m.AwayGoals);
        int awayWins = matches.Count(m => m.AwayGoals > m.HomeGoals);
        int draws = matches.Count(m => m.HomeGoals == m.AwayGoals);
        double avg = (double)totalGoals / matches.Count;

        var sb = new StringBuilder();
        sb.AppendLine(CultureInfo.InvariantCulture,
            $"Matches analysed: {matches.Count}");
        sb.AppendLine(CultureInfo.InvariantCulture,
            $"Average goals per match: {avg:0.00}");
        sb.AppendLine(CultureInfo.InvariantCulture,
            $"Home win rate: {Pct(homeWins, matches.Count)} ({homeWins}/{matches.Count})");
        sb.AppendLine(CultureInfo.InvariantCulture,
            $"Away win rate: {Pct(awayWins, matches.Count)} ({awayWins}/{matches.Count})");
        sb.AppendLine(CultureInfo.InvariantCulture,
            $"Draw rate: {Pct(draws, matches.Count)} ({draws}/{matches.Count})");
        return sb.ToString().TrimEnd();
    }

    /// <summary>Biggest victories (by goal difference).</summary>
    [McpServerTool, Description(
        "List the biggest victories (largest goal differences) in the dataset, " +
        "optionally filtered by competition/season.")]
    public string BiggestWins(
        [Description("Competition filter (optional).")] string? competition = null,
        [Description("Season year (optional).")] int? season = null,
        [Description("How many results (default 10).")] int limit = 10)
    {
        if (limit <= 0) limit = 10;
        var matches = SoccerDataStore.Dedupe(_store.Matches
            .Where(m => competition is null || SoccerDataStore.CompetitionMatches(m.Competition, competition!))
            .Where(m => season is null || m.Season == season)
            .Where(m => m.HomeGoals is not null && m.AwayGoals is not null && m.GoalDifference > 0))
            .OrderByDescending(m => m.GoalDifference)
            .ThenByDescending(m => m.TotalGoals)
            .Take(limit)
            .ToList();

        if (matches.Count == 0)
            return "No scored matches found for the given criteria.";

        var sb = new StringBuilder();
        sb.AppendLine("Biggest victories in dataset:");
        int i = 1;
        foreach (var m in matches)
        {
            sb.AppendLine($"{i}. {Formatting.DateOnly(m.Date)}: {m.HomeTeamRaw} " +
                          $"{m.HomeGoals}-{m.AwayGoals} {m.AwayTeamRaw} ({m.Competition})");
            i++;
        }
        return sb.ToString().TrimEnd();
    }

    /// <summary>Team with the best away record in a competition season.</summary>
    [McpServerTool, Description(
        "Find the team with the best away record in a competition season " +
        "(highest away win rate, minimum 5 away matches).")]
    public string BestAwayRecord(
        [Description("Competition, e.g. Brasileirão.")] string competition,
        [Description("Season year.")] int season,
        [Description("How many teams to list (default 5).")] int limit = 5)
    {
        if (limit <= 0) limit = 5;
        var seasonMatches = SoccerDataStore.Dedupe(_store.Matches
            .Where(m => SoccerDataStore.CompetitionMatches(m.Competition, competition) && m.Season == season)
            .Where(m => m.HomeGoals is not null && m.AwayGoals is not null))
            .ToList();

        if (seasonMatches.Count == 0)
            return $"No matches found for {competition} {season}.";

        var awayTeams = seasonMatches.Select(m => m.AwayKey).Distinct(ByKey).ToList();
        var records = new List<(TeamKey Key, TeamRecord Rec)>();
        foreach (var k in awayTeams)
        {
            var rec = _store.RecordForTeam(k.Full, seasonMatches, venue: "away");
            if (rec.Matches >= 5) records.Add((k, rec));
        }

        if (records.Count == 0)
            return "No team played at least 5 away matches in that competition/season.";

        var ranked = records
            .OrderByDescending(r => r.Rec.WinRate)
            .ThenByDescending(r => r.Rec.Wins)
            .Take(limit)
            .ToList();

        var sb = new StringBuilder();
        sb.AppendLine($"Best away records in {competition} {season}:");
        int i = 1;
        foreach (var (k, rec) in ranked)
        {
            var name = TeamNameNormalizer.DisplayName(k, k.Full);
            sb.AppendLine(CultureInfo.InvariantCulture,
                $"{i}. {name}: {rec.Wins}W {rec.Draws}D {rec.Losses}L from {rec.Matches} away " +
                $"(win rate {rec.WinRate:0%}, GF {rec.GoalsFor}, GA {rec.GoalsAgainst})");
            i++;
        }
        return sb.ToString().TrimEnd();
    }

    private static string Pct(int part, int whole) =>
        whole == 0 ? "0.0%" : ((double)part / whole).ToString("0.0%", CultureInfo.InvariantCulture);

    private sealed class TeamKeyComparer : IEqualityComparer<TeamKey>
    {
        public bool Equals(TeamKey x, TeamKey y) =>
            string.Equals(x.Bare, y.Bare, StringComparison.Ordinal) &&
            string.Equals(x.Suffix ?? "", y.Suffix ?? "", StringComparison.Ordinal);
        public int GetHashCode(TeamKey obj) => HashCode.Combine(obj.Bare, obj.Suffix ?? "");
    }
    private static readonly TeamKeyComparer ByKey = new();
}
