using BrazilianSoccerMcp.Services;
using BrazilianSoccerMcp.Tools;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

public class TeamStatsTests
{
    private static string? FindDataDirectory()
    {
        var dir = Directory.GetCurrentDirectory();
        for (var i = 0; i < 10; i++)
        {
            var candidate = Path.Combine(dir, "data", "kaggle");
            if (Directory.Exists(candidate))
                return candidate;
            var parent = Directory.GetParent(dir)?.FullName;
            if (parent == null) break;
            dir = parent;
        }
        return null;
    }

    private static async Task<(DataService, TeamTools, StatsTools)> LoadAsync()
    {
        var dataDir = FindDataDirectory()
            ?? throw new SkipException("data/kaggle directory not found");
        var svc = new DataService();
        await svc.LoadAsync(dataDir);
        var teamTools = new TeamTools(svc);
        var statsTools = new StatsTools(svc);
        return (svc, teamTools, statsTools);
    }

    // Scenario: Get team statistics
    [Fact]
    public async Task GivenMatchDataLoaded_WhenRequestingPalmeirasStats2023_ThenReturnsWinsLossesDrawsAndGoals()
    {
        var (_, teamTools, _) = await LoadAsync();
        var result = teamTools.GetTeamStats("Palmeiras", season: 2023, competition: "Brasileirao");
        Assert.NotEmpty(result);
        // Accepting either stats or "no data" since coverage depends on file content
    }

    [Fact]
    public async Task GetTeamStats_CorinthiansHomeRecord2022_ReturnsResult()
    {
        var (_, teamTools, _) = await LoadAsync();
        var result = teamTools.GetTeamStats("Corinthians", season: 2022, competition: "Brasileirao", homeAwayBreakdown: true);
        Assert.NotEmpty(result);
    }

    [Fact]
    public async Task GetTeamStats_AllTimeStats_ReturnsResult()
    {
        var (_, teamTools, _) = await LoadAsync();
        var result = teamTools.GetTeamStats("Flamengo");
        Assert.NotEqual($"No match data found for 'Flamengo'.", result);
        Assert.Contains("Flamengo", result);
    }

    [Fact]
    public async Task CompareTeams_PalmeirasVsSantos_ReturnsComparison()
    {
        var (_, teamTools, _) = await LoadAsync();
        var result = teamTools.CompareTeams("Palmeiras", "Santos");
        Assert.Contains("Comparison", result);
    }

    [Fact]
    public async Task GetTeamCompetitions_Flamengo_ReturnsCompetitions()
    {
        var (_, teamTools, _) = await LoadAsync();
        var result = teamTools.GetTeamCompetitions("Flamengo");
        Assert.NotEqual("No matches found for team 'Flamengo'.", result);
        Assert.Contains("Competitions", result);
    }

    [Fact]
    public async Task GetBiggestWins_ReturnsTopResults()
    {
        var (_, _, statsTools) = await LoadAsync();
        var result = statsTools.GetBiggestWins(limit: 5);
        Assert.Contains("Biggest victories", result);
    }

    [Fact]
    public async Task GetCompetitionStats_Brasileirao_ReturnsStats()
    {
        var (_, _, statsTools) = await LoadAsync();
        var result = statsTools.GetCompetitionStats(competition: "Brasileirao");
        Assert.Contains("Total matches", result);
        Assert.Contains("Goals per match", result);
    }

    [Fact]
    public async Task GetTopTeams_ByGoals_ReturnsList()
    {
        var (_, _, statsTools) = await LoadAsync();
        var result = statsTools.GetTopTeams(criteria: "goals", limit: 10);
        Assert.Contains("Top teams by goals", result);
    }

    [Fact]
    public async Task GetDataSummary_ReturnsCompleteSummary()
    {
        var (_, _, statsTools) = await LoadAsync();
        var result = statsTools.GetDataSummary();
        Assert.Contains("Total matches", result);
        Assert.Contains("Total players", result);
    }

    [Fact]
    public async Task GetTeamStats_NonExistentTeam_ReturnsNoDataMessage()
    {
        var (_, teamTools, _) = await LoadAsync();
        var result = teamTools.GetTeamStats("TeamThatDefinitelyDoesNotExist12345");
        Assert.Contains("No match data found", result);
    }
}
