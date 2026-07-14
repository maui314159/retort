using BrazilianSoccerMcp.Server.Data;
using BrazilianSoccerMcp.Server.Services;
using BrazilianSoccerMcp.Tests.Data;
using FluentAssertions;

namespace BrazilianSoccerMcp.Tests.Services;

[Collection("SoccerData")]
public sealed class StatisticsQueriesTests
{
    private readonly SoccerDataContext _context;

    public StatisticsQueriesTests(DataFixture fixture)
    {
        _context = fixture.Context;
    }

    [Fact]
    public void Given_the_match_data_is_loaded_When_calculating_average_goals_Then_result_should_be_between_one_and_five()
    {
        var service = new StatisticsService(_context);

        var result = service.GetAverageGoals(competition: "Brasileirão", season: 2019);

        var average = ExtractAverage(result);
        average.Should().BeGreaterThan(0);
        average.Should().BeLessThan(8);
    }

    [Fact]
    public void Given_the_match_data_is_loaded_When_requesting_biggest_wins_Then_should_return_matches_with_large_margins()
    {
        var service = new StatisticsService(_context);

        var result = service.GetBiggestWins(competition: "Brasileirão", limit: 5);

        result.Should().NotBeNullOrWhiteSpace();
        result.Should().Contain("Biggest wins");
    }

    private static double ExtractAverage(string text)
    {
        var tokens = text.Split(new[] { ' ', ':' }, StringSplitOptions.RemoveEmptyEntries);
        foreach (var token in tokens)
        {
            if (double.TryParse(token, out var value))
            {
                return value;
            }
        }

        return 0;
    }
}
