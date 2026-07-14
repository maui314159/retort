using Xunit;
using BrazilianSoccerMcp.Services;
using System;
using System.IO;

namespace BrazilianSoccerMcp.Tests;

public class SoccerDataServiceTests
{
    private readonly SoccerDataService _service;

    public SoccerDataServiceTests()
    {
        // Adjust path for test environment
        var dataDirectory = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", "data", "kaggle");
        if (!Directory.Exists(dataDirectory))
        {
            dataDirectory = "data/kaggle";
        }
        _service = new SoccerDataService(dataDirectory);
    }

    [Fact]
    public void DataLoadShouldSucceed()
    {
        Assert.True(_service.Matches.Count > 0, "Should have loaded matches");
        Assert.True(_service.Players.Count > 0, "Should have loaded players");
    }

    [Fact]
    public void GetTeamStatisticsShouldReturnCorrectData()
    {
        var stats = _service.GetTeamStatistics("Flamengo", "2019");
        
        Assert.NotNull(stats);
        Assert.Equal("Flamengo", stats["Team"]);
        Assert.True((int)stats["TotalMatches"] > 0);
        Assert.True((int)stats["Wins"] > 0);
    }

    [Fact]
    public void SearchPlayersShouldReturnBrazilianPlayers()
    {
        var players = _service.SearchPlayers(nationality: "Brazil", limit: 10);
        
        Assert.NotEmpty(players);
        foreach (var player in players)
        {
            Assert.Contains("Brazil", player.Nationality, StringComparison.OrdinalIgnoreCase);
        }
    }

    [Fact]
    public void GetHeadToHeadShouldReturnMatchesBetweenTeams()
    {
        var results = _service.GetHeadToHead("Flamengo", "Fluminense");
        
        Assert.True(results.Count > 1); // At least summary + 1 match
        Assert.Contains("wins", results[0]["Summary"].ToString()!);
    }

    [Fact]
    public void GetCompetitionStandingsShouldReturnSortedTable()
    {
        var standings = _service.GetCompetitionStandings("Brasileirão Serie A", "2019");
        
        Assert.NotEmpty(standings);
        Assert.Equal(1, standings[0]["Pos"]);
        
        // Verify sorting by points descending
        for (int i = 1; i < standings.Count; i++)
        {
            Assert.True((int)standings[i - 1]["Pts"] >= (int)standings[i]["Pts"]);
        }
    }

    [Fact]
    public void GetStatisticalAnalysisShouldReturnValidMetrics()
    {
        var stats = _service.GetStatisticalAnalysis(competition: "Brasileirão Serie A", season: "2019");
        
        Assert.False(stats.ContainsKey("Error"));
        Assert.True((int)stats["TotalMatches"] > 0);
        Assert.True((double)stats["AverageGoalsPerMatch"] > 0);
        Assert.Contains("%", stats["HomeWinRate"].ToString()!);
    }
}
