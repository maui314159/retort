// =============================================================================
// BrazilianSoccerMcp.Tests - Player Query BDD Tests
// -----------------------------------------------------------------------------
// Feature: Player Queries
//   Verify the FIFA player database can be searched by name, nationality, club
//   and position, and that Brazilian players are filterable.
// =============================================================================

using BrazilianSoccerMcp.Data;

namespace BrazilianSoccerMcp.Tests;

[Trait("Feature", "Player Queries")]
public class PlayerQueryTests : TestBase
{
    // Scenario: Find a player by name
    //   Given the FIFA player data is loaded
    //   When I search for "Neymar"
    //   Then I should receive at least one player whose name contains Neymar
    [Fact]
    public void SearchPlayers_ByName_FindsPlayer()
    {
        var ps = Repo.SearchPlayers(name: "Neymar").ToList();
        Assert.NotEmpty(ps);
        Assert.All(ps, p => Assert.Contains("Neymar", p.Name, StringComparison.OrdinalIgnoreCase));
        Assert.True(ps.First().Overall >= 85, "Neymar should be highly rated");
    }

    // Scenario: Filter by nationality (Brazil)
    //   Given the FIFA player data is loaded
    //   When I search for Brazilian players
    //   Then every result has Nationality "Brazil"
    [Fact]
    public void SearchPlayers_ByBrazilianNationality_ReturnsBrazilians()
    {
        var ps = Repo.SearchPlayers(nationality: "Brazil").OrderByDescending(p => p.Overall).Take(50).ToList();
        Assert.NotEmpty(ps);
        Assert.All(ps, p => Assert.Equal("Brazil", p.Nationality, StringComparer.OrdinalIgnoreCase));
        // Should be sorted by overall descending
        Assert.Equal(ps.OrderByDescending(p => p.Overall), ps);
    }

    // Scenario: Filter by club
    //   Given the FIFA player data is loaded
    //   When I search for players at Fluminense (a Brazilian club in the dataset)
    //   Then every result's club contains Fluminense
    [Fact]
    public void SearchPlayers_ByClub_FiltersClub()
    {
        var ps = Repo.SearchPlayers(club: "Fluminense").ToList();
        Assert.NotEmpty(ps);
        Assert.All(ps, p => Assert.Contains("Fluminense", p.Club, StringComparison.OrdinalIgnoreCase));
    }

    // Scenario: Brazilian players at Brazilian clubs summary
    //   Given the FIFA player data is loaded
    //   When I request the Brazilian clubs summary
    //   Then at least one Brazilian club with Brazilian players is returned
    [Fact]
    public void BrazilianClubsSummary_ReturnsBrazilianClubs()
    {
        var rows = Repo.BrazilianClubsSummary();
        Assert.NotEmpty(rows);
        Assert.All(rows, r => Assert.True(r.Count > 0));
        Assert.True(rows.First().Count >= rows.Last().Count, "should be sorted by count desc");
    }

    // Scenario: Top-rated Brazilian players
    //   Given the FIFA player data is loaded
    //   When I search for Brazilian players sorted by overall
    //   Then the highest-rated Brazilian player has overall >= 88
    [Fact]
    public void SearchPlayers_TopBrazilians_HighOverall()
    {
        var top = Repo.SearchPlayers(nationality: "Brazil").OrderByDescending(p => p.Overall).First();
        Assert.True(top.Overall >= 88, $"top Brazilian overall was {top.Overall}");
    }
}
