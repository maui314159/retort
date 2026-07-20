using System.Diagnostics;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Feature: Statistical Analysis
///   Aggregated statistics: goals per match, home/away performance,
///   head-to-head records, biggest wins. Plus derby discovery and the
///   performance requirements from the spec.
/// </summary>
public class StatsQueryTests
{
    /*
     * Scenario: Average goals per match in the Brasileirão
     *   Given the match data is loaded
     *   When I request overview stats for the Brasileirão
     *   Then the average goals per match is a plausible football number (2-4)
     */
    [Fact]
    public void Average_goals_per_match_is_plausible()
    {
        // Given
        var service = TestData.Service;

        // When
        var stats = service.GetOverview(competition: "Brasileirão");

        // Then
        Assert.True(stats.MatchCount > 1000);
        Assert.InRange(stats.AvgGoalsPerMatch, 1.5, 4.0);
        // rates are individually rounded to 0.1%, so the sum may deviate slightly
        Assert.InRange(stats.HomeWinRate + stats.DrawRate + stats.AwayWinRate, 99.0, 101.0);
    }

    /*
     * Scenario: Home advantage exists
     *   Given the match data is loaded
     *   When I request dataset-wide overview stats
     *   Then the home win rate exceeds the away win rate
     */
    [Fact]
    public void Home_advantage_exists()
    {
        // Given
        var service = TestData.Service;

        // When
        var stats = service.GetOverview();

        // Then
        Assert.True(stats.HomeWinRate > stats.AwayWinRate,
            $"Home {stats.HomeWinRate}% should exceed away {stats.AwayWinRate}%");
    }

    /*
     * Scenario: Show me the biggest wins in the dataset
     *   Given the match data is loaded
     *   When I request the 10 biggest wins
     *   Then they are ordered by goal margin, largest first
     */
    [Fact]
    public void Biggest_wins_are_ordered_by_margin()
    {
        // Given
        var service = TestData.Service;

        // When
        var wins = service.GetBiggestWins(limit: 10);

        // Then
        Assert.Equal(10, wins.Count);
        var margins = wins.Select(m => m.GoalMargin).ToList();
        Assert.Equal(margins.OrderByDescending(x => x).ToList(), margins);
        Assert.True(wins[0].GoalMargin >= 7, $"Expected a blowout, got margin {wins[0].GoalMargin}");
    }

    /*
     * Scenario: Which team has the best away record?
     *   Given the match data is loaded
     *   When I rank teams by away win rate
     *   Then the ranking is sorted and every team played enough away games
     */
    [Fact]
    public void Best_away_record_can_be_ranked()
    {
        // Given
        var service = TestData.Service;

        // When
        var best = service.GetBestRecords("away", limit: 10);

        // Then
        Assert.NotEmpty(best);
        Assert.All(best, x => Assert.True(x.Record.Matches >= 10));
        var rates = best.Select(x => x.Record.WinRate).ToList();
        Assert.Equal(rates.OrderByDescending(r => r).ToList(), rates);
    }

    /*
     * Scenario: Show me all derbies in 2023
     *   Given the match data is loaded
     *   When I search derbies for season 2023
     *   Then classic rivalries like Fla-Flu and Grenal are found
     */
    [Fact]
    public void Derbies_in_a_season_are_found()
    {
        // Given
        var service = TestData.Service;

        // When
        var derbies = service.FindDerbies(season: 2023);

        // Then
        Assert.NotEmpty(derbies);
        var names = derbies.Select(d => d.DerbyName).Distinct().ToList();
        Assert.Contains("Fla-Flu", names);
        Assert.Contains("Grenal", names);
    }

    /*
     * Scenario: Compare the 2018 and 2019 seasons
     *   Given the match data is loaded
     *   When I request overview stats for both seasons
     *   Then both seasons have matches and comparable goal averages
     */
    [Fact]
    public void Seasons_can_be_compared()
    {
        // Given
        var service = TestData.Service;

        // When
        var s2018 = service.GetOverview(competition: "Brasileirão Série A", season: 2018);
        var s2019 = service.GetOverview(competition: "Brasileirão Série A", season: 2019);

        // Then
        Assert.True(s2018.MatchCount >= 380, $"2018: {s2018.MatchCount} matches");
        Assert.True(s2019.MatchCount >= 380, $"2019: {s2019.MatchCount} matches");
        Assert.InRange(s2018.AvgGoalsPerMatch, 1.5, 4.0);
        Assert.InRange(s2019.AvgGoalsPerMatch, 1.5, 4.0);
    }

    /*
     * Scenario: Simple lookups respond in under 2 seconds
     *   Given the match data is loaded
     *   When I perform a simple match lookup
     *   Then it completes in < 2 seconds
     */
    [Fact]
    public void Simple_lookup_is_fast()
    {
        // Given
        var service = TestData.Service;

        // When
        var sw = Stopwatch.StartNew();
        var matches = service.FindMatches(team1: "Flamengo", team2: "Corinthians", limit: 1);
        sw.Stop();

        // Then
        Assert.NotEmpty(matches);
        Assert.True(sw.Elapsed < TimeSpan.FromSeconds(2), $"Lookup took {sw.Elapsed}");
    }

    /*
     * Scenario: Aggregate queries respond in under 5 seconds
     *   Given the match data is loaded
     *   When I compute a full season standings table
     *   Then it completes in < 5 seconds
     */
    [Fact]
    public void Aggregate_query_is_fast()
    {
        // Given
        var service = TestData.Service;

        // When
        var sw = Stopwatch.StartNew();
        var standings = service.GetStandings("Brasileirão Série A", 2019);
        var overview = service.GetOverview(season: 2019);
        var h2h = service.GetHeadToHead("Palmeiras", "Santos");
        sw.Stop();

        // Then
        Assert.NotEmpty(standings);
        Assert.True(overview.MatchCount > 0);
        Assert.NotEmpty(h2h.Matches);
        Assert.True(sw.Elapsed < TimeSpan.FromSeconds(5), $"Aggregates took {sw.Elapsed}");
    }
}
