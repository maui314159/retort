using BrazilianSoccerMcp.Server.Data;
using BrazilianSoccerMcp.Server.Services;
using BrazilianSoccerMcp.Tests.Data;
using FluentAssertions;

namespace BrazilianSoccerMcp.Tests.Services;

[Collection("SoccerData")]
public sealed class CompetitionQueriesTests
{
    private readonly SoccerDataContext _context;

    public CompetitionQueriesTests(DataFixture fixture)
    {
        _context = fixture.Context;
    }

    [Fact]
    public void Given_the_match_data_is_loaded_When_calculating_2019_Brasileirao_standings_Then_the_champion_should_have_the_most_points()
    {
        var service = new CompetitionService(_context);

        var standings = service.GetStandings("Brasileirão", 2019);

        standings.Should().NotBeEmpty();
        standings.First().Points.Should().BeGreaterThanOrEqualTo(90);
        standings.First().Points.Should().BeGreaterThan(standings.Skip(1).First().Points);
    }

    [Fact]
    public void Given_the_match_data_is_loaded_When_requesting_Libertadores_finals_Then_should_return_final_matches()
    {
        var service = new CompetitionService(_context);

        var finals = service.GetBracket("Copa Libertadores", 2013, "final");

        finals.Should().NotBeEmpty();
        finals.Should().OnlyContain(m =>
            m.Competition.Contains("Libertadores", StringComparison.OrdinalIgnoreCase));
    }
}
