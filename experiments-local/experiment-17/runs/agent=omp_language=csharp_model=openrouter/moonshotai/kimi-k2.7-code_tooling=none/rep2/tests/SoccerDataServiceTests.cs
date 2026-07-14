using BrazilianSoccerMcpServer.Services;
using FluentAssertions;
using Xunit;

namespace BrazilianSoccerMcpServer.Tests;

public class SoccerDataServiceTests
{
    private readonly SoccerDataService _service = new();

    [Fact]
    public void GivenMatchDataLoaded_WhenQueried_ThenAllSixSourcesArePresent()
    {
        _service.Matches.Should().NotBeEmpty();
        _service.Players.Should().NotBeEmpty();

        var competitions = _service.ListCompetitions();
        competitions.Should().Contain("Brasileirão");
        competitions.Should().Contain("Copa do Brasil");
        competitions.Should().Contain("Copa Libertadores");
    }

    [Fact]
    public void GivenFlamengoAndFluminense_WhenSearchMatches_ThenResultsContainBothTeams()
    {
        var matches = _service.FindMatches(team: "Flamengo", opponent: "Fluminense", limit: 100).ToList();

        matches.Should().NotBeEmpty();
        matches.Should().OnlyContain(m =>
            TeamNameMatcher.IsMatch(m.HomeTeamBase, "Flamengo") || TeamNameMatcher.IsMatch(m.AwayTeamBase, "Flamengo"));
        matches.Should().OnlyContain(m =>
            TeamNameMatcher.IsMatch(m.HomeTeamBase, "Fluminense") || TeamNameMatcher.IsMatch(m.AwayTeamBase, "Fluminense"));
    }

    [Fact]
    public void GivenPalmeirasIn2023_WhenGetTeamStats_ThenStatsAreReturned()
    {
        var stats = _service.GetTeamStats("Palmeiras", season: 2023, competition: "Brasileirão");

        stats.Matches.Should().BeGreaterThan(0);
        stats.Matches.Should().Be(stats.Wins + stats.Draws + stats.Losses);
    }

    [Fact]
    public void Given2019Brasileirao_WhenGetStandings_ThenFlamengoIsChampion()
    {
        var standings = _service.GetStandings("Brasileirão", season: 2019).ToList();

        standings.Should().NotBeEmpty();
        standings.First().Team.Should().Be("Flamengo");
    }

    [Fact]
    public void GivenFlamengoAndCorinthians_WhenGetHeadToHead_ThenRecordIsReturned()
    {
        var h2h = _service.GetHeadToHead("Flamengo", "Corinthians");

        h2h.Matches.Should().BeGreaterThan(0);
        h2h.Matches.Should().Be(h2h.WinsA + h2h.Draws + h2h.WinsB);
    }

    [Fact]
    public void GivenCopaDoBrasil_WhenGetBiggestWins_ThenMatchesHaveLargeGoalDifferences()
    {
        var wins = _service.GetBiggestWins("Copa do Brasil", limit: 5).ToList();

        wins.Should().NotBeEmpty();
        wins.First().GoalDifference.Should().BeGreaterOrEqualTo(wins.Last().GoalDifference ?? 0);
    }

    [Fact]
    public void GivenBrazilianNationality_WhenSearchPlayers_ThenNeymarIsIncluded()
    {
        var players = _service.SearchPlayers(nationality: "Brazil", minOverall: 90, limit: 10).ToList();

        players.Should().NotBeEmpty();
        players.Should().Contain(p => p.Name.Contains("Neymar", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void GivenFlamengoClub_WhenSearchPlayers_ThenAtLeastOnePlayerIsReturned()
    {
        var players = _service.SearchPlayers(club: "Flamengo", limit: 10).ToList();
        players.Should().NotBeEmpty();
    }

    [Fact]
    public void GivenPlayerName_WhenGetPlayerByName_ThenPlayerIsReturned()
    {
        var player = _service.GetPlayerByName("Gabriel Barbosa");
        player.Should().NotBeNull();
    }

    [Fact]
    public void GivenLoadedData_WhenAverageGoalsCalculated_ThenResultIsPositive()
    {
        var avg = _service.GetAverageGoals("Brasileirão");
        avg.Should().BeGreaterThan(0);
    }
}
