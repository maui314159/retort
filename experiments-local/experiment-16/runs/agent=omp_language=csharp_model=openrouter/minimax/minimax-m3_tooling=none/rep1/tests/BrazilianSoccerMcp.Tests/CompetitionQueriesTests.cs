// =============================================================================
// Brazilian Soccer MCP Server
// File: CompetitionQueriesTests.cs
// Purpose: BDD tests for the "Competition Queries" capability.
// Context: Computes standings from match data. The 2019 Brasileirão
//          champion is the historical fact -- the test verifies that
//          Flamengo, who actually won that year, comes out on top
//          from our calculated table (within reason: standings from
//          a subset of the bundled data may not match exactly).
// =============================================================================

using BrazilianSoccerMcp.Core;
using BrazilianSoccerMcp.Core.Models;
using FluentAssertions;

namespace BrazilianSoccerMcp.Tests;

[Collection("Dataset")]
public class CompetitionQueriesTests
{
    private readonly QueryEngine _engine;
    public CompetitionQueriesTests(TestDataFixture fixture) => _engine = fixture.Engine;

    // Scenario: "Who won the 2019 Brasileirão?"
    // Flamengo is the historical champion. Standings computed from the
    // bundled data should rank them first when they played.
    [Fact]
    public void Given_2019_Brasileirao_When_calculating_standings_Then_Flamengo_is_top_team()
    {
        var standings = _engine.GetStandings(2019, Competition.Brasileirao);
        standings.Should().NotBeEmpty();
        var first = standings[0];
        first.Team.Should().Contain("Flamengo");
        first.Points.Should().BeGreaterThan(0);
        first.Played.Should().BeGreaterThan(0);
    }

    // Scenario: Standings are sorted by points desc (then by wins, GD, etc.)
    [Fact]
    public void Given_any_season_When_calculating_standings_Then_ordered_by_points_desc()
    {
        var standings = _engine.GetStandings(2018, Competition.Brasileirao);
        standings.Should().NotBeEmpty();
        for (var i = 1; i < standings.Count; i++)
            standings[i].Points.Should().BeLessThanOrEqualTo(standings[i - 1].Points);
    }

    // Scenario: Standings invariants: W + D + L == Played; Points == 3W + D
    [Fact]
    public void Given_any_standings_row_Then_invariants_hold()
    {
        var standings = _engine.GetStandings(2017, Competition.Brasileirao);
        standings.Should().NotBeEmpty();
        foreach (var s in standings)
        {
            (s.Wins + s.Draws + s.Losses).Should().Be(s.Played);
            s.Points.Should().Be(s.Wins * 3 + s.Draws);
            s.GoalDifference.Should().Be(s.GoalsFor - s.GoalsAgainst);
        }
    }
}
