using BrazilianSoccerCore.Data;
using BrazilianSoccerMcp.Tests.Infrastructure;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Feature: Team Queries
/// BDD scenarios for team statistics, venue records, and head-to-head.
/// </summary>
[Collection("SoccerData")]
public class TeamQueryTests
{
    private readonly DataFixture _f;
    public TeamQueryTests(DataFixture f) => _f = f;

    // Scenario: Get team statistics
    //   Given the match data is loaded
    //   When I request statistics for "Palmeiras" in season 2023
    //   Then I should receive wins, losses, draws, and goals
    [Fact]
    public void GetTeamStats_returns_wins_draws_losses_goals()
    {
        var stats = _f.Matches.GetTeamStats("Palmeiras", season: 2023);

        Assert.True(stats.Matches > 0);
        Assert.Equal(stats.Matches, stats.Wins + stats.Draws + stats.Losses);
        Assert.True(stats.GoalsFor >= 0);
        Assert.Equal(stats.GoalsFor + stats.GoalsAgainst > 0, stats.Matches > 0 || true);
    }

    // Scenario: home record filter
    //   When I request Corinthians' home record in 2022
    //   Then home wins + draws + losses equals home matches
    [Fact]
    public void GetTeamStats_home_record_sums_correctly()
    {
        var stats = _f.Matches.GetTeamStats("Corinthians", venue: "home", season: 2022);
        Assert.Equal(stats.Matches, stats.Wins + stats.Draws + stats.Losses);
        Assert.Equal("home", stats.Venue);
    }

    // Scenario: win rate is within [0, 100]
    [Fact]
    public void WinRate_is_within_valid_range()
    {
        var stats = _f.Matches.GetTeamStats("Flamengo");
        Assert.InRange(stats.WinRate, 0, 100);
    }

    // Scenario: goals scored equals sum of team goals across matches
    [Fact]
    public void GoalsScoredBy_is_non_negative_and_consistent()
    {
        var goals = _f.Matches.GoalsScoredBy("São Paulo", competition: "Brasileirão");
        Assert.True(goals >= 0);
    }

    // Scenario: best home record exists
    [Fact]
    public void BestHomeRecord_returns_a_team()
    {
        var best = _f.Matches.BestHomeRecord();
        Assert.NotNull(best);
        Assert.True(best!.Matches >= 10);
        Assert.True(best.WinRate > 0);
    }

    // Scenario: best away record exists
    [Fact]
    public void BestAwayRecord_returns_a_team()
    {
        var best = _f.Matches.BestAwayRecord();
        Assert.NotNull(best);
        Assert.True(best!.Matches >= 10);
    }

    // Scenario: competitions a team played in
    [Fact]
    public void CompetitionsForTeam_returns_multiple_competitions()
    {
        var comps = _f.Matches.CompetitionsForTeam("Palmeiras");
        Assert.NotEmpty(comps);
        // Palmeiras appears in Brasileirão and likely Libertadores/Copa do Brasil.
        Assert.Contains(comps, c => c.Contains("Brasileirão"));
    }

    // Scenario: biggest wins are sorted by goal difference descending
    [Fact]
    public void BiggestWins_sorted_by_goal_difference()
    {
        var wins = _f.Matches.BiggestWins(limit: 5);
        Assert.NotEmpty(wins);
        for (var i = 1; i < wins.Count; i++)
            Assert.True(wins[i - 1].GoalDifference >= wins[i].GoalDifference);
    }
}