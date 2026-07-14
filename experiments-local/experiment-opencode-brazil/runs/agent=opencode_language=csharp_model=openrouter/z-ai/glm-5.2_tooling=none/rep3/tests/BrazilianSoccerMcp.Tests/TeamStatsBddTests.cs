using BrazilianSoccerMcp.Services;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// BDD-style tests for team-level statistics.
/// Maps to the "Get team statistics" scenario in TASK.md.
/// </summary>
[Collection("DataCollection")]
public class TeamStatsBddTests
{
    private readonly DataFixture _fixture;

    public TeamStatsBddTests(DataFixture fixture) => _fixture = fixture;

    [Fact]
    public void Get_team_statistics_returns_wins_losses_draws_and_goals()
    {
        // Given the match data is loaded
        var svc = new TeamService(_fixture.Repository);

        // When I request statistics for "Palmeiras" in season 2023
        var stats = svc.GetStats("Palmeiras", season: 2023);

        // Then I should receive wins, losses, draws, and goals
        Assert.True(stats.Matches > 0, "Palmeiras should have played matches in 2023");
        Assert.True(stats.Wins + stats.Draws + stats.Losses == stats.Matches,
            "wins + draws + losses must equal total matches");
        Assert.True(stats.GoalsFor >= 0);
        Assert.True(stats.GoalsAgainst >= 0);
        Assert.True(stats.WinRatePercent >= 0 && stats.WinRatePercent <= 100);
    }

    [Fact]
    public void Home_record_filters_to_home_matches_only()
    {
        // Given the match data is loaded
        var svc = new TeamService(_fixture.Repository);

        // When I request Palmeiras home record in 2023
        var home = svc.GetStats("Palmeiras", season: 2023, venue: "home");

        // Then all matches counted are home matches
        Assert.Equal(home.Matches, home.HomeMatches);
        Assert.Equal(0, home.AwayMatches);
    }

    [Fact]
    public void Away_record_filters_to_away_matches_only()
    {
        var svc = new TeamService(_fixture.Repository);
        var away = svc.GetStats("Palmeiras", season: 2023, venue: "away");
        Assert.Equal(0, away.HomeMatches);
        Assert.Equal(away.Matches, away.AwayMatches);
    }

    [Fact]
    public void Search_teams_returns_canonical_spellings()
    {
        var svc = new TeamService(_fixture.Repository);
        var teams = svc.SearchTeams("Flamengo");
        Assert.Contains("Flamengo", teams);
    }
}
