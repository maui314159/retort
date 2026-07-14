/*
 * Brazilian Soccer MCP Server - Match Query Tests
 *
 * BDD scenarios covering match lookups by team, season, competition and date.
 */
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Queries;

namespace BrazilianSoccerMcp.Tests;

public class MatchQueryTests : QueryTestBase
{
    public MatchQueryTests(DataFixture fixture) : base(fixture) { }

    [Fact]
    public void GivenMatchDataLoaded_WhenSearchingForFlamengoVsFluminense_ThenReceiveMatchesWithDateScoresAndCompetition()
    {
        var matches = Engine.FindMatches(team: "Flamengo", opponent: "Fluminense");

        Assert.NotEmpty(matches);
        Assert.All(matches, m =>
        {
            Assert.True(m.Date.HasValue);
            Assert.True(m.HomeGoals.HasValue);
            Assert.True(m.AwayGoals.HasValue);
            Assert.False(string.IsNullOrWhiteSpace(m.Competition));
            Assert.True(TeamNameNormalizer.AreSame(m.HomeTeam, "Flamengo") || TeamNameNormalizer.AreSame(m.HomeTeam, "Fluminense"));
            Assert.True(TeamNameNormalizer.AreSame(m.AwayTeam, "Flamengo") || TeamNameNormalizer.AreSame(m.AwayTeam, "Fluminense"));
        });
    }

    [Fact]
    public void GivenMatchDataLoaded_WhenSearchingForPalmeirasIn2023_ThenReceiveOnly2023PalmeirasMatches()
    {
        var matches = Engine.FindMatches(team: "Palmeiras", season: 2023);

        Assert.NotEmpty(matches);
        Assert.All(matches, m =>
        {
            Assert.Equal(2023, m.Season);
            Assert.True(TeamNameNormalizer.AreSame(m.HomeTeam, "Palmeiras") || TeamNameNormalizer.AreSame(m.AwayTeam, "Palmeiras"));
        });
    }

    [Fact]
    public void GivenMatchDataLoaded_WhenSearchingForLibertadoresFinals_ThenReceiveFinalStageMatches()
    {
        var matches = Engine.FindMatches(competition: "Copa Libertadores")
            .Where(m => !string.IsNullOrWhiteSpace(m.Stage) && m.Stage.Contains("final", StringComparison.OrdinalIgnoreCase))
            .ToList();

        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.Equal("Copa Libertadores", m.Competition));
    }

    [Fact]
    public void GivenMatchDataLoaded_WhenFilteringByDateRange_ThenOnlyMatchesInRangeReturned()
    {
        var from = new DateTime(2023, 1, 1);
        var to = new DateTime(2023, 12, 31);

        var matches = Engine.FindMatches(team: "Flamengo", dateFrom: from, dateTo: to);

        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.True(m.Date >= from && m.Date <= to));
    }

    [Fact]
    public void GivenDifferentNameFormats_WhenSearchingForPalmeiras_ThenMatchesFromAllDatasetsAreFound()
    {
        var matches = Engine.FindMatches(team: "Palmeiras");

        Assert.NotEmpty(matches);
        var competitions = matches.Select(m => m.Competition).Distinct().ToList();
        Assert.Contains("Brasileirão", competitions);
    }
}
