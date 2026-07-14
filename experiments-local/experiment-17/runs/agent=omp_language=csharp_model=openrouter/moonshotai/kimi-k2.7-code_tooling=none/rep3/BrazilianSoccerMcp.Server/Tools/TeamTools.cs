using System.ComponentModel;
using BrazilianSoccerMcp.Server.Data;
using BrazilianSoccerMcp.Server.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Server.Tools;

[McpServerToolType]
public sealed class TeamTools
{
    private readonly TeamService _teamService;
    private readonly MatchService _matchService;

    public TeamTools(SoccerDataContext context)
    {
        _teamService = new TeamService(context);
        _matchService = new MatchService(context);
    }

    [McpServerTool]
    [Description("Get match history and statistics for a team. Optionally filter by competition, season, or home-only matches.")]
    public string GetTeamStatistics(
        [Description("Team name")] string team,
        [Description("Competition filter (optional)")] string? competition = null,
        [Description("Season year filter (optional)")] int? season = null,
        [Description("Whether to consider only home matches (default false)")] bool homeOnly = false)
    {
        var stats = _teamService.GetStatistics(team, competition, season, homeOnly);
        var scope = $"{team} {(homeOnly ? "home" : "overall")} record";
        if (!string.IsNullOrWhiteSpace(competition)) scope += $" ({competition})";
        if (season.HasValue) scope += $" {season.Value}";
        return _teamService.FormatStatistics(stats, scope);
    }

    [McpServerTool]
    [Description("Compare two teams head-to-head across all available match data.")]
    public string CompareTeams(
        [Description("First team name")] string teamA,
        [Description("Second team name")] string teamB,
        [Description("Competition filter (optional)")] string? competition = null,
        [Description("Season year filter (optional)")] int? season = null)
    {
        var matches = _matchService.FindMatches(team: teamA, opponent: teamB,
            competition: competition, season: season);
        return _matchService.FormatMatches(teamA, teamB, matches);
    }
}
