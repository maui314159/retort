using BrazilianSoccerMcp.Services;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Feature: Statistical Analysis
/// Aggregated goals-per-match averages, home vs away performance and record wins.
/// </summary>
public class CompetitionStatsFeatureTests
{
    private readonly TeamAnalyticsService _analytics =
        new(TestData.Graph, new MatchQueryService(TestData.Graph));

    [Fact]
    public void Given_MatchDataLoaded_When_RequestingSerieAverages_Then_AvgGoalsPerMatchIsRealistic()
    {
        // Given / When ("What's the average goals per match in the Brasileirão?")
        var stats = _analytics.GetCompetitionStats("Brasileirão");

        // Then
        Assert.True(stats.PlayedMatches > 7_000, $"expected the full unified history, got {stats.PlayedMatches}");
        Assert.InRange(stats.AvgGoalsPerMatch, 2.0, 3.0);
        Assert.Equal(stats.TotalMatches, stats.PlayedMatches + (stats.TotalMatches - stats.PlayedMatches));
    }

    [Fact]
    public void Given_MatchDataLoaded_When_ComparingHomeAndAway_Then_HomeAdvantageExists()
    {
        // Given / When
        var stats = _analytics.GetCompetitionStats("Serie A");

        // Then: the well-known home advantage shows in the aggregates
        Assert.True(stats.HomeWinRate > stats.AwayWinRate,
            $"home {stats.HomeWinRate:P} should exceed away {stats.AwayWinRate:P}");
        Assert.InRange(stats.HomeWinRate, 0.40, 0.55);
        Assert.Equal(1.0, stats.HomeWinRate + stats.DrawRate + stats.AwayWinRate, precision: 6);
    }

    [Fact]
    public void Given_MatchDataLoaded_When_RequestingBiggestWins_Then_TheyAreOrderedByMargin()
    {
        // Given / When
        var wins = _analytics.GetBiggestWins(limit: 10);

        // Then
        Assert.Equal(10, wins.Count);
        Assert.All(wins, m => Assert.True(m.Played));
        var margins = wins.Select(m => Math.Abs(m.HomeGoals!.Value - m.AwayGoals!.Value)).ToList();
        Assert.Equal(margins.OrderByDescending(x => x), margins);
        // The dataset's record win: São Paulo 9-1 4 de Julho (2021 Copa do Brasil)
        Assert.Equal(8, margins[0]);
        Assert.Equal(9, Math.Max(wins[0].HomeGoals!.Value, wins[0].AwayGoals!.Value));
    }

    [Fact]
    public void Given_MatchDataLoaded_When_FilteringStatsBySeason_Then_OnlyThatSeasonIsAggregated()
    {
        // Given / When ("Compare the 2018 and 2019 seasons")
        var s2018 = _analytics.GetCompetitionStats("Serie A", 2018);
        var s2019 = _analytics.GetCompetitionStats("Serie A", 2019);

        // Then
        Assert.Equal(380, s2018.PlayedMatches);
        Assert.Equal(380, s2019.PlayedMatches);
        Assert.NotEqual(s2018.TotalGoals, s2019.TotalGoals);
    }

    [Fact]
    public void Given_UnplayedMatchesExist_When_RequestingAverages_Then_TheyAreExcludedFromGoalMath()
    {
        // Given (2022 has NA-score fixtures)

        // When
        var stats = _analytics.GetCompetitionStats("Serie A", 2022);

        // Then: played count excludes NA rows, and averages only cover played games
        Assert.True(stats.TotalMatches > stats.PlayedMatches);
        Assert.InRange(stats.AvgGoalsPerMatch, 1.5, 4.0);
    }
}
