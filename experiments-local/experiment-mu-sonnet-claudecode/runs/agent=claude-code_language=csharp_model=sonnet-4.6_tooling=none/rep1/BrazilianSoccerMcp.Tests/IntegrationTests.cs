using BrazilianSoccerMcp.Services;
using BrazilianSoccerMcp.Tools;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Integration tests that load from the real CSV data files.
/// Requires the data/kaggle directory to be accessible from the test working directory.
/// </summary>
public class IntegrationTests
{
    private static SoccerDataService? _service;
    private static readonly object _lock = new();

    private static SoccerDataService GetService()
    {
        if (_service != null) return _service;
        lock (_lock)
        {
            if (_service != null) return _service;
            var dataPath = DataPathFinder.FindKaggleDataPath();
            _service = SoccerDataService.LoadFromDisk(dataPath);
            return _service;
        }
    }

    [Fact]
    public void DataLoads_Matches_NotEmpty()
    {
        var service = GetService();
        var matches = service.FindMatches(limit: 10);
        Assert.NotEmpty(matches);
    }

    [Fact]
    public void DataLoads_Players_NotEmpty()
    {
        var service = GetService();
        var players = service.FindPlayers(nationality: "Brazil", limit: 5);
        Assert.NotEmpty(players);
    }

    [Fact]
    public void FindMatches_Flamengo_ReturnsResults()
    {
        var service = GetService();
        var matches = service.FindMatches("Flamengo", limit: 10);
        Assert.NotEmpty(matches);
        Assert.All(matches, m =>
            Assert.True(
                Services.TeamNameNormalizer.Matches(m.HomeTeam, "Flamengo") ||
                Services.TeamNameNormalizer.Matches(m.AwayTeam, "Flamengo")));
    }

    [Fact]
    public void FindMatches_FlamengoVsFluminense_ReturnsHeadToHead()
    {
        var service = GetService();
        var matches = service.FindMatches("Flamengo", "Fluminense", limit: 50);
        Assert.NotEmpty(matches);
    }

    [Fact]
    public void GetTeamStats_Palmeiras_HasValidStats()
    {
        var service = GetService();
        var stats = service.GetTeamStats("Palmeiras");
        Assert.True(stats.Played > 0);
        Assert.Equal(stats.Wins + stats.Draws + stats.Losses, stats.Played);
        Assert.True(stats.GoalsFor >= 0);
        Assert.True(stats.GoalsAgainst >= 0);
    }

    [Fact]
    public void GetBrasileiraStandings_2019_HasFlamengo()
    {
        var service = GetService();
        var standings = service.GetBrasileiraStandings(2019);
        Assert.NotEmpty(standings);
        Assert.Contains(standings, s => s.Team.Contains("Flamengo", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void FindPlayers_Brazilian_ReturnsResults()
    {
        var service = GetService();
        var players = service.FindPlayers(nationality: "Brazil", limit: 10);
        Assert.NotEmpty(players);
        Assert.All(players, p => Assert.Equal("Brazil", p.Nationality));
    }

    [Fact]
    public void GetBiggestWins_ReturnsOrdered()
    {
        var service = GetService();
        var wins = service.GetBiggestWins(limit: 5);
        Assert.NotEmpty(wins);
        for (int i = 0; i < wins.Count - 1; i++)
        {
            var d1 = Math.Abs(wins[i].HomeGoal - wins[i].AwayGoal);
            var d2 = Math.Abs(wins[i + 1].HomeGoal - wins[i + 1].AwayGoal);
            Assert.True(d1 >= d2);
        }
    }

    [Fact]
    public void GetGlobalStats_AllCompetitions_IsValid()
    {
        var service = GetService();
        var stats = service.GetGlobalStats();
        Assert.True(stats.TotalMatches > 1000);
        Assert.True(stats.AvgGoalsPerMatch > 1.0);
        Assert.Equal(stats.TotalMatches, stats.HomeWins + stats.Draws + stats.AwayWins);
    }

    [Fact]
    public void MatchTool_FindMatches_Flamengo_ReturnsFormattedString()
    {
        var service = GetService();
        var tool = new MatchTools(service);
        var result = tool.FindMatches(team: "Flamengo", limit: 5);
        Assert.Contains("Flamengo", result);
        Assert.DoesNotContain("No matches found", result);
    }

    [Fact]
    public void TeamTool_GetStats_Corinthians_ReturnsFormattedString()
    {
        var service = GetService();
        var tool = new TeamTools(service);
        var result = tool.GetTeamStats("Corinthians", season: 2022);
        Assert.Contains("Corinthians", result);
    }

    [Fact]
    public void PlayerTool_FindBrazilians_ReturnsFormattedString()
    {
        var service = GetService();
        var tool = new PlayerTools(service);
        var result = tool.FindPlayers(nationality: "Brazil", limit: 5);
        Assert.Contains("Brazil", result);
        Assert.DoesNotContain("No players found", result);
    }

    [Fact]
    public void CompetitionTool_GetStandings_2019_ReturnsTable()
    {
        var service = GetService();
        var tool = new CompetitionTools(service);
        var result = tool.GetStandings(2019);
        Assert.Contains("2019", result);
        Assert.Contains("Pts", result);
    }

    [Fact]
    public void StatsTool_GetBiggestWins_ReturnsResults()
    {
        var service = GetService();
        var tool = new StatisticsTools(service);
        var result = tool.GetBiggestWins();
        Assert.Contains("wins", result.ToLowerInvariant());
        Assert.DoesNotContain("No matches found", result);
    }

    [Fact]
    public void FindMatches_BySeason2023_ReturnsOnlySeason2023()
    {
        var service = GetService();
        var matches = service.FindMatches(season: 2023, limit: 50);
        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.Equal(2023, m.Season));
    }

    [Fact]
    public void FindMatches_Brasileirao_ReturnsOnlyBrasileirao()
    {
        var service = GetService();
        var matches = service.FindMatches(competition: "brasileirao", limit: 10);
        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.Contains("Brasileirao", m.Competition, StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void FindMatches_Libertadores_ReturnsLibertadoresMatches()
    {
        var service = GetService();
        var matches = service.FindMatches(competition: "libertadores", limit: 10);
        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.Contains("Libertadores", m.Competition, StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void FindPlayers_ByClub_RealMadrid_ReturnsPlayers()
    {
        var service = GetService();
        // FIFA dataset has European clubs; use Real Madrid as a known-present club
        var players = service.FindPlayers(club: "Real Madrid");
        Assert.NotEmpty(players);
    }

    [Fact]
    public void AllSixCsvFilesLoad_MatchCountIsSubstantial()
    {
        var service = GetService();
        // Total matches across all 6 files should be in the tens of thousands range
        var stats = service.GetGlobalStats();
        Assert.True(stats.TotalMatches > 5000,
            $"Expected >5000 matches but got {stats.TotalMatches}. Some CSV files may not have loaded.");
    }
}
