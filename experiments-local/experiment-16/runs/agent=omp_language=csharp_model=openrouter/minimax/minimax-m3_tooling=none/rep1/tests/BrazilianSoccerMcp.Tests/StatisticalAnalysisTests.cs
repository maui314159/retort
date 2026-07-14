// =============================================================================
// Brazilian Soccer MCP Server
// File: StatisticalAnalysisTests.cs
// Purpose: BDD tests for the "Statistical Analysis" capability.
// Context: Verifies goals-per-match, home win rate, biggest wins, etc.
// =============================================================================

using BrazilianSoccerMcp.Core;
using BrazilianSoccerMcp.Core.Models;
using FluentAssertions;

namespace BrazilianSoccerMcp.Tests;

[Collection("Dataset")]
public class StatisticalAnalysisTests
{
    private readonly QueryEngine _engine;
    public StatisticalAnalysisTests(TestDataFixture fixture) => _engine = fixture.Engine;

    // Scenario: "What's the average goals per match in the Brasileirão?"
    [Fact]
    public void Given_all_matches_When_calculating_average_goals_Then_value_between_1_and_5()
    {
        var avg = _engine.AverageGoalsPerMatch(Competition.Brasileirao);
        avg.Should().BeGreaterThan(1.0);
        avg.Should().BeLessThan(5.0);
    }

    // Scenario: home win rate is plausible (between 30% and 60%)
    [Fact]
    public void Given_all_matches_When_calculating_home_win_rate_Then_between_30_and_60_percent()
    {
        var rate = _engine.HomeWinRate(Competition.Brasileirao);
        rate.Should().BeGreaterThan(0.30);
        rate.Should().BeLessThan(0.60);
    }

    // Scenario: "Show me the biggest wins in the dataset"
    [Fact]
    public void Given_biggest_wins_When_returning_Then_first_match_has_largest_goal_difference()
    {
        var top = _engine.BiggestWins(limit: 10);
        top.Should().NotBeEmpty();
        for (var i = 1; i < top.Count; i++)
        {
            var prevDiff = Math.Abs(top[i - 1].HomeGoal - top[i - 1].AwayGoal);
            var currDiff = Math.Abs(top[i].HomeGoal - top[i].AwayGoal);
            currDiff.Should().BeLessThanOrEqualTo(prevDiff);
        }
    }

    // Scenario: goals per match is reproducible: same scope -> same number
    [Fact]
    public void Given_same_scope_When_calling_twice_Then_result_is_identical()
    {
        var a = _engine.AverageGoalsPerMatch(Competition.Brasileirao, season: 2019);
        var b = _engine.AverageGoalsPerMatch(Competition.Brasileirao, season: 2019);
        a.Should().Be(b);
    }

    // Scenario: a season-scope average is non-negative
    [Fact]
    public void Given_specific_season_When_calculating_average_goals_Then_non_negative()
    {
        var avg = _engine.AverageGoalsPerMatch(Competition.Brasileirao, season: 2020);
        avg.Should().BeGreaterThanOrEqualTo(0.0);
    }
}
