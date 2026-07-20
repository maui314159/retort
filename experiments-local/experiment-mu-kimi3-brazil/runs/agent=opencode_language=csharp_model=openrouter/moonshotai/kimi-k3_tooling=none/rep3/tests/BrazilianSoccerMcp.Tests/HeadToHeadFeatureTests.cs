using BrazilianSoccerMcp.Services;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Feature: Head-to-head comparison between two teams.
/// </summary>
public class HeadToHeadFeatureTests
{
    private readonly TeamAnalyticsService _analytics =
        new(TestData.Graph, new MatchQueryService(TestData.Graph));

    [Fact]
    public void Given_MatchDataLoaded_When_ComparingPalmeirasAndSantos_Then_TallyIsConsistentWithMatchList()
    {
        // Given / When
        var h2h = _analytics.GetHeadToHead("Palmeiras", "Santos");

        // Then: wins + draws equal the number of played matches listed
        Assert.NotEmpty(h2h.Matches);
        var played = h2h.Matches.Count(m => m.Played);
        Assert.Equal(played, h2h.Team1Wins + h2h.Team2Wins + h2h.Draws);
        // And every listed match really is between the two clubs
        Assert.All(h2h.Matches, m =>
        {
            Assert.True(m.Involves("palmeiras"));
            Assert.True(m.Involves("santos"));
        });
    }

    [Fact]
    public void Given_MatchDataLoaded_When_ReversingTeams_Then_WinCountsSwap()
    {
        // Given / When
        var ab = _analytics.GetHeadToHead("Flamengo", "Fluminense");
        var ba = _analytics.GetHeadToHead("Fluminense", "Flamengo");

        // Then
        Assert.Equal(ab.Team1Wins, ba.Team2Wins);
        Assert.Equal(ab.Team2Wins, ba.Team1Wins);
        Assert.Equal(ab.Draws, ba.Draws);
    }

    [Fact]
    public void Given_MatchDataLoaded_When_CompetitionFilterApplied_Then_OnlyThatCompetitionIsCounted()
    {
        // Given / When
        var cupOnly = _analytics.GetHeadToHead("Flamengo", "Fluminense", competition: "Copa do Brasil");

        // Then
        Assert.NotEmpty(cupOnly.Matches);
        Assert.All(cupOnly.Matches, m => Assert.Equal("Copa do Brasil", m.Competition));
    }
}
