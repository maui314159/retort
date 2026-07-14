// <copyright file="CompetitionQueryTests.cs" company="BrazilianSoccerMcp">
// Brazilian Soccer MCP Server - BDD scenarios for competition queries.
// </copyright>
using BrazilianSoccerMcp.Core.Services;
using BrazilianSoccerMcp.Tests.Fixtures;
using FluentAssertions;

namespace BrazilianSoccerMcp.Tests.Queries;

[Collection("Data")]
public class CompetitionQueryTests
{
    private readonly SoccerQueryService _queryService;

    public CompetitionQueryTests(DataFixture fixture)
    {
        _queryService = fixture.QueryService;
    }

    [Fact]
    public void GivenMatchData_WhenCalculating2019Brasileirao_ThenFlamengoIsChampion()
    {
        var table = _queryService.GetStandings("Brasileirão", 2019);

        table.Should().NotBeEmpty();
        table.First().Team.Should().Be("Flamengo");
        table.First().Points.Should().BeGreaterThan(0);
    }

    [Fact]
    public void GivenMatchData_WhenCalculating2020Brasileirao_ThenBottomFourTeamsAreRelegationCandidates()
    {
        var table = _queryService.GetStandings("Brasileirão", 2020);

        table.Should().HaveCountGreaterThanOrEqualTo(20);
        var bottomFour = table.Skip(table.Count - 4).ToList();
        bottomFour.Should().HaveCount(4);
    }

    [Fact]
    public void GivenMatchData_WhenAskingBiggestWins_ThenReturnsHighGoalDifferenceMatches()
    {
        var wins = _queryService.GetBiggestWins("Brasileirão", 5);

        wins.Should().NotBeEmpty();
        wins.First().HomeGoals.Should().NotBeNull();
        wins.First().AwayGoals.Should().NotBeNull();
        Math.Abs(wins.First().HomeGoals!.Value - wins.First().AwayGoals!.Value).Should().BeGreaterThan(0);
    }
}
