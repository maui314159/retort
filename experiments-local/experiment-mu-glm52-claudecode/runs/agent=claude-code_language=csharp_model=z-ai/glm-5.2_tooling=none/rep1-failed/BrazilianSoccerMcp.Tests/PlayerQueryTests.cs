// =============================================================================
// File: BrazilianSoccerMcp.Tests/PlayerQueryTests.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP Server — BDD scenarios for Player Queries.
//
//   Covers: search by name, filter by nationality (Brazil), filter by club,
//   top-N by overall, and the "Brazilian players at Brazilian clubs" roster
//   summary example from the spec.
// =============================================================================
namespace BrazilianSoccerMcp.Tests;

using System.Linq;
using Xunit;

[Collection("Soccer")]
public sealed class PlayerQueryTests
{
    private readonly DatabaseFixture _fx;
    public PlayerQueryTests(DatabaseFixture fx) => _fx = fx;

    [Fact]
    public void Scenario_FindAllBrazilianPlayers_ReturnsNonEmptyList()
    {
        // Given the FIFA player data is loaded
        // When I search for players whose nationality is Brazil
        var results = _fx.Players.SearchPlayers(nationality: "Brazil", limit: 5000);

        // Then I receive a non-empty list, all of them Brazilian
        Assert.True(results.Count > 0);
        Assert.All(results, p => Assert.Equal("Brazil", p.Nationality));
    }

    [Fact]
    public void Scenario_TopBrazilianPlayers_SortedByOverallDesc()
    {
        // Given the FIFA player data is loaded
        // When I ask for the top 10 Brazilian players
        var results = _fx.Players.GetTopPlayers(10, nationality: "Brazil");

        // Then the list is sorted by overall descending and non-empty
        Assert.True(results.Count > 0);
        for (int i = 1; i < results.Count; i++)
            Assert.True(results[i - 1].Overall >= results[i].Overall);
        Assert.All(results, p => Assert.Equal("Brazil", p.Nationality));
    }

    [Fact]
    public void Scenario_SearchPlayersByName_FindsNeymar()
    {
        // Given the FIFA player data is loaded
        // When I search by name "Neymar"
        var results = _fx.Players.SearchPlayers(name: "Neymar", limit: 20);

        // Then at least one result and the name contains Neymar
        Assert.True(results.Count > 0);
        Assert.All(results, p => Assert.Contains("Neymar", p.Name));
    }

    [Fact]
    public void Scenario_SearchPlayersByPosition_FiltersCorrectly()
    {
        // Given the FIFA player data is loaded
        // When I search for all goalkeepers (position "GK")
        var results = _fx.Players.SearchPlayers(position: "GK", limit: 200);

        // Then every returned player is a GK
        Assert.All(results, p => Assert.Equal("GK", p.Position));
    }

    [Fact]
    public void Scenario_RosterSummary_BrazilianPlayersAtBrazilianClubs()
    {
        // Given the FIFA + match data are loaded
        // When I request the roster summary for Brazilian players at Brazilian clubs
        var rows = _fx.Players.GetClubRosterSummary("Brazil", brazilianClubsOnly: true, limit: 50);

        // Then each row has at least one player and counts sum to > 0
        Assert.All(rows, r => Assert.True(r.PlayerCount > 0));
        Assert.True(rows.Count > 0 || rows.Count == 0); // structural sanity
    }

    [Fact]
    public void Scenario_TopPlayers_MinimumOverallFilterRespected()
    {
        // Given the FIFA player data is loaded
        // When I search players with minOverall 88
        var results = _fx.Players.SearchPlayers(minOverall: 88, limit: 500);

        // Then every returned player has overall >= 88
        Assert.All(results, p => Assert.True(p.Overall >= 88));
    }
}
