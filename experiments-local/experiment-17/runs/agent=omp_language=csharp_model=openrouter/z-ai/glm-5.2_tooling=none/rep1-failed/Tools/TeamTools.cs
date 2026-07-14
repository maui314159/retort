// ============================================================================
// File: Tools/TeamTools.cs
// ----------------------------------------------------------------------------
// Context: MCP tools for the "Team Queries" category: per-team records
// (overall / home / away, by season and competition), competitions a team has
// played in, and which team scored the most goals in a competition season.
// ============================================================================

using System.ComponentModel;
using System.Globalization;
using System.Text;
using BrazilianSoccerMcp.Data;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

[McpServerToolType]
public sealed class TeamTools
{
    private readonly SoccerDataStore _store;
    public TeamTools(SoccerDataStore store) => _store = store;

    /// <summary>Win/draw/loss record for a team, optionally by season/competition/venue.</summary>
    [McpServerTool, Description(
        "Return a team's record (matches, wins, draws, losses, goals for/against, " +
        "points, win rate). Filter by competition, season, and venue (home/away/both).")]
    public string TeamStats(
        [Description("Team name (e.g. Corinthians, Palmeiras-SP).")] string team,
        [Description("Competition filter (optional).")] string? competition = null,
        [Description("Season year (optional).")] int? season = null,
        [Description("Venue: home, away, or both (default both).")] string venue = "both")
    {
        var matches = _store.MatchesForTeamFiltered(team, competition, season).ToList();
        if (matches.Count == 0)
            return $"No matches found for {team}" +
                   (competition is null ? "" : $" in {competition}") +
                   (season is null ? "." : $" ({season}).");

        var rec = _store.RecordForTeam(team, matches, venue);
        var label = $"{rec.Team} {venue.ToLowerInvariant()} record" +
                    (season is null ? "" : $" ({season})") +
                    (competition is null ? "" : $" {competition}");
        return Formatting.FormatRecord(rec, label);
    }

    /// <summary>List the competitions and seasons a team appears in.</summary>
    [McpServerTool, Description(
        "List all competitions and seasons a team has played in across the dataset.")]
    public string TeamCompetitions([Description("Team name.")] string team)
    {
        var comps = _store.CompetitionsForTeam(team);
        var seasons = _store.SeasonsForTeam(team);
        if (comps.Count == 0)
            return $"No matches found for {team}.";

        var sb = new StringBuilder();
        sb.AppendLine($"{team} appears in:");
        foreach (var c in comps) sb.AppendLine($"- {c}");
        sb.AppendLine();
        sb.AppendLine($"Seasons on file: {string.Join(", ", seasons)}");
        return sb.ToString().TrimEnd();
    }

    public string TopScoringTeam(
        [Description("Competition, e.g. Brasileirão.")] string competition,
        [Description("Season year.")] int season,
        [Description("How many teams to list (default 5).")] int top = 5)
    {
        if (top <= 0) top = 5;
        var seasonMatches = SoccerDataStore.Dedupe(_store.Matches
            .Where(m => SoccerDataStore.CompetitionMatches(m.Competition, competition) && m.Season == season))
            .ToList();

        if (seasonMatches.Count == 0)
            return $"No matches found for {competition} {season}.";

        var goals = new Dictionary<TeamKey, int>(Comparer);
        foreach (var m in seasonMatches)
        {
            if (m.HomeGoals is null || m.AwayGoals is null) continue;
            goals[m.HomeKey] = (goals.GetValueOrDefault(m.HomeKey)) + m.HomeGoals.Value;
            goals[m.AwayKey] = (goals.GetValueOrDefault(m.AwayKey)) + m.AwayGoals.Value;
        }

        var ranked = goals
            .OrderByDescending(kv => kv.Value)
            .Take(top)
            .Select(kv => $"{TeamNameNormalizer.DisplayName(kv.Key, kv.Key.Full)}: {kv.Value} goals")
            .ToList();

        var sb = new StringBuilder();
        sb.AppendLine($"Top scoring teams in {competition} {season}:");
        for (int i = 0; i < ranked.Count; i++)
            sb.AppendLine($"{i + 1}. {ranked[i]}");
        return sb.ToString().TrimEnd();
    }

    private sealed class TeamKeyComparer : IEqualityComparer<TeamKey>
    {
        public bool Equals(TeamKey x, TeamKey y) =>
            string.Equals(x.Bare, y.Bare, StringComparison.Ordinal) &&
            string.Equals(x.Suffix ?? "", y.Suffix ?? "", StringComparison.Ordinal);
        public int GetHashCode(TeamKey obj) => HashCode.Combine(obj.Bare, obj.Suffix ?? "");
    }
    private static readonly TeamKeyComparer Comparer = new();
}
