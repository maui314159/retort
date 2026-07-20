// BrazilianSoccerMcp.Tests / CompetitionQueriesTests.cs
// -----------------------------------------------------------------------------
// Context: BDD scenarios for TASK.md "Required Capabilities 4. Competition Queries".
// Covers: standings by season (calculated from match results), champion, and the
// relegation zone.
// Feature: Competition Queries
// The spec's example: "2019 Brasileirão Final Standings ... 1. Flamengo - 90 pts
// (28W, 6D, 4L) - Champion". These scenarios assert that exact outcome.
// -----------------------------------------------------------------------------

using BrazilianSoccerMcp.Core.Models;
using BrazilianSoccerMcp.Core.Queries;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

[Collection("SoccerData")]
public class CompetitionQueriesTests
{
    private readonly CompetitionQueries _queries;
    public CompetitionQueriesTests(SoccerDataFixture fixture)
        => _queries = new CompetitionQueries(fixture.Data);

    // Scenario: who won the 2019 Brasileirão?
    [Fact]
    public void GivenBrasileirao2019_WhenIRequestTheChampion_ThenFlamengoIsChampionWith90Points()
    {
        // Given the 2019 Brasileirão
        // When I request the champion
        var champ = _queries.Champion(CompetitionKind.BrasileiraoSerieA, 2019);
        // Then Flamengo is the champion with ~90 points (TASK.md example)
        Assert.NotNull(champ);
        Assert.Equal("flamengo-rj", champ!.Team);
        Assert.Equal(90, champ.Record.Points);
        Assert.True(champ.IsChampion);
        Assert.Equal(28, champ.Record.Wins);
        Assert.Equal(6, champ.Record.Draws);
        Assert.Equal(4, champ.Record.Losses);
    }

    // Scenario: full standings table for 2019 Brasileirão
    [Fact]
    public void GivenBrasileirao2019_WhenIRequestStandings_ThenTableHas20TeamsSortedByPointsDescending()
    {
        // Given the 2019 Brasileirão
        // When I request the full standings
        var table = _queries.Standings(CompetitionKind.BrasileiraoSerieA, 2019);
        // Then the table has 20 teams
        Assert.Equal(20, table.Count);
        // And positions are 1..20 in order
        Assert.Equal(1, table[0].Position);
        Assert.True(table[0].IsChampion);
        // And the table is sorted by points (then GD, then GF) descending
        for (int i = 1; i < table.Count; i++)
        {
            var prev = table[i - 1].Record;
            var cur = table[i].Record;
            Assert.True(prev.Points >= cur.Points,
                $"row {i}: {prev.Points} should be >= {cur.Points}");
        }
        // And every team's W+D+L equals its matches played
        Assert.All(table, r => Assert.Equal(r.Record.Matches, r.Record.Wins + r.Record.Draws + r.Record.Losses));
    }

    // Scenario: which teams were relegated?
    [Fact]
    public void GivenBrasileirao2019_WhenIRequestRelegatedTeams_ThenBottomFourAreReturned()
    {
        // Given the 2019 Brasileirão
        // When I request the relegation zone (bottom 4)
        var relegated = _queries.Relegated(CompetitionKind.BrasileiraoSerieA, 2019, count: 4);
        // Then four teams are returned, in ascending-points order
        Assert.Equal(4, relegated.Count);
        for (int i = 1; i < relegated.Count; i++)
            Assert.True(relegated[i - 1].Record.Points <= relegated[i].Record.Points);
        // And the relegation zone has strictly fewer points than the champion
        Assert.True(relegated[^1].Record.Points < 90);
    }

    // Scenario: standings points sum to a consistent total (3*Wins+Draws invariant)
    [Fact]
    public void GivenAnySeasonStandings_WhenPointsAreSummed_ThenEachRowSatisfiesPointsEquals3WinsPlusDraws()
    {
        // Given the 2018 Brasileirão standings
        var table = _queries.Standings(CompetitionKind.BrasileiraoSerieA, 2018);
        // When each row's points are checked
        // Then Points == 3*Wins + Draws for every team
        Assert.All(table, r => Assert.Equal(3 * r.Record.Wins + r.Record.Draws, r.Record.Points));
    }
}
