using System.ComponentModel;
using BrazilianSoccerMcp.Server.Data;
using BrazilianSoccerMcp.Server.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Server.Tools;

[McpServerToolType]
public sealed class StatisticsTools
{
    private readonly StatisticsService _statisticsService;

    public StatisticsTools(SoccerDataContext context)
    {
        _statisticsService = new StatisticsService(context);
    }

    [McpServerTool]
    [Description("Calculate the average goals per match, optionally filtered by competition and season.")]
    public string GetAverageGoals(
        [Description("Competition filter (optional)")] string? competition = null,
        [Description("Season year filter (optional)")] int? season = null)
    {
        return _statisticsService.GetAverageGoals(competition, season);
    }

    [McpServerTool]
    [Description("Show the biggest wins (largest goal margins) in the dataset, optionally filtered by competition.")]
    public string GetBiggestWins(
        [Description("Competition filter (optional)")] string? competition = null,
        [Description("Maximum number of results (default 10)")] int? limit = 10)
    {
        return _statisticsService.GetBiggestWins(competition, limit);
    }

    [McpServerTool]
    [Description("Calculate the home win rate, optionally filtered by competition and season.")]
    public string GetHomeWinRate(
        [Description("Competition filter (optional)")] string? competition = null,
        [Description("Season year filter (optional)")] int? season = null)
    {
        return _statisticsService.GetHomeWinRate(competition, season);
    }
}
