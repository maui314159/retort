// Context block
// File: StatisticsQueryTests.cs
// Purpose: BDD/GWT tests for the StatisticsService of the Brazilian Soccer MCP server,
// covering the "Statistical Analysis" feature from TASK.md: average goals per match,
// outcome rates, biggest victories, and best away record. Tests run against the real
// bundled CSV data via the shared SoccerDataFixture.
// Language: C# (.NET 10) + xUnit. Owner: Brazilian Soccer MCP benchmark implementation.

using BrazilianSoccerMcp.Models;
using BrazilianSoccerMcp.Services;

namespace BrazilianSoccerMcp.Tests;

[Collection("SoccerData")]
public class StatisticsQueryTests
{
    private readonly SoccerDataFixture _f;
    public StatisticsQueryTests(SoccerDataFixture fixture) => _f = fixture;

    // Feature: Statistical Analysis

    // Scenario: Average goals per match in the Brasileirao
    //   Given the match data is loaded
    //   When I request the average goals for the Brasileirao
    //   Then the value should be positive and reasonable
    [Fact]
    public void Average_goals_is_positive()
    {
        var avg = _f.Stats.AverageGoalsPerMatch(Competition.Brasileirao);

        Assert.True(avg > 0);
        Assert.True(avg < 10);
    }

    // Scenario: Outcome rates sum to 100%
    //   Given the match data is loaded
    //   When I request outcome rates for the Brasileirao
    //   Then home + draw + away rates should sum to ~100
    [Fact]
    public void Outcome_rates_sum_to_100()
    {
        var rates = _f.Stats.OutcomeRates(Competition.Brasileirao);

        Assert.True(rates.MatchCount > 0);
        var sum = rates.HomeWinRate + rates.DrawRate + rates.AwayWinRate;
        Assert.InRange(sum, 99.9, 100.1);
    }

    // Scenario: Biggest wins are sorted by margin
    //   Given the match data is loaded
    //   When I request the top 5 biggest wins
    //   Then the margins should be non-increasing
    [Fact]
    public void Biggest_wins_sorted_by_margin()
    {
        var wins = _f.Stats.BiggestWins(topN: 5);

        Assert.NotEmpty(wins);
        for (int i = 1; i < wins.Count; i++)
        {
            var prev = Math.Abs(wins[i - 1].HomeGoal - wins[i - 1].AwayGoal);
            var cur = Math.Abs(wins[i].HomeGoal - wins[i].AwayGoal);
            Assert.True(prev >= cur);
        }
    }

    // Scenario: Best away record is a valid team
    //   Given the match data is loaded
    //   When I request the best away record for 2022 Brasileirao
    //   Then I should get a team with a positive away record and enough matches
    [Fact]
    public void Best_away_record_returns_a_team()
    {
        var best = _f.Stats.BestAwayRecord(season: 2022, competition: Competition.Brasileirao, minMatches: 3);

        Assert.NotNull(best);
        Assert.True(best!.Played >= 3);
        Assert.Equal(Venue.Away, best.Venue);
    }
}
