using System.ComponentModel;
using BrazilianSoccerMcp.Server.Data;
using BrazilianSoccerMcp.Server.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Server.Tools;

[McpServerToolType]
public sealed class MatchTools
{
    private readonly MatchService _matchService;

    public MatchTools(SoccerDataContext context)
    {
        _matchService = new MatchService(context);
    }

    [McpServerTool]
    [Description("Search for matches between teams, by competition, season, date range, or stage.")]
    public string SearchMatches(
        [Description("Team name to search for (optional)")] string? team = null,
        [Description("Opponent team name (optional). When provided with team, returns head-to-head matches.")] string? opponent = null,
        [Description("Competition filter, e.g. Brasileirão, Copa do Brasil, Copa Libertadores (optional)")] string? competition = null,
        [Description("Season year filter (optional)")] int? season = null,
        [Description("Start date filter in ISO format yyyy-MM-dd (optional)")] string? fromDate = null,
        [Description("End date filter in ISO format yyyy-MM-dd (optional)")] string? toDate = null,
        [Description("Tournament stage or round filter (optional)")] string? stage = null,
        [Description("Maximum number of matches to return (default 50)")] int? limit = 50)
    {
        var from = ParseDate(fromDate);
        var to = ParseDate(toDate);

        if (!string.IsNullOrWhiteSpace(team) && !string.IsNullOrWhiteSpace(opponent))
        {
            var matches = _matchService.FindMatches(team: team, opponent: opponent, competition: competition,
                season: season, from: from, to: to, stage: stage, limit: limit);
            return _matchService.FormatMatches(team, opponent, matches);
        }

        var results = _matchService.FindMatches(team: team, competition: competition, season: season,
            from: from, to: to, stage: stage, limit: limit);

        if (!string.IsNullOrWhiteSpace(team))
        {
            return _matchService.FormatMatches(team, "opponents", results);
        }

        return _matchService.FormatMatches("Team", "opponents", results);
    }

    private static DateTime? ParseDate(string? value)
    {
        if (string.IsNullOrWhiteSpace(value))
            return null;
        if (DateTime.TryParse(value, out var date))
            return date;
        return null;
    }
}
