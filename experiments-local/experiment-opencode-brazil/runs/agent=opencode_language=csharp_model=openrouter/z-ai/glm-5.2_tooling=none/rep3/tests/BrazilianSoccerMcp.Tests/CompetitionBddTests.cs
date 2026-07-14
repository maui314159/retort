using BrazilianSoccerMcp.Services;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// BDD-style tests for competition standings, biggest victories and
/// match-level averages.
/// </summary>
[Collection("DataCollection")]
public class CompetitionBddTests
{
    private readonly DataFixture _fixture;

    public CompetitionBddTests(DataFixture fixture) => _fixture = fixture;

    [Fact]
    public void Standings_for_a_season_are_sorted_by_points_descending()
    {
        // Given the match data is loaded
        var svc = new CompetitionService(_fixture.Repository);

        // When I request standings for a recent Brasileirao season
        var seasons = svc.GetSeasons("Brasileirao");
        Assert.NotEmpty(seasons);
        var season = seasons.First();
        var table = svc.GetStandings("Brasileirao", season);

        // Then rows are sorted by points descending
        Assert.NotEmpty(table.Rows);
        for (int i = 1; i < table.Rows.Count; i++)
            Assert.True(table.Rows[i - 1].Points >= table.Rows[i].Points);

        // And points are internally consistent with W/D/L
        Assert.All(table.Rows, r =>
            Assert.Equal(r.Wins * 3 + r.Draws, r.Points));
    }

    [Fact]
    public void Biggest_victories_returns_largest_margin_first()
    {
        var svc = new CompetitionService(_fixture.Repository);
        var list = svc.BiggestVictories(limit: 5);
        Assert.NotEmpty(list);
        for (int i = 1; i < list.Count; i++)
        {
            var prev = Math.Abs(list[i - 1].HomeGoal - list[i - 1].AwayGoal);
            var curr = Math.Abs(list[i].HomeGoal - list[i].AwayGoal);
            Assert.True(prev >= curr);
        }
    }

    [Fact]
    public void Match_averages_are_consistent()
    {
        var svc = new CompetitionService(_fixture.Repository);
        var avg = svc.GetAverages("Brasileirao");
        Assert.True(avg.Matches > 0);
        Assert.True(avg.AverageGoals > 0);
        Assert.True(avg.HomeWinPercent + avg.AwayWinPercent + avg.DrawPercent - 100.0 < 0.5);
    }
}
