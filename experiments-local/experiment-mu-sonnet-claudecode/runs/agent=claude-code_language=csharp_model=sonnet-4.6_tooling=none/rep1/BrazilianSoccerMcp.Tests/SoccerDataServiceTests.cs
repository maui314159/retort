using BrazilianSoccerMcp.Models;
using BrazilianSoccerMcp.Services;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

public class SoccerDataServiceTests
{
    private static SoccerDataService CreateServiceWithTestData()
    {
        var matches = new List<UnifiedMatch>
        {
            new(new DateTime(2023, 9, 3), "Flamengo-RJ", "Fluminense-RJ", 2, 1, 2023, "Brasileirao Serie A", "22"),
            new(new DateTime(2023, 5, 28), "Fluminense-RJ", "Flamengo-RJ", 1, 0, 2023, "Brasileirao Serie A", "8"),
            new(new DateTime(2022, 10, 15), "Palmeiras-SP", "Corinthians-SP", 3, 0, 2022, "Brasileirao Serie A", "30"),
            new(new DateTime(2022, 8, 20), "Corinthians-SP", "Palmeiras-SP", 1, 1, 2022, "Brasileirao Serie A", "24"),
            new(new DateTime(2023, 8, 17), "Flamengo-RJ", "Gremio-RS", 1, 0, 2023, "Copa do Brasil", null, "semi-final"),
            new(new DateTime(2019, 11, 23), "Flamengo-RJ", "River Plate", 2, 1, 2019, "Copa Libertadores", null, "final"),
        };

        var players = new List<FifaPlayer>
        {
            new(1, "Gabriel Barbosa", 22, "Brazilian", 85, 90, "Flamengo", "ST", 9),
            new(2, "Filipe Luis", 33, "Brazilian", 83, 83, "Flamengo", "LB", 16),
            new(3, "Dudu", 26, "Brazilian", 80, 82, "Palmeiras", "LW", 7),
            new(4, "Neymar Jr", 27, "Brazilian", 92, 92, "Paris Saint-Germain", "LW", 10),
            new(5, "Alisson", 26, "Brazilian", 89, 90, "Liverpool", "GK", 1),
        };

        return new SoccerDataService(matches, players);
    }

    [Fact]
    public void FindMatches_ByTeam_ReturnsCorrectMatches()
    {
        var service = CreateServiceWithTestData();
        var results = service.FindMatches("Flamengo");
        Assert.Equal(4, results.Count);
    }

    [Fact]
    public void FindMatches_HeadToHead_ReturnsBothOrders()
    {
        var service = CreateServiceWithTestData();
        var results = service.FindMatches("Flamengo", "Fluminense");
        Assert.Equal(2, results.Count);
    }

    [Fact]
    public void FindMatches_BySeason_FiltersCorrectly()
    {
        var service = CreateServiceWithTestData();
        var results = service.FindMatches(season: 2023);
        Assert.Equal(3, results.Count);
        Assert.All(results, m => Assert.Equal(2023, m.Season));
    }

    [Fact]
    public void FindMatches_ByCompetition_FiltersCorrectly()
    {
        var service = CreateServiceWithTestData();
        var results = service.FindMatches(competition: "copa do brasil");
        Assert.Single(results);
    }

    [Fact]
    public void GetTeamStats_ReturnsCorrectStats()
    {
        var service = CreateServiceWithTestData();
        var stats = service.GetTeamStats("Flamengo");

        Assert.Equal("Flamengo", stats.TeamName);
        Assert.Equal(4, stats.Played);
        Assert.Equal(3, stats.Wins);
        Assert.Equal(0, stats.Draws);
        Assert.Equal(1, stats.Losses);
        Assert.Equal(5, stats.GoalsFor);
        Assert.Equal(3, stats.GoalsAgainst);
    }

    [Fact]
    public void GetHeadToHead_ReturnsCorrectRecord()
    {
        var service = CreateServiceWithTestData();
        var h2h = service.GetHeadToHead("Flamengo", "Fluminense");

        Assert.Equal(2, h2h.TotalMatches);
        Assert.Equal(1, h2h.Team1Wins); // Flamengo won 2-1 at home
        Assert.Equal(0, h2h.Draws);
        Assert.Equal(1, h2h.Team2Wins); // Fluminense won 1-0 at home
    }

    [Fact]
    public void GetBrasileiraStandings_CalculatesPointsCorrectly()
    {
        var service = CreateServiceWithTestData();
        var standings = service.GetBrasileiraStandings(2022);

        Assert.NotEmpty(standings);
        var palmeiras = standings.FirstOrDefault(s => s.Team.Contains("Palmeiras", StringComparison.OrdinalIgnoreCase));
        Assert.NotNull(palmeiras);
        Assert.Equal(4, palmeiras!.Points); // 1 win (3pts) + 1 draw (1pt) = 4pts
    }

    [Fact]
    public void FindPlayers_ByNationality_ReturnsCorrectPlayers()
    {
        var service = CreateServiceWithTestData();
        var players = service.FindPlayers(nationality: "Brazilian");
        Assert.Equal(5, players.Count);
        Assert.All(players, p => Assert.Equal("Brazilian", p.Nationality));
    }

    [Fact]
    public void FindPlayers_ByClub_ReturnsCorrectPlayers()
    {
        var service = CreateServiceWithTestData();
        var players = service.FindPlayers(club: "Flamengo");
        Assert.Equal(2, players.Count);
        Assert.All(players, p => Assert.Contains("Flamengo", p.Club));
    }

    [Fact]
    public void FindPlayers_ByMinRating_FiltersCorrectly()
    {
        var service = CreateServiceWithTestData();
        var players = service.FindPlayers(minRating: 89);
        Assert.Equal(2, players.Count);
        Assert.All(players, p => Assert.True(p.Overall >= 89));
    }

    [Fact]
    public void FindPlayers_OrderedByRating()
    {
        var service = CreateServiceWithTestData();
        var players = service.FindPlayers(nationality: "Brazilian");
        for (int i = 0; i < players.Count - 1; i++)
            Assert.True(players[i].Overall >= players[i + 1].Overall);
    }

    [Fact]
    public void GetBiggestWins_ReturnsDescendingGoalDifference()
    {
        var service = CreateServiceWithTestData();
        var wins = service.GetBiggestWins(limit: 10);

        Assert.NotEmpty(wins);
        for (int i = 0; i < wins.Count - 1; i++)
        {
            var diff1 = Math.Abs(wins[i].HomeGoal - wins[i].AwayGoal);
            var diff2 = Math.Abs(wins[i + 1].HomeGoal - wins[i + 1].AwayGoal);
            Assert.True(diff1 >= diff2);
        }
    }

    [Fact]
    public void GetGlobalStats_CalculatesCorrectly()
    {
        var service = CreateServiceWithTestData();
        var stats = service.GetGlobalStats();

        Assert.Equal(6, stats.TotalMatches);
        Assert.True(stats.AvgGoalsPerMatch > 0);
        Assert.Equal(stats.HomeWins + stats.Draws + stats.AwayWins, stats.TotalMatches);
    }

    [Fact]
    public void FindMatches_RespectsLimit()
    {
        var service = CreateServiceWithTestData();
        var results = service.FindMatches(limit: 2);
        Assert.Equal(2, results.Count);
    }
}
