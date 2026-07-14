// <copyright file="MatchQueryTests.cs" company="BrazilianSoccerMcp">
// Brazilian Soccer MCP Server - BDD scenarios for match queries.
// </copyright>
using BrazilianSoccerMcp.Core.Models;
using BrazilianSoccerMcp.Core.Services;
using BrazilianSoccerMcp.Tests.Fixtures;
using FluentAssertions;

namespace BrazilianSoccerMcp.Tests.Queries;

[Collection("Data")]
public class MatchQueryTests
{
    private readonly SoccerQueryService _queryService;

    public MatchQueryTests(DataFixture fixture)
    {
        _queryService = fixture.QueryService;
    }

    [Fact]
    public void GivenMatchData_WhenSearchingForFlamengoVsFluminense_ThenReturnsRecentMatches()
    {
        var matches = _queryService.GetHeadToHead("Flamengo", "Fluminense");

        matches.Should().NotBeEmpty();
        matches.Should().OnlyContain(m => m.Involves("Flamengo") && m.Involves("Fluminense"));
        matches.First().Date.Should().NotBeNull();
        matches.Should().BeInDescendingOrder(m => m.Date);
    }

    [Fact]
    public void GivenMatchData_WhenSearchingForPalmeirasIn2023_ThenReturnsMatchesWithScores()
    {
        var matches = _queryService.SearchMatches(new MatchSearchCriteria
        {
            Team = "Palmeiras",
            Season = 2023
        });

        matches.Should().NotBeEmpty();
        matches.Should().OnlyContain(m => m.Involves("Palmeiras") && m.Season == 2023);
        matches.Should().OnlyContain(m => m.HomeGoals.HasValue && m.AwayGoals.HasValue);
    }

    [Fact]
    public void GivenMatchData_WhenSearchingCopaDoBrasilLatestRound_ThenReturnsMatches()
    {
        var matches = _queryService.SearchMatches(new MatchSearchCriteria
        {
            Competition = "Copa do Brasil",
            Round = "8"
        });

        matches.Should().NotBeEmpty();
        matches.Should().OnlyContain(m =>
            m.Competition.Equals("Copa do Brasil", StringComparison.OrdinalIgnoreCase) &&
            m.Round == "8");
    }
}
