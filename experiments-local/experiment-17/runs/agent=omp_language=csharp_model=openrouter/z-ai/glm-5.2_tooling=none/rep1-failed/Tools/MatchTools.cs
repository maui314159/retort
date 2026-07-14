// ============================================================================
// File: Tools/MatchTools.cs
// ----------------------------------------------------------------------------
// Context: MCP tools answering the "Match Queries" category of the spec:
// find matches by team, opponent, competition, season, and date range, plus
// head-to-head records and "last match" lookups.
//
// Registered with the MCP host via WithTools<MatchTools>(); the SoccerDataStore
// singleton is constructor-injected.
// ============================================================================

using System.ComponentModel;
using System.Globalization;
using System.Text;
using BrazilianSoccerMcp.Data;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

[McpServerToolType]
public sealed class MatchTools
{
    private readonly SoccerDataStore _store;
    public MatchTools(SoccerDataStore store) => _store = store;

    /// <summary>Find matches by team, opponent, competition, season and/or date range.</summary>
    [McpServerTool, Description(
        "Search Brazilian soccer matches. Filter by team, opponent, competition " +
        "(Brasileirão, Copa do Brasil, Copa Libertadores, Serie A), season, and/or " +
        "a date range (YYYY-MM-DD). Returns a formatted list with date, score and competition.")]
    public string SearchMatches(
        [Description("Team name (e.g. Flamengo, Palmeiras-SP). Optional.")] string? team = null,
        [Description("Opponent team name. Optional.")] string? opponent = null,
        [Description("Competition name. Optional.")] string? competition = null,
        [Description("Season year, e.g. 2023. Optional.")] int? season = null,
        [Description("Start date YYYY-MM-DD inclusive. Optional.")] string? fromDate = null,
        [Description("End date YYYY-MM-DD inclusive. Optional.")] string? toDate = null,
        [Description("Maximum number of matches to return (default 50).")] int limit = 50)
    {
        if (limit <= 0) limit = 50;

        IEnumerable<SoccerMatch> matches = _store.Matches;

        if (!string.IsNullOrWhiteSpace(team) && !string.IsNullOrWhiteSpace(opponent))
        {
            matches = _store.MatchesBetween(team!, opponent!, competition);
            if (season is not null) matches = matches.Where(m => m.Season == season);
        }
        else if (!string.IsNullOrWhiteSpace(team))
        {
            matches = _store.MatchesForTeamFiltered(team, competition, season,
                ParseDate(fromDate), ParseDate(toDate));
        }
        else
        {
            matches = matches
                .Where(m => competition is null || SoccerDataStore.CompetitionMatches(m.Competition, competition!))
                .Where(m => season is null || m.Season == season)
                .Where(m => fromDate is null || (m.Date is { } d && d >= ParseDate(fromDate)))
                .Where(m => toDate is null || (m.Date is { } d && d <= ParseDate(toDate)));
        }

        var ordered = matches.OrderByDescending(m => m.Date ?? DateTime.MinValue).ToList();
        if (ordered.Count == 0)
            return "No matches found for the given criteria.";

        var shown = ordered.Take(limit).Select(Formatting.FormatMatch);
        var sb = new StringBuilder();
        sb.AppendLine($"Found {ordered.Count} match(es)" +
                      (limit < ordered.Count ? $" (showing first {limit})" : "") + ":");
        foreach (var line in shown) sb.AppendLine(line);
        return sb.ToString().TrimEnd();
    }

    /// <summary>Head-to-head record between two teams.</summary>
    [McpServerTool, Description(
        "Compare two teams head-to-head: lists their matches and the aggregate " +
        "win/draw/loss record across all competitions in the dataset.")]
    public string HeadToHead(
        [Description("First team name.")] string team1,
        [Description("Second team name.")] string team2,
        [Description("Competition filter (optional).")] string? competition = null,
        [Description("Max matches to list (default 30).")] int limit = 30)
    {
        if (limit <= 0) limit = 30;
        var matches = _store.MatchesBetween(team1, team2, competition)
            .OrderByDescending(m => m.Date ?? DateTime.MinValue).ToList();

        if (matches.Count == 0)
            return $"No matches found between {team1} and {team2}" +
                   (competition is null ? "." : $" in {competition}.");

        var r1 = _store.RecordForTeam(team1, matches);
        var r2 = _store.RecordForTeam(team2, matches);
        // Draws are draws for both; recompute draw count from either record.
        int draws = r1.Draws;

        var sb = new StringBuilder();
        sb.AppendLine($"{r1.Team} vs {r2.Team} (head-to-head in dataset):");
        foreach (var m in matches.Take(limit)) sb.AppendLine(Formatting.FormatMatch(m));
        if (matches.Count > limit) sb.AppendLine($"... ({matches.Count - limit} more matches in dataset)");
        sb.AppendLine();
        sb.Append($"Head-to-head in dataset: {r1.Team} {r1.Wins} wins, {r2.Team} {r2.Wins} wins, {draws} draws");
        return sb.ToString();
    }

    /// <summary>Most recent match between two teams.</summary>
    [McpServerTool, Description(
        "Find the most recent match between two teams. Returns the date, score and competition.")]
    public string LastMatch(
        [Description("First team name.")] string team1,
        [Description("Second team name.")] string team2)
    {
        var match = _store.MatchesBetween(team1, team2)
            .Where(m => m.Date is not null)
            .OrderByDescending(m => m.Date)
            .FirstOrDefault();

        if (match is null)
            return $"No matches found between {team1} and {team2}.";

        return $"Last meeting between the teams:\n{Formatting.FormatMatch(match)}";
    }

    private static DateTime? ParseDate(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return null;
        return DateTime.TryParseExact(s.Trim(), "yyyy-MM-dd", CultureInfo.InvariantCulture,
            DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out var d)
            ? d
            : DateTime.TryParse(s, CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out var loose)
                ? loose : (DateTime?)null;
    }
}
