using BrazilianSoccerMcp.Services;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

public class DataServiceTests
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

    private static async Task<DataService> LoadDataServiceAsync()
    {
        var dataDir = FindDataDirectory()
            ?? throw new SkipException("data/kaggle directory not found; skipping integration tests");
        var svc = new DataService();
        await svc.LoadAsync(dataDir);
        return svc;
    }

    [Fact]
    public async Task LoadAsync_LoadsAllMatchFiles()
    {
        var svc = await LoadDataServiceAsync();
        Assert.True(svc.Matches.Count > 1000, $"Expected >1000 matches, got {svc.Matches.Count}");
    }

    [Fact]
    public async Task LoadAsync_LoadsPlayerData()
    {
        var svc = await LoadDataServiceAsync();
        Assert.True(svc.Players.Count > 100, $"Expected >100 players, got {svc.Players.Count}");
    }

    [Fact]
    public async Task LoadAsync_BrasileiraoMatchesHaveCorrectCompetition()
    {
        var svc = await LoadDataServiceAsync();
        var brasileirao = svc.Matches.Where(m => m.Competition == "Brasileirão Serie A").ToList();
        Assert.NotEmpty(brasileirao);
    }

    [Fact]
    public async Task LoadAsync_CupMatchesHaveCorrectCompetition()
    {
        var svc = await LoadDataServiceAsync();
        var cup = svc.Matches.Where(m => m.Competition == "Copa do Brasil").ToList();
        Assert.NotEmpty(cup);
    }

    [Fact]
    public async Task LoadAsync_LibertadoresMatchesHaveCorrectCompetition()
    {
        var svc = await LoadDataServiceAsync();
        var lib = svc.Matches.Where(m => m.Competition == "Copa Libertadores").ToList();
        Assert.NotEmpty(lib);
    }

    [Fact]
    public async Task LoadAsync_MatchesHaveDates()
    {
        var svc = await LoadDataServiceAsync();
        var withDates = svc.Matches.Count(m => m.Date.HasValue);
        Assert.True(withDates > svc.Matches.Count * 0.5, "More than half the matches should have dates");
    }

    [Fact]
    public async Task LoadAsync_PlayersHaveNames()
    {
        var svc = await LoadDataServiceAsync();
        Assert.True(svc.Players.All(p => !string.IsNullOrEmpty(p.Name)));
    }

    [Fact]
    public async Task LoadAsync_PlayersHaveOverallRating()
    {
        var svc = await LoadDataServiceAsync();
        var withRating = svc.Players.Count(p => p.Overall.HasValue);
        Assert.True(withRating > 0);
    }

    [Fact]
    public async Task LoadAsync_IsIdempotent()
    {
        var svc = await LoadDataServiceAsync();
        var count = svc.Matches.Count;
        await svc.LoadAsync(FindDataDirectory()!);
        Assert.Equal(count, svc.Matches.Count);
    }
}

// Simple skip exception for missing test data
public class SkipException : Exception
{
    public SkipException(string message) : base(message) { }
}
