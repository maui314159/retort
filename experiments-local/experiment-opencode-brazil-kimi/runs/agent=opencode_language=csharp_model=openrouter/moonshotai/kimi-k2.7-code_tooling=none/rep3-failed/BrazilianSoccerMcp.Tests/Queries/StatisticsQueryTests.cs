// <copyright file="StatisticsQueryTests.cs" company="BrazilianSoccerMcp">
// Brazilian Soccer MCP Server - BDD scenarios for statistical analysis.
// </copyright>
using BrazilianSoccerMcp.Core.Services;
using BrazilianSoccerMcp.Tests.Fixtures;
using FluentAssertions;

namespace BrazilianSoccerMcp.Tests.Queries;

[Collection("Data")]
public class StatisticsQueryTests
{
    private readonly SoccerQueryService _queryService;

    public StatisticsQueryTests(DataFixture fixture)
    {
        _queryService = fixture.QueryService;
    }

    [Fact]
    public void GivenMatchData_WhenCalculatingAverageGoals_ThenReturnsPositiveAverage()
    {
        var stats = _queryService.GetCompetitionStatistics("Brasileirão");

        stats.MatchesPlayed.Should().BeGreaterThan(0);
        stats.AverageGoalsPerMatch.Should().BeGreaterThan(0);
    }

    [Fact]
    public void GivenMatchData_WhenCalculatingHomeWinRate_ThenHomeWinsAreMoreLikelyThanAwayWins()
    {
        var stats = _queryService.GetCompetitionStatistics("Brasileirão");

        stats.HomeWinRate.Should().BeGreaterThan(stats.AwayWinRate);
    }

    [Fact]
    public void GivenMatchData_WhenAskingBestAwayRecords_ThenReturnsTeamsWithPositiveAwayMatches()
    {
        var records = _queryService.GetBestAwayRecords(minMatches: 10);

        records.Should().NotBeEmpty();
        records.Should().OnlyContain(r => r.Matches >= 10);
    }
}
