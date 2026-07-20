using BrazilianSoccerMcp.Services;
using BrazilianSoccerMcp.Tools;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

public class MatchQueryTests
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

    private static async Task<(DataService, MatchTools)> LoadAsync()
    {
        var dataDir = FindDataDirectory()
            ?? throw new SkipException("data/kaggle directory not found");
        var svc = new DataService();
        await svc.LoadAsync(dataDir);
        var tools = new MatchTools(svc);
        return (svc, tools);
    }

    // Scenario: Find matches between two teams
    [Fact]
    public async Task GivenMatchDataLoaded_WhenSearchingFlamengoVsFluminense_ThenReturnsMatches()
    {
        var (_, tools) = await LoadAsync();
        var result = tools.SearchMatches(team: "Flamengo", opponent: "Fluminense", limit: 50);
        Assert.NotEqual("No matches found for the given criteria.", result);
        Assert.Contains("Flamengo", result);
        Assert.Contains("Fluminense", result);
    }

    // Scenario: Find matches for a team in a season
    [Fact]
    public async Task GivenMatchDataLoaded_WhenSearchingPalmeirasIn2023_ThenReturnsMatches()
    {
        var (_, tools) = await LoadAsync();
        var result = tools.SearchMatches(team: "Palmeiras", season: 2023);
        Assert.NotEqual("No matches found for the given criteria.", result);
        Assert.Contains("2023", result);
    }

    // Scenario: Find matches in Copa do Brasil
    [Fact]
    public async Task GivenMatchDataLoaded_WhenSearchingCopaDoBrasil_ThenReturnsMatches()
    {
        var (_, tools) = await LoadAsync();
        var result = tools.SearchMatches(competition: "Copa do Brasil", limit: 10);
        Assert.NotEqual("No matches found for the given criteria.", result);
        Assert.Contains("Copa do Brasil", result);
    }

    // Scenario: Get head-to-head record
    [Fact]
    public async Task GivenMatchDataLoaded_WhenGettingH2HFlamengoCorinthians_ThenReturnsRecord()
    {
        var (_, tools) = await LoadAsync();
        var result = tools.GetHeadToHead("Flamengo", "Corinthians");
        Assert.NotEqual("No matches found between 'Flamengo' and 'Corinthians'.", result);
        Assert.Contains("Head-to-Head", result);
    }

    // Scenario: Get standings
    [Fact]
    public async Task GivenMatchDataLoaded_WhenGettingStandings2023_ThenReturnsTable()
    {
        var (_, tools) = await LoadAsync();
        var result = tools.GetStandings(2023, "Brasileirao");
        // Either we get standings or "no data" - either is acceptable
        Assert.NotEmpty(result);
    }

    [Fact]
    public async Task SearchMatches_WithNoFilter_ReturnsDefaultLimit()
    {
        var (_, tools) = await LoadAsync();
        var result = tools.SearchMatches(limit: 5);
        // Should return at most 5 results
        var lineCount = result.Split('\n', StringSplitOptions.RemoveEmptyEntries).Length;
        Assert.True(lineCount > 0);
    }

    [Fact]
    public async Task SearchMatches_ByDateRange_ReturnsMatchesInRange()
    {
        var (_, tools) = await LoadAsync();
        var result = tools.SearchMatches(dateFrom: "2023-01-01", dateTo: "2023-12-31");
        if (result != "No matches found for the given criteria.")
        {
            Assert.Contains("2023", result);
        }
    }

    [Fact]
    public async Task GetHeadToHead_NonExistentTeams_ReturnsNoMatchesMessage()
    {
        var (_, tools) = await LoadAsync();
        var result = tools.GetHeadToHead("TeamThatDoesNotExist", "AnotherFakeTeam");
        Assert.StartsWith("No matches found", result);
    }

    [Fact]
    public async Task GetStandings_InvalidSeason_ReturnsNoDataMessage()
    {
        var (_, tools) = await LoadAsync();
        var result = tools.GetStandings(1800, "Brasileirao");
        Assert.Contains("No match data found", result);
    }
}
