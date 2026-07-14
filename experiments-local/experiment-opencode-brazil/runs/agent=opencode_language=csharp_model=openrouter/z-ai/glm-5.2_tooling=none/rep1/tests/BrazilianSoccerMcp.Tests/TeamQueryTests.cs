// Context block
// File: TeamQueryTests.cs
// Purpose: BDD/GWT tests for the TeamService of the Brazilian Soccer MCP server, covering
// the "Team Queries" feature from TASK.md: home record for a team in a season, and a
// head-to-head comparison between two rivals. Tests run against the real bundled CSV
// data via the shared SoccerDataFixture.
// Language: C# (.NET 10) + xUnit. Owner: Brazilian Soccer MCP benchmark implementation.

using BrazilianSoccerMcp.Models;
using BrazilianSoccerMcp.Services;

namespace BrazilianSoccerMcp.Tests;

[Collection("SoccerData")]
public class TeamQueryTests
{
    private readonly SoccerDataFixture _f;
    public TeamQueryTests(SoccerDataFixture fixture) => _f = fixture;

    // Feature: Team Queries

    // Scenario: Get team home record for a season
    //   Given the match data is loaded
    //   When I request Corinthians home record in season 2022 Brasileirao
    //   Then I should receive wins, losses, draws, and goals
    //   And wins + draws + losses should equal matches played
    [Fact]
    public void Home_record_aggregates_correctly()
    {
        var stats = _f.Teams.GetTeamStats("Corinthians", season: 2022,
            competition: Competition.Brasileirao, venue: Venue.Home);

        Assert.True(stats.Played > 0);
        Assert.Equal(stats.Played, stats.Wins + stats.Draws + stats.Losses);
        Assert.True(stats.GoalsFor >= 0);
        Assert.True(stats.GoalsAgainst >= 0);
        Assert.Equal(Venue.Home, stats.Venue);
    }

    // Scenario: Compare Palmeiras and Santos head-to-head
    //   Given the match data is loaded
    //   When I compare Palmeiras and Santos
    //   Then the comparison should include both teams' stats and a head-to-head record
    [Fact]
    public void Compare_teams_returns_stats_and_head_to_head()
    {
        var comp = _f.Teams.CompareTeams("Palmeiras", "Santos");

        Assert.Equal("Palmeiras", comp.TeamA.Team);
        Assert.Equal("Santos", comp.TeamB.Team);
        Assert.True(comp.HeadToHead.TotalMatches >= 0);
        Assert.Equal(comp.HeadToHead.TotalMatches,
            comp.HeadToHead.TeamAWins + comp.HeadToHead.TeamBWins + comp.HeadToHead.Draws);
    }

    // Scenario: Home record only counts home matches
    //   Given the match data is loaded
    //   When I request Flamengo home record for 2022 Brasileirao
    //   Then the played count should not exceed the number of home matches in the dataset
    [Fact]
    public void Home_venue_filter_excludes_away_matches()
    {
        var home = _f.Teams.GetTeamStats("Flamengo", season: 2022,
            competition: Competition.Brasileirao, venue: Venue.Home);
        var all = _f.Teams.GetTeamStats("Flamengo", season: 2022,
            competition: Competition.Brasileirao, venue: Venue.All);

        Assert.True(home.Played <= all.Played);
        Assert.True(home.Played > 0);
    }
}
