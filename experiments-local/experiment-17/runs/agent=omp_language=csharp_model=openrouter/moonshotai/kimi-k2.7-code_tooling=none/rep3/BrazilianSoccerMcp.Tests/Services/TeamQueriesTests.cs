using BrazilianSoccerMcp.Server.Data;
using BrazilianSoccerMcp.Server.Services;
using BrazilianSoccerMcp.Tests.Data;
using FluentAssertions;

namespace BrazilianSoccerMcp.Tests.Services;

[Collection("SoccerData")]
public sealed class TeamQueriesTests
{
    private readonly SoccerDataContext _context;

    public TeamQueriesTests(DataFixture fixture)
    {
        _context = fixture.Context;
    }

    [Fact]
    public void Given_the_match_data_is_loaded_When_requesting_statistics_for_Palmeiras_in_2019_Then_should_receive_wins_losses_draws_and_goals()
    {
        var service = new TeamService(_context);

        var stats = service.GetStatistics("Palmeiras", competition: "Brasileirão", season: 2019);

        stats.Matches.Should().BeGreaterThan(0);
        stats.Wins.Should().BeGreaterThanOrEqualTo(0);
        stats.Draws.Should().BeGreaterThanOrEqualTo(0);
        stats.Losses.Should().BeGreaterThanOrEqualTo(0);
        stats.GoalsFor.Should().BeGreaterThanOrEqualTo(0);
        stats.GoalsAgainst.Should().BeGreaterThanOrEqualTo(0);
        (stats.Wins + stats.Draws + stats.Losses).Should().Be(stats.Matches);
    }

    [Fact]
    public void Given_the_match_data_is_loaded_When_requesting_home_statistics_Then_only_home_matches_should_be_counted()
    {
        var service = new TeamService(_context);

        var homeStats = service.GetStatistics("Flamengo", competition: "Brasileirão", season: 2019, homeOnly: true);
        var overallStats = service.GetStatistics("Flamengo", competition: "Brasileirão", season: 2019);

        homeStats.Matches.Should().BeLessThanOrEqualTo(overallStats.Matches);
    }
}
