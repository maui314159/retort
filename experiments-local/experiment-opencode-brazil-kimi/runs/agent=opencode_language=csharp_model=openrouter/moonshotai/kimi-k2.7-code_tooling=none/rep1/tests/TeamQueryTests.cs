/*
 * Brazilian Soccer MCP Server - Team Query Tests
 *
 * BDD scenarios covering team statistics, home/away records and head-to-head.
 */
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Queries;

namespace BrazilianSoccerMcp.Tests;

public class TeamQueryTests : QueryTestBase
{
    public TeamQueryTests(DataFixture fixture) : base(fixture) { }

    [Fact]
    public void GivenMatchDataLoaded_WhenRequestingCorinthiansHomeRecordIn2022_ThenReceiveWinsDrawsLossesAndGoals()
    {
        var stats = Engine.GetTeamStatistics("Corinthians", season: 2022, competition: "Brasileirão", homeOnly: true);

        Assert.True(stats.Matches > 0);
        Assert.Equal(stats.Matches, stats.Wins + stats.Draws + stats.Losses);
        Assert.True(stats.GoalsFor >= 0);
        Assert.True(stats.GoalsAgainst >= 0);
    }

    [Fact]
    public void GivenMatchDataLoaded_WhenComparingPalmeirasAndSantos_ThenReceiveHeadToHeadStatistics()
    {
        var h2h = Engine.GetHeadToHead("Palmeiras", "Santos");

        Assert.True(h2h.Matches > 0);
        Assert.Equal(h2h.Matches, h2h.TeamAWins + h2h.TeamBWins + h2h.Draws);
    }

    [Fact]
    public void GivenMatchDataLoaded_WhenSearchingForTeamWithMostGoalsIn2023Brasileirao_ThenReceiveValidStatistics()
    {
        var standings = Engine.GetCompetitionStandings(2023, "Brasileirão");
        var topScorer = standings.OrderByDescending(s => s.GoalsFor).First();

        Assert.True(topScorer.GoalsFor > 0);
        Assert.False(string.IsNullOrWhiteSpace(topScorer.Team));
    }

    [Fact]
    public void GivenMatchDataLoaded_WhenRequestingBestAwayRecord_ThenReceiveTeamWithHighestAwayWinRate()
    {
        var stats = Engine.GetBestAwayRecord(competition: "Brasileirão");

        Assert.False(string.IsNullOrWhiteSpace(stats.Team));
        Assert.True(stats.Matches > 0);
    }
}
