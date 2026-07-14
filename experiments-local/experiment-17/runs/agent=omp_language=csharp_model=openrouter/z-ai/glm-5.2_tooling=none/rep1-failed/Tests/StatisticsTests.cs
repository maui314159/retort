// ============================================================================
// File: Tests/StatisticsTests.cs
// ----------------------------------------------------------------------------
// Context: BDD tests for the "Statistical Analysis" category (StatisticsTools):
// average goals, biggest victories, best away record.
//
// Feature: Statistical Analysis
// ============================================================================

using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Tools;

namespace BrazilianSoccerMcp.Tests;

[Collection("Store")]
public class StatisticsTests
{
    private readonly StatisticsTools _tools;

    public StatisticsTests(StoreFixture fixture)
        => _tools = new StatisticsTools(fixture.Store);

    // Scenario: What's the average goals per match in the Brasileirão?
    //   Given the match data is loaded
    //   When I request average goals for Brasileirão
    //   Then I receive a positive average and home/away/draw rates
    [Fact]
    public void AverageGoals_Brasileirao_returns_positive_average_and_rates()
    {
        var result = _tools.AverageGoals(competition: "Brasileirão");

        Assert.Contains("Average goals per match:", result);
        Assert.Contains("Home win rate:", result);
        Assert.Contains("Away win rate:", result);
        Assert.Contains("Draw rate:", result);

        var avgLine = result.Split('\n').First(l => l.Contains("Average goals per match:"));
        var avg = double.Parse(avgLine.Split(':')[1].Trim());
        Assert.InRange(avg, 1.0, 5.0);
    }

    // Scenario: Show me the biggest wins in the dataset
    //   Given the match data is loaded
    //   When I request biggest victories
    //   Then I receive a ranked list with score lines
    [Fact]
    public void BiggestWins_returns_ranked_scorelines()
    {
        var result = _tools.BiggestWins(limit: 5);

        Assert.Contains("Biggest victories", result);
        var lines = result.Split('\n').Where(l => l.TrimStart().StartsWith("1.")).ToList();
        Assert.Single(lines);
        Assert.Matches(@"\d+-\d+", result); // a score
    }

    // Scenario: Which team has the best away record?
    //   Given the match data is loaded
    //   When I request best away record for Brasileirão 2019
    //   Then I receive a ranked list of teams with away win rates
    [Fact]
    public void BestAwayRecord_Brasileirao_2019_returns_ranking()
    {
        var result = _tools.BestAwayRecord("Brasileirão", 2019, limit: 5);

        Assert.Contains("Best away records", result);
        Assert.Contains("win rate", result);
    }
}
