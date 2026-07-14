/*
 * Brazilian Soccer MCP Server - Competition and Statistics Tests
 *
 * BDD scenarios covering league standings, biggest wins and average goals.
 */
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Queries;

namespace BrazilianSoccerMcp.Tests;

public class CompetitionAndStatsTests : QueryTestBase
{
    public CompetitionAndStatsTests(DataFixture fixture) : base(fixture) { }

    [Fact]
    public void GivenMatchDataLoaded_WhenRequesting2019BrasileiraoStandings_ThenReceiveStandingsWithChampionOnTop()
    {
        var standings = Engine.GetCompetitionStandings(2019, "Brasileirão");

        Assert.NotEmpty(standings);
        Assert.Equal("Flamengo", standings[0].Team, StringComparer.OrdinalIgnoreCase);
        Assert.True(standings[0].Points > 0);
    }

    [Fact]
    public void GivenMatchDataLoaded_WhenRequestingBiggestWins_ThenReceiveMatchesWithLargeGoalDifferences()
    {
        var matches = Engine.GetBiggestWins(competition: "Brasileirão", count: 5);

        Assert.Equal(5, matches.Count);
        Assert.All(matches, m =>
        {
            Assert.True(m.HomeGoals.HasValue && m.AwayGoals.HasValue);
            Assert.True(Math.Abs(m.HomeGoals.Value - m.AwayGoals.Value) > 0);
        });
    }

    [Fact]
    public void GivenMatchDataLoaded_WhenRequestingAverageGoals_ThenReceivePositiveAverage()
    {
        var average = Engine.GetAverageGoalsPerMatch("Brasileirão");

        Assert.True(average > 0);
    }

    [Fact]
    public void GivenMatchDataLoaded_WhenRequestingTeamCompetitions_ThenReceiveDistinctCompetitions()
    {
        var competitions = Engine.GetTeamCompetitions("Palmeiras");

        Assert.NotEmpty(competitions);
        Assert.Equal(competitions.Count, competitions.Distinct(StringComparer.OrdinalIgnoreCase).Count());
    }

    [Fact]
    public void GivenMatchDataLoaded_WhenRequestingRelegatedTeamsIn2020_ThenBottomFourTeamsReturned()
    {
        var standings = Engine.GetCompetitionStandings(2020, "Brasileirão");
        var relegated = standings.TakeLast(4).ToList();

        Assert.Equal(4, relegated.Count);
        Assert.All(relegated, r => Assert.True(r.Points >= 0));
    }
}
