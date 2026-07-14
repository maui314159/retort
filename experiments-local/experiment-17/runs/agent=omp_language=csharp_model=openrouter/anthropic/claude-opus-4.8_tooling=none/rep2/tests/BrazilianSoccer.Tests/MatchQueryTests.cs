// =============================================================================
// Context
// -----------------------------------------------------------------------------
// File:    MatchQueryTests.cs
// Project: BrazilianSoccer.Tests
// Purpose: BDD (Given/When/Then) scenarios for match queries against the real
//          loaded dataset, covering the spec's "Feature: Match Queries":
//          find matches between teams, by team+season, by competition, and the
//          most-recent-meeting lookup.
// =============================================================================

using BrazilianSoccer.Core.Models;
using BrazilianSoccer.Core.Queries;
using Xunit;

namespace BrazilianSoccer.Tests;

[Collection("dataset")]
public sealed class MatchQueryTests
{
    private readonly QueryService _query;

    public MatchQueryTests(DatasetFixture fixture) => _query = fixture.Query;

    [Fact]
    public void Given_LoadedData_When_SearchMatchesBetweenFlamengoAndFluminense_Then_ReturnsMatchesWithScores()
    {
        // When I search for matches between Flamengo and Fluminense
        var matches = _query.MatchesBetween("Flamengo", "Fluminense");

        // Then I should receive a non-empty list, each with the two teams
        Assert.NotEmpty(matches);
        Assert.All(matches, m =>
        {
            var pair = new[] { m.HomeTeamKey, m.AwayTeamKey };
            Assert.Contains("flamengo", pair);
            Assert.Contains("fluminense", pair);
        });
    }

    [Fact]
    public void Given_LoadedData_When_FilteredByTeamAndSeason_Then_AllMatchesAreThatTeamInThatSeason()
    {
        // When I request Palmeiras matches in 2019
        var matches = _query.FindMatches(new MatchFilter { Team = "Palmeiras", Season = 2019 });

        // Then every result involves Palmeiras and is from 2019
        Assert.NotEmpty(matches);
        Assert.All(matches, m =>
        {
            Assert.Equal(2019, m.Season);
            Assert.True(m.HomeTeamKey == "palmeiras" || m.AwayTeamKey == "palmeiras");
        });
    }

    [Fact]
    public void Given_LoadedData_When_FilteredByCompetition_Then_OnlyThatCompetitionReturned()
    {
        // When I filter by Copa do Brasil
        var matches = _query.FindMatches(new MatchFilter { Competition = Competition.CopaDoBrasil, Limit = 50 });

        // Then every match is a Copa do Brasil match
        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.Equal(Competition.CopaDoBrasil, m.Competition));
    }

    [Fact]
    public void Given_LoadedData_When_ResultsReturned_Then_TheyAreOrderedNewestFirst()
    {
        // When I fetch a team's matches
        var matches = _query.FindMatches(new MatchFilter { Team = "Flamengo", Limit = 30 });

        // Then dates are descending
        var dated = matches.Where(m => m.Date is not null).Select(m => m.Date!.Value).ToList();
        for (var i = 1; i < dated.Count; i++)
            Assert.True(dated[i - 1] >= dated[i]);
    }

    [Fact]
    public void Given_TwoTeams_When_AskingForLastMeeting_Then_ItIsTheMostRecentInData()
    {
        // When I ask for the most recent Flamengo vs Corinthians match
        var last = _query.LastMatchBetween("Flamengo", "Corinthians");
        var all = _query.MatchesBetween("Flamengo", "Corinthians");

        // Then it equals the newest-dated match in the full list
        Assert.NotNull(last);
        var expected = all.OrderByDescending(m => m.Date ?? DateTime.MinValue).First();
        Assert.Equal(expected.Date, last!.Date);
    }

    [Fact]
    public void Given_UnknownTeam_When_Searched_Then_ResultIsEmptyNotError()
    {
        var matches = _query.MatchesBetween("Nonexistent FC", "Flamengo");
        Assert.Empty(matches);
    }
}
