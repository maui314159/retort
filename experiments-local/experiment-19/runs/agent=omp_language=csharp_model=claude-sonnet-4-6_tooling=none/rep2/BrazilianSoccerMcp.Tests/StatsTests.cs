using BrazilianSoccerMcp.Models;
using BrazilianSoccerMcp.Services;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// BDD scenarios for statistical queries.
/// Feature: Statistical Analysis and Team Stats
/// </summary>
[Collection("Data")]
public sealed class StatsTests(DataFixture fixture)
{
    private DataRepository Repo => fixture.Repository;

    // Scenario: Get team statistics
    //   Given the match data is loaded
    //   When I request statistics for "Palmeiras" in season "2023"
    //   Then I should receive wins, losses, draws, and goals
    [Fact]
    public void GivenMatchData_WhenGetStatsForPalmeiras2023_ThenWinsDrawsLossesGoalsReturned()
    {
        var stats = Repo.GetTeamStats("Palmeiras", season: 2023);

        Assert.True(stats.Matches > 0, "Palmeiras should have matches in 2023");
        Assert.True(stats.Wins >= 0);
        Assert.True(stats.Draws >= 0);
        Assert.True(stats.Losses >= 0);
        Assert.Equal(stats.Matches, stats.Wins + stats.Draws + stats.Losses);
        Assert.True(stats.GoalsFor >= 0);
        Assert.True(stats.GoalsAgainst >= 0);
    }

    // Scenario: Points calculation
    [Fact]
    public void GivenTeamStats_WhenPointsCalculated_ThenCorrectFormula()
    {
        var stats = Repo.GetTeamStats("Flamengo", season: 2022);

        // Points = Wins * 3 + Draws
        Assert.Equal(stats.Wins * 3 + stats.Draws, stats.Points);
    }

    // Scenario: All matches accounted for
    [Fact]
    public void GivenTeamStats_WhenWinDrawLoss_ThenSumEqualsMatches()
    {
        var stats = Repo.GetTeamStats("Corinthians");
        Assert.Equal(stats.Matches, stats.Wins + stats.Draws + stats.Losses);
    }

    // Scenario: Win rate in range 0-100
    [Fact]
    public void GivenTeamStats_WhenWinRateCalculated_ThenBetween0And100()
    {
        var stats = Repo.GetTeamStats("Grêmio");
        Assert.InRange(stats.WinRate, 0.0, 100.0);
    }

    // Scenario: Get standings for a season
    //   Given the match data is loaded
    //   When I request standings for Brasileirao 2022
    //   Then I should get a ranked list with at least 10 teams
    [Fact]
    public void GivenMatchData_WhenGetStandingsBrasileirao2022_ThenRankedTeamsReturned()
    {
        var standings = Repo.GetStandings(2022, Competition.Brasileirao);

        Assert.NotEmpty(standings);
        Assert.True(standings.Count >= 10, $"Expected at least 10 teams, got {standings.Count}");

        // Verify descending points order
        for (int i = 1; i < standings.Count; i++)
            Assert.True(standings[i - 1].Stats.Points >= standings[i].Stats.Points,
                "Standings should be in descending points order");
    }

    // Scenario: Historic Brasileirao standings
    [Fact]
    public void GivenMatchData_WhenGetStandingsHistorico2019_ThenFlamengoAtTop()
    {
        var standings = Repo.GetStandings(2019, Competition.HistoricoBrasileiro);

        Assert.NotEmpty(standings);
        // Flamengo won 2019 with record points - should be top or near top
        var top3 = standings.Take(3).Select(s => s.Team).ToList();
        Assert.True(top3.Any(t => t.Contains("Flamengo", StringComparison.OrdinalIgnoreCase)),
            $"Flamengo should be in top 3 of 2019. Got: {string.Join(", ", top3)}");
    }

    // Scenario: Competition stats - average goals
    [Fact]
    public void GivenMatchData_WhenGetCompetitionStats_ThenAvgGoalsIsPositive()
    {
        var (avgGoals, homeWinRate, drawRate, awayWinRate, total) =
            Repo.GetCompetitionStats(Competition.Brasileirao);

        Assert.True(total > 0);
        Assert.True(avgGoals > 0, "Average goals should be positive");
        Assert.True(avgGoals < 10, "Average goals should be reasonable (< 10)");

        // Rates should sum to ~100%
        var sum = homeWinRate + drawRate + awayWinRate;
        Assert.True(Math.Abs(sum - 100.0) < 1.0,
            $"Win/draw/away rates should sum to ~100%, got {sum:F1}%");
    }

    // Scenario: Head-to-head is symmetric
    [Fact]
    public void GivenMatchData_WhenHeadToHead_ThenSameMatchCountBothDirections()
    {
        var flaVsFlu = Repo.SearchMatches(team: "Flamengo", opponent: "Fluminense", limit: 200);
        var fluVsFla = Repo.SearchMatches(team: "Fluminense", opponent: "Flamengo", limit: 200);

        // Same matches regardless of which team is named first
        Assert.Equal(flaVsFlu.Count, fluVsFla.Count);
    }

    // Scenario: Biggest wins are not draws
    [Fact]
    public void GivenMatchData_WhenGetBiggestWins_ThenNoneAreDrwas()
    {
        var wins = Repo.GetBiggestWins(limit: 20);

        Assert.NotEmpty(wins);
        Assert.All(wins, m => Assert.False(m.IsDraw, $"Draw listed as biggest win: {m.HomeGoals}-{m.AwayGoals}"));
        Assert.All(wins, m => Assert.True(m.GoalDifference > 0));
    }

    // Scenario: Team without data returns zero-record stats (not exception)
    [Fact]
    public void GivenMatchData_WhenTeamNotFound_ThenReturnsZeroStats()
    {
        var stats = Repo.GetTeamStats("NonExistentTeamXYZ123");
        Assert.Equal(0, stats.Matches);
        Assert.Equal(0, stats.Points);
    }

    // Scenario: Cross-dataset team stats (team appears in multiple competitions)
    [Fact]
    public void GivenMatchData_WhenGetStatsAcrossAllCompetitions_ThenHigherCount()
    {
        var allStats = Repo.GetTeamStats("Flamengo");
        var brasilStats = Repo.GetTeamStats("Flamengo", competition: Competition.Brasileirao);

        // Without filter should include more matches
        Assert.True(allStats.Matches >= brasilStats.Matches,
            "All-competition stats should be >= single competition");
    }
}
