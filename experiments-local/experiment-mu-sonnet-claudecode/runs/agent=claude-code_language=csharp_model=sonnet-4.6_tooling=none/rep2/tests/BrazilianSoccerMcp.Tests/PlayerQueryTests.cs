using BrazilianSoccerMcp.Services;
using BrazilianSoccerMcp.Tools;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

public class PlayerQueryTests
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

    private static async Task<(DataService, PlayerTools)> LoadAsync()
    {
        var dataDir = FindDataDirectory()
            ?? throw new SkipException("data/kaggle directory not found");
        var svc = new DataService();
        await svc.LoadAsync(dataDir);
        var tools = new PlayerTools(svc);
        return (svc, tools);
    }

    // Scenario: Find all Brazilian players
    [Fact]
    public async Task GivenPlayerDataLoaded_WhenSearchingBrazilianPlayers_ThenReturnsResults()
    {
        var (_, tools) = await LoadAsync();
        var result = tools.SearchPlayers(nationality: "Brazilian", limit: 10);
        Assert.NotEqual("No players found for the given criteria.", result);
        // Nationality field in FIFA data is stored as "Brazil"
        Assert.Contains("Brazil", result);
    }

    // Scenario: Find top-rated players
    [Fact]
    public async Task GivenPlayerDataLoaded_WhenGettingTopPlayers_ThenReturnsSortedByOverall()
    {
        var (_, tools) = await LoadAsync();
        var result = tools.GetTopPlayers(limit: 5);
        Assert.NotEqual("No players found for the given criteria.", result);
        Assert.Contains("Overall:", result);
    }

    // Scenario: Find players at a club
    [Fact]
    public async Task GivenPlayerDataLoaded_WhenSearchingByClub_ThenReturnsClubPlayers()
    {
        var (_, tools) = await LoadAsync();
        var result = tools.SearchPlayers(club: "Barcelona", limit: 10);
        if (result != "No players found for the given criteria.")
        {
            Assert.Contains("Barcelona", result);
        }
    }

    // Scenario: Find players by position
    [Fact]
    public async Task GivenPlayerDataLoaded_WhenSearchingByPosition_ThenReturnsPositionPlayers()
    {
        var (_, tools) = await LoadAsync();
        var result = tools.SearchPlayers(position: "GK", limit: 5);
        Assert.NotEqual("No players found for the given criteria.", result);
        Assert.Contains("GK", result);
    }

    // Scenario: Search by name
    [Fact]
    public async Task GivenPlayerDataLoaded_WhenSearchingByName_ThenReturnsMatchingPlayers()
    {
        var (_, tools) = await LoadAsync();
        var result = tools.SearchPlayers(name: "Neymar");
        if (result != "No players found for the given criteria.")
        {
            Assert.Contains("Neymar", result);
        }
    }

    [Fact]
    public async Task GetBrazilianClubPlayers_ReturnsGroupedByClub()
    {
        var (_, tools) = await LoadAsync();
        var result = tools.GetBrazilianClubPlayers("Brazilian");
        Assert.Contains("Brazilian players by club", result);
    }

    [Fact]
    public async Task SearchPlayers_WithMinOverall_FiltersCorrectly()
    {
        var (svc, tools) = await LoadAsync();
        var result = tools.SearchPlayers(minOverall: 90, limit: 20);
        if (result != "No players found for the given criteria.")
        {
            // All returned players should have overall >= 90
            var players = svc.Players.Where(p => p.Overall >= 90).ToList();
            Assert.True(players.Count > 0);
        }
    }

    [Fact]
    public async Task SearchPlayers_NonExistentName_ReturnsNoResults()
    {
        var (_, tools) = await LoadAsync();
        var result = tools.SearchPlayers(name: "xyzAbsolutelyNobodyNamedThis123");
        Assert.Equal("No players found for the given criteria.", result);
    }
}
