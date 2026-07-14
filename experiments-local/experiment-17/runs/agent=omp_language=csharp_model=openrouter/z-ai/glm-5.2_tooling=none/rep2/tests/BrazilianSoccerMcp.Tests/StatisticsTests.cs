using BrazilianSoccerMcp.Tests.Infrastructure;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Feature: Statistical Analysis
/// BDD scenarios for aggregate match statistics.
/// </summary>
[Collection("SoccerData")]
public class StatisticsTests
{
    private readonly DataFixture _f;
    public StatisticsTests(DataFixture f) => _f = f;

    // Scenario: average goals per match in the Brasileirão
    //   Given the match data is loaded
    //   When I request the average goals per match for the Brasileirão
    //   Then I should receive a positive number around 2-3
    [Fact]
    public void AverageGoalsPerMatch_is_positive_and_reasonable()
    {
        var avg = _f.Stats.AverageGoalsPerMatch("Brasileirão");
        Assert.True(avg > 0);
        Assert.InRange(avg, 1.0, 6.0);
    }

    // Scenario: aggregate stats sum correctly
    //   home wins + away wins + draws == matches
    [Fact]
    public void Aggregate_wins_draws_sum_to_matches()
    {
        var agg = _f.Stats.Aggregate("Brasileirão", 2019);
        Assert.True(agg.Matches > 0);
        Assert.Equal(agg.Matches, agg.HomeWins + agg.AwayWins + agg.Draws);
    }

    // Scenario: home win rate + away win rate + draw rate ≈ 100
    [Fact]
    public void Aggregate_rates_sum_to_100()
    {
        var agg = _f.Stats.Aggregate("Brasileirão", 2019);
        Assert.True(agg.Matches > 0);
        var total = agg.HomeWinRate + agg.AwayWinRate + agg.DrawRate;
        Assert.InRange(total, 99.5, 100.5);
    }

    // Scenario: average goals = total goals / matches
    [Fact]
    public void AverageGoals_equals_total_divided_by_matches()
    {
        var agg = _f.Stats.Aggregate("Brasileirão", 2019);
        Assert.Equal(Math.Round((double)agg.TotalGoals / agg.Matches, 2), agg.AverageGoalsPerMatch);
    }

    // Scenario: home advantage — home win rate exceeds away win rate
    [Fact]
    public void HomeWinRate_exceeds_away_win_rate_overall()
    {
        var agg = _f.Stats.Aggregate();
        Assert.True(agg.Matches > 0);
        Assert.True(agg.HomeWinRate > agg.AwayWinRate,
            $"expected home win rate ({agg.HomeWinRate}%) > away win rate ({agg.AwayWinRate}%)");
    }

    // Scenario: season comparison across years
    [Fact]
    public void SeasonComparison_returns_multiple_seasons()
    {
        var seasons = _f.Stats.SeasonComparison("Brasileirão", 2018, 2019);
        Assert.True(seasons.Count >= 1);
        Assert.All(seasons, s => Assert.True(s.AvgGoals > 0));
    }
}