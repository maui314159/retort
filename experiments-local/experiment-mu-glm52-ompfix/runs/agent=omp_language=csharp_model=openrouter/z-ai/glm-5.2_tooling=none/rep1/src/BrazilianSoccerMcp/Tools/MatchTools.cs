// Brazilian Soccer MCP Server - Match & Team MCP tools
//
// Context: These tool methods are exposed to the LLM via the Model Context
// Protocol SDK. Each [McpServerTool] method is automatically registered with
// WithToolsFromAssembly in Program.cs. The SoccerDataService is injected via
// constructor by ActivatorUtilities (see Program.cs registration).
//
// Output philosophy: tools return human-readable formatted strings so an LLM
// can relay them directly, rather than raw JSON the client would have to
// re-format. Where structured data is useful, the return type is a serialized
// shape; the spec's answer formats are plain text, so plain text is primary.

using System.ComponentModel;
using BrazilianSoccerMcp.Models;
using BrazilianSoccerMcp.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

/// <summary>MCP tools for querying matches, teams, and head-to-head records.</summary>
[McpServerToolType]
public sealed class MatchTools
{
    private readonly SoccerDataService _data;
    public MatchTools(SoccerDataService data) => _data = data;

    [McpServerTool, Description("Find matches by team, opponent, competition, season, and/or date range. At least one team name should be provided. Competitions: Brasileirão, Copa do Brasil, Libertadores.")]
    public string FindMatches(
        [Description("Team name to search for (home or away). Optional.")] string? team = null,
        [Description("Opponent team name. Optional; when provided with team, returns head-to-head matches.")] string? opponent = null,
        [Description("Competition filter, e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores'. Optional.")] string? competition = null,
        [Description("Season year filter, e.g. 2023. Optional.")] int? season = null,
        [Description("Start date (yyyy-MM-dd). Optional.")] string? fromDate = null,
        [Description("End date (yyyy-MM-dd). Optional.")] string? toDate = null,
        [Description("Maximum number of matches to return. Default 20.")] int limit = 20)
    {
        _data.EnsureLoaded();

        IEnumerable<Match> query = _data.Matches;

        if (!string.IsNullOrWhiteSpace(team))
        {
            if (!string.IsNullOrWhiteSpace(opponent))
                query = _data.HeadToHead(team, opponent);
            else
            {
                var key = _data.ResolveTeamKey(team);
                query = query.Where(m => m.HomeTeamKey == key || m.AwayTeamKey == key);
            }
        }

        if (!string.IsNullOrWhiteSpace(competition))
            query = query.Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));
        if (season.HasValue)
            query = query.Where(m => m.Season == season);
        if (DateTime.TryParse(fromDate, out var from))
            query = query.Where(m => m.Date >= from);
        if (DateTime.TryParse(toDate, out var to))
            query = query.Where(m => m.Date <= to);

        var results = query.OrderByDescending(m => m.Date ?? DateTime.MinValue).Take(Math.Max(1, limit)).ToList();
        if (results.Count == 0)
            return "No matches found matching the criteria.";

        var total = query.Count();
        var header = BuildHeader(team, opponent, competition, season, from, to, results.Count, total);
        var lines = results.Select(m => "- " + m.Summary);
        return header + string.Join("\n", lines);
    }

    private static string BuildHeader(string? team, string? opponent, string? competition, int? season, DateTime? from, DateTime? to, int shown, int total)
    {
        var parts = new List<string>();
        if (!string.IsNullOrWhiteSpace(team))
        {
            parts.Add(!string.IsNullOrWhiteSpace(opponent)
                ? $"{team} vs {opponent}"
                : team!);
        }
        if (!string.IsNullOrWhiteSpace(competition)) parts.Add(competition!);
        if (season.HasValue) parts.Add(season.Value.ToString());
        if (from.HasValue) parts.Add($"from {from:yyyy-MM-dd}");
        if (to.HasValue) parts.Add($"to {to:yyyy-MM-dd}");

        var header = parts.Count > 0 ? string.Join(" | ", parts) : "Matches";
        return $"{header} ({shown} shown of {total}):\n";
    }

    [McpServerTool, Description("Get win/loss/draw statistics for a team, optionally filtered by competition, season, or home/away.")]
    public string GetTeamStats(
        [Description("Team name, e.g. 'Flamengo', 'Palmeiras-SP'.")] string team,
        [Description("Competition filter. Optional.")] string? competition = null,
        [Description("Season year. Optional.")] int? season = null,
        [Description("Restrict to home matches. Default false.")] bool homeOnly = false,
        [Description("Restrict to away matches. Default false.")] bool awayOnly = false)
    {
        _data.EnsureLoaded();
        var stats = _data.StatsForTeam(team, competition, season, homeOnly, awayOnly);
        var scope = string.Join(", ", new[] { competition, season?.ToString() }.Where(s => !string.IsNullOrWhiteSpace(s)));
        if (homeOnly) scope = (string.IsNullOrEmpty(scope) ? "" : scope + ", ") + "home";
        if (awayOnly) scope = (string.IsNullOrEmpty(scope) ? "" : scope + ", ") + "away";
        return stats.Format(string.IsNullOrWhiteSpace(scope) ? null : scope);
    }

    [McpServerTool, Description("Compare two teams head-to-head: matches played, wins, draws, losses for each.")]
    public string CompareTeams(
        [Description("First team name.")] string teamA,
        [Description("Second team name.")] string teamB)
    {
        _data.EnsureLoaded();
        var matches = _data.HeadToHead(teamA, teamB).OrderBy(m => m.Date ?? DateTime.MinValue).ToList();

        if (matches.Count == 0)
            return $"No head-to-head matches found between {teamA} and {teamB}.";

        var keyA = _data.ResolveTeamKey(teamA);
        int winsA = 0, winsB = 0, draws = 0;
        foreach (var m in matches)
        {
            if (!m.HomeGoals.HasValue || !m.AwayGoals.HasValue) continue;
            bool aIsHome = m.HomeTeamKey == keyA;
            int aGoals = aIsHome ? m.HomeGoals.Value : m.AwayGoals.Value;
            int bGoals = aIsHome ? m.AwayGoals.Value : m.HomeGoals.Value;
            if (aGoals > bGoals) winsA++;
            else if (aGoals < bGoals) winsB++;
            else draws++;
        }

        var lines = matches.Take(20).Select(m => "- " + m.Summary);
        var truncated = matches.Count > 20 ? $"\n... ({matches.Count - 20} more matches in dataset)" : "";

        return $"Head-to-head: {_data.DisplayName(keyA)} vs {_data.DisplayName(_data.ResolveTeamKey(teamB))}\n" +
               $"Matches: {matches.Count} | {_data.DisplayName(keyA)} {winsA} wins, {_data.DisplayName(_data.ResolveTeamKey(teamB))} {winsB} wins, {draws} draws\n\n" +
               string.Join("\n", lines) + truncated;
    }
}
