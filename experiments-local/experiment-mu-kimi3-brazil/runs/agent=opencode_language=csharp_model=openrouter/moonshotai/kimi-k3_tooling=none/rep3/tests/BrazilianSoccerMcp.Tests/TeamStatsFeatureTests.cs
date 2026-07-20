using BrazilianSoccerMcp.Services;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Feature: Team Queries
/// Win/loss/draw records with venue, season and competition filters.
/// </summary>
public class TeamStatsFeatureTests
{
    private readonly TeamAnalyticsService _analytics =
        new(TestData.Graph, new MatchQueryService(TestData.Graph));

    [Fact]
    public void Given_MatchDataLoaded_When_RequestingCorinthiansHomeRecord2022_Then_WinsLossesDrawsAndGoalsAreReturned()
    {
        // Given the match data is loaded

        // When I request statistics for "Corinthians" at home in season "2022"
        var rec = _analytics.GetTeamRecord("Corinthians", season: 2022, competition: "Brasileirão", venue: "home");

        // Then I should receive wins, losses, draws, and goals
        Assert.Equal(15, rec.Played);
        Assert.Equal(10, rec.Wins);
        Assert.Equal(4, rec.Draws);
        Assert.Equal(1, rec.Losses);
        Assert.Equal(21, rec.GoalsFor);
        Assert.Equal(7, rec.GoalsAgainst);
        Assert.True(rec.WinRate > 0.6);
        Assert.Equal(4, rec.Unplayed); // postponed 2022 fixtures carry NA scores
    }

    [Fact]
    public void Given_MatchDataLoaded_When_RequestingFullSeasonRecord_Then_GamesAddUpTo38()
    {
        // Given / When
        var rec = _analytics.GetTeamRecord("Flamengo", season: 2019, competition: "Serie A");

        // Then: a complete 38-game season
        Assert.Equal(38, rec.Played);
        Assert.Equal(28, rec.Wins);
        Assert.Equal(6, rec.Draws);
        Assert.Equal(4, rec.Losses);
        Assert.Equal(90, rec.Points);
    }

    [Fact]
    public void Given_MatchDataLoaded_When_RequestingAwayRecord_Then_OnlyAwayMatchesAreCounted()
    {
        // Given / When
        var home = _analytics.GetTeamRecord("Palmeiras", season: 2019, competition: "Serie A", venue: "home");
        var away = _analytics.GetTeamRecord("Palmeiras", season: 2019, competition: "Serie A", venue: "away");
        var all = _analytics.GetTeamRecord("Palmeiras", season: 2019, competition: "Serie A");

        // Then
        Assert.Equal(all.Played, home.Played + away.Played);
        Assert.Equal(all.GoalsFor, home.GoalsFor + away.GoalsFor);
    }

    [Fact]
    public void Given_MatchDataLoaded_When_TeamNameHasStateSuffix_Then_ItResolvesTheSame()
    {
        // Given / When
        var bySuffix = _analytics.GetTeamRecord("Flamengo-RJ", season: 2019, competition: "Serie A");
        var byPlain = _analytics.GetTeamRecord("Flamengo", season: 2019, competition: "Serie A");

        // Then
        Assert.Equal(byPlain.Played, bySuffix.Played);
        Assert.Equal(byPlain.Points, bySuffix.Points);
    }

    [Fact]
    public void Given_MatchDataLoaded_When_TeamUnknown_Then_AnInformativeErrorIsRaised()
    {
        // Given / When / Then
        var ex = Assert.Throws<KeyNotFoundException>(() => _analytics.GetTeamRecord("Wimbledon FC"));
        Assert.Contains("Wimbledon FC", ex.Message);
    }
}
