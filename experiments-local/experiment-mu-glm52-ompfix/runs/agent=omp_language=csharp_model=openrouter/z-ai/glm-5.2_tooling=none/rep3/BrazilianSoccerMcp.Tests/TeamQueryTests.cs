// =============================================================================
// BrazilianSoccerMcp.Tests - Team & Head-to-Head BDD Tests
// -----------------------------------------------------------------------------
// Feature: Team Queries
//   Verify team statistics (W/D/L, goals), home/away venue filters, and
//   head-to-head comparisons aggregate correctly from match results.
// =============================================================================

using BrazilianSoccerMcp.Data;

namespace BrazilianSoccerMcp.Tests;

[Trait("Feature", "Team Queries")]
public class TeamQueryTests : TestBase
{
    // Scenario: Get team statistics for a season
    //   Given the match data is loaded
    //   When I request statistics for "Palmeiras" in season 2022
    //   Then I should receive wins, losses, draws and goals
    [Fact]
    public void TeamStatistics_ForSeason_ReturnsWinsDrawsLossesGoals()
    {
        var key = Repo.ResolveTeamKey("Palmeiras");
        var s = Repo.GetTeamStatistics(key, season: 2022);

        Assert.True(s.Matches > 0, "Palmeiras should have 2022 matches");
        Assert.True(s.Wins + s.Draws + s.Losses == s.Matches, "W+D+L must equal matches");
        Assert.True(s.GoalsFor >= 0 && s.GoalsAgainst >= 0);
        Assert.Equal(s.Wins * 3 + s.Draws, s.Points);
    }

    // Scenario: Home record filters to home matches only
    //   Given the match data is loaded
    //   When I request Corinthians home record for 2022 (all competitions)
    //   Then every counted match is a home match for Corinthians
    [Fact]
    public void TeamStatistics_HomeVenue_OnlyCountsHomeMatches()
    {
        var key = Repo.ResolveTeamKey("Corinthians");
        var home = Repo.GetTeamStatistics(key, season: 2022, venue: "home");
        var total = Repo.GetTeamStatistics(key, season: 2022, venue: "any");

        Assert.True(home.Matches > 0);
        Assert.True(home.Matches <= total.Matches);
        // Home is a strict subset of all matches: a team also plays away.
        Assert.True(home.Matches < total.Matches, "home must be fewer than total (away games exist)");
        // Internally consistent: wins + draws + losses equals matches.
        Assert.Equal(home.Matches, home.Wins + home.Draws + home.Losses);
    }

    // Scenario: Head-to-head tally is internally consistent
    //   Given the match data is loaded
    //   When I compare Palmeiras and Santos head-to-head
    //   Then the sum of wins + draws equals the match count
    [Fact]
    public void HeadToHead_WinsPlusDraws_EqualsMatchCount()
    {
        var h2h = Repo.GetHeadToHead("Palmeiras", "Santos");
        Assert.NotEmpty(h2h.Matches);
        Assert.Equal(h2h.Matches.Count, h2h.Team1Wins + h2h.Team2Wins + h2h.Draws);
    }

    // Scenario: Head-to-head lists fixtures in both directions
    //   Given the match data is loaded
    //   When I compare Flamengo and Fluminense
    //   Then matches include both Flamengo-home and Fluminense-home fixtures
    [Fact]
    public void HeadToHead_IncludesBothHomeDirections()
    {
        var h2h = Repo.GetHeadToHead("Flamengo", "Fluminense");
        Assert.NotEmpty(h2h.Matches);
        var flamengoHome = h2h.Matches.Any(m => m.HomeKey == "flamengo");
        var fluHome = h2h.Matches.Any(m => m.HomeKey == "fluminense");
        Assert.True(flamengoHome && fluHome, "expected fixtures in both home directions");
    }

    // Scenario: Team competitions span multiple tournaments
    //   Given the match data is loaded
    //   When I list competitions Palmeiras has played in
    //   Then the list includes at least Brasileirão Série A
    [Fact]
    public void TeamCompetitions_Palmeiras_IncludesBrasileirao()
    {
        var comps = Repo.TeamCompetitions("Palmeiras");
        Assert.Contains("Brasileirão Série A", comps);
        Assert.True(comps.Count >= 2, "Palmeiras should appear in >=2 competitions");
    }
}
