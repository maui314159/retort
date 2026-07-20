using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Services;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Feature: Match Queries
/// Scenarios from the specification: Fla-Flu derby, team season schedules,
/// cup finals, date-range and venue filtering.
/// </summary>
public class MatchQueryFeatureTests
{
    private readonly MatchQueryService _queries = new(TestData.Graph);

    [Fact]
    public void Given_MatchDataLoaded_When_SearchingFlamengoVsFluminense_Then_ListHasDateScoresAndCompetition()
    {
        // Given the match data is loaded (shared fixture)

        // When I search for matches between "Flamengo" and "Fluminense"
        var matches = _queries.Find(new MatchFilter { Team = "Flamengo", Opponent = "Fluminense", Limit = 100 },
            out _);

        // Then I should receive a list of matches
        Assert.NotEmpty(matches);
        // And each match should have date, scores, and competition
        Assert.All(matches, m =>
        {
            Assert.NotNull(m.Date);
            Assert.True(m.Played);
            Assert.False(string.IsNullOrWhiteSpace(m.Competition));
            Assert.True(m.Involves("flamengo"));
            Assert.True(m.Involves("fluminense"));
        });
        // And the derby should be well covered across the unified history
        Assert.True(matches.Count >= 20, $"expected at least 20 Fla-Flu matches, got {matches.Count}");
    }

    [Fact]
    public void Given_MatchDataLoaded_When_SearchingPalmeirasIn2023_Then_AllResultsAreFrom2023()
    {
        // Given / When
        var matches = _queries.Find(new MatchFilter { Team = "Palmeiras", Season = 2023, Limit = 100 }, out _);

        // Then
        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.Equal(2023, m.Season));
        Assert.Contains(matches, m => m.Competition == DataLoader.SerieA);
    }

    [Fact]
    public void Given_MatchDataLoaded_When_SearchingCopaDoBrasilFinals_Then_FinalsAreReturned()
    {
        // Given / When
        var matches = _queries.Find(
            new MatchFilter { Competition = "Copa do Brasil", Round = "final", Limit = 100 }, out _);

        // Then: cup finals from several seasons, at most 2 legs per season
        Assert.NotEmpty(matches);
        var seasons = matches.Where(m => m.Season is not null).Select(m => m.Season!.Value).Distinct().ToList();
        Assert.True(seasons.Count >= 8, $"expected finals from at least 8 seasons, got {seasons.Count}");
        Assert.All(matches, m => Assert.Equal(DataLoader.CopaDoBrasil, m.Competition));
    }

    [Fact]
    public void Given_MatchDataLoaded_When_FilteringByDateRange_Then_OnlyMatchesInsideRangeAreReturned()
    {
        // Given / When
        var matches = _queries.Find(new MatchFilter
        {
            Team = "Corinthians",
            From = new DateTime(2022, 1, 1),
            To = new DateTime(2022, 12, 31),
            Limit = 200,
        }, out _);

        // Then
        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.Equal(2022, m.Date!.Value.Year));
    }

    [Fact]
    public void Given_MatchDataLoaded_When_FilteringHomeVenue_Then_TeamIsAlwaysHome()
    {
        // Given / When
        var matches = _queries.Find(
            new MatchFilter { Team = "Grêmio", Venue = "home", Season = 2019, Limit = 50 }, out _);

        // Then
        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.Equal("gremio", m.HomeKey));
    }

    [Fact]
    public void Given_MatchDataLoaded_When_FilteringLibertadoresGroupStage_Then_StageMatches()
    {
        // Given / When
        var matches = _queries.Find(
            new MatchFilter { Competition = "Libertadores", Round = "group stage", Season = 2020, Limit = 20 }, out _);

        // Then
        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.Equal("group stage", m.Round));
    }

    [Fact]
    public void Given_MatchDataLoaded_When_CompetitionAliasUsed_Then_ItResolvesToCanonicalName()
    {
        // Given / When / Then
        Assert.Equal(DataLoader.SerieA, _queries.ResolveCompetition("brasileirao"));
        Assert.Equal(DataLoader.SerieA, _queries.ResolveCompetition("Serie A"));
        Assert.Equal(DataLoader.Libertadores, _queries.ResolveCompetition("libertadores"));
        Assert.Equal(DataLoader.CopaDoBrasil, _queries.ResolveCompetition("copa do brasil"));
        Assert.Equal(DataLoader.SerieB, _queries.ResolveCompetition("serie b"));
    }
}
