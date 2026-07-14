// Context block
// File: CompetitionQueryTests.cs
// Purpose: BDD/GWT tests for the CompetitionService of the Brazilian Soccer MCP server,
// covering the "Competition Queries" feature from TASK.md: compute Brasileirão standings
// for a season from match results and identify the champion. Tests run against the real
// bundled CSV data via the shared SoccerDataFixture. The 2019 season is used because
// Flamengo won it, which lets us assert a concrete known champion.
// Language: C# (.NET 10) + xUnit. Owner: Brazilian Soccer MCP benchmark implementation.

using BrazilianSoccerMcp.Services;

namespace BrazilianSoccerMcp.Tests;

[Collection("SoccerData")]
public class CompetitionQueryTests
{
    private readonly SoccerDataFixture _f;
    public CompetitionQueryTests(SoccerDataFixture fixture) => _f = fixture;

    // Feature: Competition Queries

    // Scenario: Compute standings for a season
    //   Given the Brasileirao match data is loaded
    //   When I request standings for season 2019
    //   Then I should receive a non-empty standings table ordered by points
    [Fact]
    public void Standings_for_2019_are_ordered_by_points()
    {
        var standings = _f.Competitions.GetBrasileiraoStandings(2019, topN: 5);

        Assert.NotEmpty(standings);
        for (int i = 1; i < standings.Count; i++)
        {
            Assert.True(standings[i - 1].Points >= standings[i].Points,
                $"row {i - 1} points {standings[i - 1].Points} >= row {i} points {standings[i].Points}");
        }
        Assert.Equal(1, standings[0].Position);
    }

    // Scenario: Who won the 2019 Brasileirao
    //   Given the Brasileirao match data is loaded
    //   When I request the champion for season 2019
    //   Then the champion should be Flamengo
    [Fact]
    public void Champion_of_2019_is_flamengo()
    {
        var champ = _f.Competitions.GetChampion(2019);

        Assert.NotNull(champ);
        Assert.Equal("Flamengo", champ!.Team);
    }

    // Scenario: Standings totals are internally consistent
    //   Given the Brasileirao match data is loaded
    //   When I compute standings for season 2018
    //   Then each row's wins + draws + losses should equal played
    [Fact]
    public void Standings_row_totals_match_played()
    {
        var standings = _f.Competitions.GetBrasileiraoStandings(2018, topN: 20);

        Assert.NotEmpty(standings);
        Assert.All(standings, r => Assert.Equal(r.Played, r.Wins + r.Draws + r.Losses));
    }
}
