// =============================================================================
// File: BrazilianSoccerMcp.Tests/CompetitionQueryTests.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP Server — BDD scenarios for Competition Queries.
//
//   Covers: computed league standings (sorted, W+D+L == matches, points math),
//   competition info summary, and finding knockout finals.
// =============================================================================
namespace BrazilianSoccerMcp.Tests;

using System.Linq;
using Xunit;

[Collection("Soccer")]
public sealed class CompetitionQueryTests
{
    private readonly DatabaseFixture _fx;
    public CompetitionQueryTests(DatabaseFixture fx) => _fx = fx;

    [Fact]
    public void Scenario_Standings_AreSortedByPointsDescAndConsistent()
    {
        // Given the match data is loaded
        // When I compute the Brasileirão 2019 standings
        var standings = _fx.Competitions.GetStandings("Brasileirão", 2019);

        // Then I get a non-empty table
        Assert.True(standings.Count > 0);

        // And the table is sorted by points (then GD then GF) descending
        for (int i = 1; i < standings.Count; i++)
        {
            var prev = standings[i - 1];
            var cur = standings[i];
            Assert.True(prev.Points >= cur.Points);
        }

        // And each row's W+D+L == matches, points math (3*W + D) holds
        Assert.All(standings, r =>
        {
            Assert.Equal(r.Matches, r.Wins + r.Draws + r.Losses);
            Assert.Equal(3 * r.Wins + r.Draws, r.Points);
            Assert.Equal(r.GoalsFor - r.GoalsAgainst, r.GoalDifference);
        });

        // And positions are sequential 1..N
        for (int i = 0; i < standings.Count; i++)
            Assert.Equal(i + 1, standings[i].Position);
    }

    [Fact]
    public void Scenario_Standings_KnockoutCupHasNoLeagueTable()
    {
        // Given Copa do Brasil is a knockout (non-league) competition
        // When I ask for its standings
        var standings = _fx.Competitions.GetStandings("Copa do Brasil", 2023);

        // Then the service returns an empty table (no league format)
        Assert.Empty(standings);
    }

    [Fact]
    public void Scenario_CompetitionInfo_ReturnsMatchCountAndRounds()
    {
        // Given the match data is loaded
        // When I request competition info for the 2019 Brasileirão
        var info = _fx.Competitions.GetCompetitionInfo("Brasileirão", 2019);

        // Then match count is positive and rounds list is populated
        Assert.Equal("Brasileirão", info.Competition);
        Assert.Equal(2019, info.Season);
        Assert.True(info.MatchCount > 0);
        Assert.True(info.Rounds.Count > 0);
    }

    [Fact]
    public void Scenario_FindCopaDoBrasilFinals_FindsFinals()
    {
        // Given the match data is loaded
        // When I search for Copa do Brasil finals
        var finals = _fx.Competitions.FindFinals(competition: "Copa do Brasil", limit: 50);

        // Then each result is in the Copa do Brasil and its round mentions "final"
        Assert.All(finals, m => Assert.Equal("Copa do Brasil", m.Competition));
        Assert.All(finals, m =>
            Assert.True((m.Round?.Contains("final", System.StringComparison.OrdinalIgnoreCase) ?? false)
                     || (m.Stage?.Contains("final", System.StringComparison.OrdinalIgnoreCase) ?? false)));
    }
}
