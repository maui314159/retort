// ============================================================================
// BrazilianSoccerMcp.Tests - BddCompetitionAndStats.cs
//
// Context block:
//   BDD tests for competition standings (TASK.md "Competition Queries") and
//   statistical analysis (TASK.md "Statistical Analysis"): standings are
//   computed from matches, champion is position 1, goals overview averages
//   are positive, biggest wins are sorted by goal difference.
// ============================================================================

using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

public class BddCompetitionAndStats : IClassFixture<DataFixture>
{
    private readonly DataFixture _f;
    public BddCompetitionAndStats(DataFixture f) => _f = f;

    // Scenario: Who won the Brasileirao in a given season?
    [Fact]
    public void Given_brasileirao_matches_when_computing_standings_then_champion_is_position_1()
    {
        var seasons = _f.Service.ListSeasons(Competition.Brasileirao);
        Assert.NotEmpty(seasons);
        var season = seasons.Max(); // most recent fully-loaded season
        var rows = _f.Service.GetStandings(Competition.Brasileirao, season);

        Assert.NotEmpty(rows);
        Assert.Equal(1, rows[0].Position);
        Assert.True(rows[0].IsChampion, "position 1 should be flagged champion");
        // Standings should be sorted by points desc
        for (int i = 1; i < rows.Count; i++)
            Assert.True(rows[i - 1].Points >= rows[i].Points);
    }

    // Scenario: Standings rows satisfy points arithmetic
    [Fact]
    public void Given_standings_when_computed_then_points_equal_3w_plus_d()
    {
        var rows = _f.Service.GetStandings(Competition.HistoricoBrasileirao, 2019);
        Assert.NotEmpty(rows);
        Assert.All(rows, r => Assert.Equal(3 * r.Wins + r.Draws, r.Points));
        Assert.All(rows, r => Assert.Equal(r.Wins + r.Draws + r.Losses, r.Played));
    }

    // Scenario: Goals overview averages are positive
    [Fact]
    public void Given_all_matches_when_goals_overview_then_averages_are_reasonable()
    {
        var o = _f.Service.GetGoalsOverview();
        Assert.True(o.Matches > 0);
        Assert.InRange(o.AverageGoalsPerMatch, 0.5, 10.0);
        Assert.InRange(o.HomeWinRate + o.AwayWinRate + o.DrawRate, 99.9, 100.1);
    }

    // Scenario: Biggest wins are sorted by goal difference
    [Fact]
    public void Given_all_matches_when_biggest_wins_then_sorted_by_goal_difference_desc()
    {
        var wins = _f.Service.GetBiggestWins(limit: 5);
        Assert.True(wins.Count >= 5);
        for (int i = 1; i < wins.Count; i++)
        {
            var prev = Math.Abs(wins[i - 1].HomeGoals!.Value - wins[i - 1].AwayGoals!.Value);
            var cur = Math.Abs(wins[i].HomeGoals!.Value - wins[i].AwayGoals!.Value);
            Assert.True(prev >= cur);
        }
    }

    // Scenario: Standings for a single Serie A season has ~20 teams
    [Fact]
    public void Given_historico_2019_when_standings_then_about_20_teams()
    {
        var rows = _f.Service.GetStandings(Competition.HistoricoBrasileirao, 2019);
        Assert.InRange(rows.Count, 18, 24);
        // Bottom 4 of a >=20 team league flagged relegated
        Assert.All(rows.Where(r => r.Position >= rows.Count - 3), r => Assert.True(r.Relegated));
        Assert.True(rows[0].IsChampion);
    }

    // Scenario: Competition standings reject unknown competition gracefully
    [Fact]
    public void Given_unknown_competition_when_standings_then_empty()
    {
        var rows = _f.Service.GetStandings(Competition.Libertadores, 1900);
        Assert.Empty(rows);
    }
}
