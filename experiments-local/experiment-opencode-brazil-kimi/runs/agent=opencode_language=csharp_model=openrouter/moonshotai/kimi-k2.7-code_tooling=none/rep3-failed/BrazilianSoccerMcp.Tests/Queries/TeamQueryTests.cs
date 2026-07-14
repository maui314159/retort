// <copyright file="TeamQueryTests.cs" company="BrazilianSoccerMcp">
// Brazilian Soccer MCP Server - BDD scenarios for team queries.
// </copyright>
using BrazilianSoccerMcp.Core.Services;
using BrazilianSoccerMcp.Tests.Fixtures;
using FluentAssertions;

namespace BrazilianSoccerMcp.Tests.Queries;

[Collection("Data")]
public class TeamQueryTests
{
    private readonly SoccerQueryService _queryService;

    public TeamQueryTests(DataFixture fixture)
    {
        _queryService = fixture.QueryService;
    }

    [Fact]
    public void GivenMatchData_WhenRequestingCorinthiansHomeRecord2022_ThenReturnsWinsLossesAndGoals()
    {
        var stats = _queryService.GetTeamVenueStatistics("Corinthians", 2022, "Brasileirão");

        stats.Home.Matches.Should().BeGreaterThan(0);
        stats.Home.Matches.Should().Be(stats.Home.Wins + stats.Home.Draws + stats.Home.Losses);
        (stats.Home.GoalsFor + stats.Home.GoalsAgainst).Should().BeGreaterThan(0);
    }

    [Fact]
    public void GivenMatchData_WhenComparingPalmeirasAndSantos_ThenReturnsHeadToHeadStats()
    {
        var matches = _queryService.GetHeadToHead("Palmeiras", "Santos");
        var (palmeirasWins, draws, santosWins) = _queryService.GetHeadToHeadStats("Palmeiras", "Santos");

        matches.Count.Should().Be(palmeirasWins + draws + santosWins);
        matches.Should().NotBeEmpty();
    }

    [Fact]
    public void GivenMatchData_WhenRequestingTeamStatistics_ThenWinsPlusDrawsPlusLossesEqualsMatches()
    {
        var stats = _queryService.GetTeamStatistics("Flamengo", 2023);

        stats.Matches.Should().Be(stats.Wins + stats.Draws + stats.Losses);
        stats.Matches.Should().BeGreaterThan(0);
    }
}
