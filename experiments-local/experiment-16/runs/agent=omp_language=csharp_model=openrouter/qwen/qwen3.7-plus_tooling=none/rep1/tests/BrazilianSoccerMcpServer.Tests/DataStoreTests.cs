using BrazilianSoccerMcpServer.Services;
using BrazilianSoccerMcpServer.Tools;
using Xunit;

namespace BrazilianSoccerMcpServer.Tests;

public class DataStoreTests
{
    private readonly BrazilianSoccerDataStore _dataStore;

    public DataStoreTests()
    {
        _dataStore = new BrazilianSoccerDataStore();
        
        // Find the data directory relative to the test project
        var currentDir = Directory.GetCurrentDirectory();
        var dataDir = Path.Combine(currentDir, "..", "..", "..", "..", "..", "data", "kaggle");
        
        if (!Directory.Exists(dataDir))
        {
            // Try looking from project root
            dataDir = Path.GetFullPath(Path.Combine(currentDir, "data", "kaggle"));
        }
        
        if (Directory.Exists(dataDir))
        {
            _dataStore.LoadFromDirectory(dataDir);
        }
    }

    [Fact]
    public void LoadFromDirectory_ShouldLoadMatches()
    {
        // At least the main datasets should have matches
        Assert.True(_dataStore.Matches.Count > 1000, $"Expected > 1000 matches, got {_dataStore.Matches.Count}");
    }

    [Fact]
    public void LoadFromDirectory_ShouldLoadPlayers()
    {
        Assert.True(_dataStore.Players.Count > 1000, $"Expected > 1000 players, got {_dataStore.Players.Count}");
    }

    [Fact]
    public void TeamNameNormalizer_ShouldNormalizeStateSuffixes()
    {
        Assert.Equal("Palmeiras", TeamNameNormalizer.Normalize("Palmeiras-SP"));
        Assert.Equal("Flamengo", TeamNameNormalizer.Normalize("Flamengo-RJ"));
    }

    [Fact]
    public void TeamNameNormalizer_ShouldNormalizeFullNames()
    {
        Assert.Equal("Corinthians", TeamNameNormalizer.Normalize("Sport Club Corinthians Paulista"));
        Assert.Equal("Athletico-PR", TeamNameNormalizer.Normalize("Athletico Paranaense"));
    }

    [Fact]
    public void TeamNameNormalizer_ShouldMatchVariations()
    {
        Assert.True(TeamNameNormalizer.Matches("Palmeiras-SP", "Palmeiras"));
        Assert.True(TeamNameNormalizer.Matches("Flamengo", "Flamengo-RJ"));
        Assert.True(TeamNameNormalizer.Matches("São Paulo", "Sao Paulo"));
    }
}

public class SoccerToolsTests
{
    private readonly BrazilianSoccerDataStore _dataStore;
    private readonly SoccerTools _tools;

    public SoccerToolsTests()
    {
        _dataStore = new BrazilianSoccerDataStore();
        var currentDir = Directory.GetCurrentDirectory();
        var dataDir = Path.Combine(currentDir, "..", "..", "..", "..", "..", "data", "kaggle");
        if (!Directory.Exists(dataDir))
        {
            dataDir = Path.GetFullPath(Path.Combine(currentDir, "data", "kaggle"));
        }
        
        if (Directory.Exists(dataDir))
        {
            _dataStore.LoadFromDirectory(dataDir);
        }
        _tools = new SoccerTools(_dataStore);
    }

    [Fact]
    public void SearchMatches_ShouldFindMatchesByTeam()
    {
        var result = _tools.SearchMatches(eitherTeam: "Flamengo", limit: 10);
        Assert.Contains("Flamengo", result);
    }

    [Fact]
    public void GetTeamStats_ShouldReturnStatistics()
    {
        var result = _tools.GetTeamStats("Palmeiras", season: 2023);
        Assert.Contains("Matches:", result);
        Assert.Contains("Wins:", result);
    }

    [Fact]
    public void GetHeadToHead_ShouldReturnRecord()
    {
        var result = _tools.GetHeadToHead("Flamengo", "Fluminense");
        Assert.Contains("Head-to-Head", result);
        Assert.Contains("Wins:", result);
    }

    [Fact]
    public void SearchPlayers_ShouldFindPlayersByNationality()
    {
        var result = _tools.SearchPlayers(nationality: "Brazil", minOverall: 85, limit: 10);
        Assert.Contains("Brazil", result);
    }

    [Fact]
    public void GetCompetitionStandings_ShouldCalculateStandings()
    {
        var result = _tools.GetCompetitionStandings("Brasileirao", 2022);
        Assert.Contains("Standings", result);
        Assert.Contains("pts", result);
    }
    [Fact]
    public void GetStatisticalAnalysis_ShouldReturnStats()
    {
        var result = _tools.GetStatisticalAnalysis(competition: "Brasileirao");
        Assert.Contains("Average goals per match", result);
        Assert.Contains("Home win rate", result);
    }
}
