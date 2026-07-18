// ============================================================================
// BrazilianSoccerMcp.Tests - BddTeamQueries.cs
//
// Context block:
//   BDD tests for team statistics and head-to-head (TASK.md "Team Queries").
//   Validates win/loss/draw arithmetic, venue filtering, and H2H totals.
// ============================================================================

using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

public class BddTeamQueries : IClassFixture<DataFixture>
{
    private readonly DataFixture _f;
    public BddTeamQueries(DataFixture f) => _f = f;

    // Scenario: Get team statistics for a season
    [Fact]
    public void Given_match_data_when_requesting_palmeiras_stats_2022_then_returns_wins_losses_draws_goals()
    {
        var stats = _f.Service.GetTeamStatistics("Palmeiras", season: 2022,
            competition: Competition.Brasileirao);

        // Then I should receive wins, losses, draws, and goals
        Assert.True(stats.Matches > 0, "Palmeiras should have 2022 matches");
        Assert.Equal(stats.Matches, stats.Wins + stats.Draws + stats.Losses);
        Assert.True(stats.GoalsFor >= stats.Wins, "GF should be at least as many as wins");
        Assert.True(stats.WinRate >= 0 && stats.WinRate <= 100);
    }

    // Scenario: Home record only counts home matches
    [Fact]
    public void Given_match_data_when_requesting_home_venue_then_only_home_matches_counted()
    {
        var home = _f.Service.GetTeamStatistics("Flamengo", season: 2022,
            competition: Competition.Brasileirao, venue: Venue.Home);
        var away = _f.Service.GetTeamStatistics("Flamengo", season: 2022,
            competition: Competition.Brasileirao, venue: Venue.Away);
        var either = _f.Service.GetTeamStatistics("Flamengo", season: 2022,
            competition: Competition.Brasileirao, venue: Venue.Either);

        Assert.Equal(either.Matches, home.Matches + away.Matches);
        Assert.True(home.Matches > 0 && away.Matches > 0);
    }

    // Scenario: Compare Palmeiras and Santos head-to-head
    [Fact]
    public void Given_match_data_when_head_to_head_palmeiras_santos_then_totals_match()
    {
        var h2h = _f.Service.GetHeadToHead("Palmeiras", "Santos");
        Assert.True(h2h.Total > 0, "expected Palmeiras-Santos fixtures");
        Assert.Equal(h2h.Total, h2h.WinsA + h2h.WinsB + h2h.Draws);
        // WinsA + WinsB + Draws should equal the count of *scored* H2H matches
        var scored = h2h.Matches.Count(m => m.HasScore);
        Assert.Equal(scored, h2h.WinsA + h2h.WinsB + h2h.Draws);
    }

    // Scenario: Head-to-head only involves the two named teams
    [Fact]
    public void Given_head_to_head_when_inspecting_matches_then_both_teams_appear()
    {
        var h2h = _f.Service.GetHeadToHead("Flamengo", "Fluminense");
        Assert.All(h2h.Matches, m =>
        {
            bool a = TeamNameNormalizer.TeamMatches(m.HomeTeam, "Flamengo") ||
                     TeamNameNormalizer.TeamMatches(m.AwayTeam, "Flamengo");
            bool b = TeamNameNormalizer.TeamMatches(m.HomeTeam, "Fluminense") ||
                     TeamNameNormalizer.TeamMatches(m.AwayTeam, "Fluminense");
            Assert.True(a, "Flamengo should be in the fixture");
            Assert.True(b, "Fluminense should be in the fixture");
        });
    }
}
