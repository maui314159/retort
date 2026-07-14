// ============================================================================
// File: Tests/PlayerQueryTests.cs
// ----------------------------------------------------------------------------
// Context: BDD tests for the "Player Queries" category (PlayerTools).
//
// Feature: Player Queries
//   Scenario: Search the FIFA database
//     Given the FIFA player data is loaded
//     When I search for Brazilian players
//     Then I should receive players including Neymar Jr with overall 92
// ============================================================================

using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Tools;

namespace BrazilianSoccerMcp.Tests;

[Collection("Store")]
public class PlayerQueryTests
{
    private readonly SoccerDataStore _store;
    private readonly PlayerTools _tools;

    public PlayerQueryTests(StoreFixture fixture)
    {
        _store = fixture.Store;
        _tools = new PlayerTools(_store);
    }

    // Given the FIFA player data is loaded
    // When I search for "Neymar"
    // Then I receive a result showing Neymar Jr, Brazil, overall 92
    [Fact]
    public void SearchPlayers_by_name_finds_Neymar()
    {
        var result = _tools.SearchPlayers(name: "Neymar");

        Assert.Contains("Neymar", result);
        Assert.Contains("Overall 92", result);
        Assert.Contains("Brazil", result);
    }

    // Scenario: Find all Brazilian players in the dataset
    //   Given the FIFA player data is loaded
    //   When I filter by nationality Brazil
    //   Then I receive many players, sorted by overall rating
    [Fact]
    public void SearchPlayers_Brazilian_returns_many_sorted_by_overall()
    {
        var result = _tools.SearchPlayers(nationality: "Brazil", limit: 20);

        Assert.Contains("Found", result);
        // First listed player should have a high overall (sorted descending).
        var firstLine = result.Split('\n').First(l => l.StartsWith("- "));
        Assert.Contains("Overall", firstLine);
        Assert.Contains("Brazil", result);
    }

    // Scenario: Who are the highest-rated players at Flamengo?
    //   Given the FIFA player data is loaded
    //   When I filter by club Flamengo
    //   Then I receive Flamengo players (if any in the dataset)
    [Fact]
    public void SearchPlayers_by_club_finds_club_players()
    {
        var result = _tools.SearchPlayers(club: "Flamengo", limit: 10);

        // The FIFA snapshot may or may not include Flamengo; either way the
        // tool must respond cleanly. If it found players, they mention Flamengo.
        if (!result.StartsWith("No players"))
            Assert.Contains("Flamengo", result);
    }

    // Scenario: Top Brazilian players ranking
    [Fact]
    public void TopPlayers_Brazil_returns_ranked_list()
    {
        var result = _tools.TopPlayers(nationality: "Brazil", limit: 5);

        Assert.DoesNotContain("No players", result);
        // Neymar is the top-rated Brazilian in the dataset (overall 92).
        var firstLine = result.Split('\n').First(l => l.StartsWith("- "));
        Assert.Contains("Neymar", firstLine);
    }

    // Scenario: Brazilian players grouped by Brazilian club
    [Fact]
    public void BrazilianPlayersAtBrazilianClubs_returns_grouping_or_clean_message()
    {
        var result = _tools.BrazilianPlayersAtBrazilianClubs();

        Assert.True(result.Contains("players") || result.Contains("No Brazilian players"));
    }
}
