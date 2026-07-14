// BrazilianSoccerMcp.Tests - BDD feature: Statistical Analysis.
// Covers average goals per match, home/draw/away win-rate breakdown, and
// biggest-victory ranking.
using BrazilianSoccerMcp.Core.Data;
using LightBDD.Framework;
using LightBDD.Framework.Scenarios;

namespace BrazilianSoccerMcp.Tests;

[FeatureDescription(
    "Statistical analysis: average goals per match, home/draw/away win rates, " +
    "and biggest victories by goal difference.")]
public class StatisticsTests : SoccerFeatureFixture
{
    [Scenario]
    public void Average_goals_per_match_in_Brasileirao()
    {
        Runner.RunScenario(
            Given_the_match_data_is_loaded,
            When_I_request_the_average_goals_per_Brasileirao_match,
            Then_the_average_should_be_between_1_and_6);
    }

    [Scenario]
    public void Win_rate_breakdown_sums_to_one()
    {
        Runner.RunScenario(
            Given_the_match_data_is_loaded,
            When_I_request_the_win_rate_breakdown_for_Brasileirao,
            Then_home_plus_draw_plus_away_rates_should_sum_to_one);
    }

    [Scenario]
    public void Biggest_victories_are_ranked_by_goal_difference()
    {
        Runner.RunScenario(
            Given_the_match_data_is_loaded,
            When_I_request_the_top_5_biggest_victories,
            Then_I_should_receive_5_matches,
            And_the_first_match_should_have_the_largest_goal_difference);
    }

    // --- steps ------------------------------------------------------------

    private void Given_the_match_data_is_loaded() { }

    private void When_I_request_the_average_goals_per_Brasileirao_match()
        => ResultDouble = Query.AverageGoalsPerMatch(Competition.Brasileirao);

    private void When_I_request_the_win_rate_breakdown_for_Brasileirao()
        => ResultRates = Query.WinRateBreakdown(Competition.Brasileirao);

    private void When_I_request_the_top_5_biggest_victories()
        => ResultMatches = Query.BiggestWins(top: 5);

    private void Then_the_average_should_be_between_1_and_6()
        => Assert.InRange(ResultDouble, 1.0, 6.0);

    private void Then_home_plus_draw_plus_away_rates_should_sum_to_one()
    {
        var sum = ResultRates.Home + ResultRates.Draw + ResultRates.Away;
        Assert.InRange(sum, 0.999, 1.001);
    }

    private void Then_I_should_receive_5_matches()
        => Assert.Equal(5, ResultMatches.Count);

    private void And_the_first_match_should_have_the_largest_goal_difference()
    {
        var max = ResultMatches.Max(m => m.GoalDifference);
        Assert.Equal(max, ResultMatches[0].GoalDifference);
        Assert.True(max >= 1);
    }
}
