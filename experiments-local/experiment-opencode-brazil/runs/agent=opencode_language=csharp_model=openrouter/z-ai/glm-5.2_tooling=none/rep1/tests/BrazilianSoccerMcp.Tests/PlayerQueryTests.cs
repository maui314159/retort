// Context block
// File: PlayerQueryTests.cs
// Purpose: BDD/GWT tests for the PlayerService of the Brazilian Soccer MCP server,
// covering the "Player Queries" feature from TASK.md: search Brazilian players, find
// players by club, and rank by overall rating. Tests run against the real FIFA dataset
// via the shared SoccerDataFixture.
// Language: C# (.NET 10) + xUnit. Owner: Brazilian Soccer MCP benchmark implementation.

using BrazilianSoccerMcp.Services;

namespace BrazilianSoccerMcp.Tests;

[Collection("SoccerData")]
public class PlayerQueryTests
{
    private readonly SoccerDataFixture _f;
    public PlayerQueryTests(SoccerDataFixture fixture) => _f = fixture;

    // Feature: Player Queries

    // Scenario: Find top-rated Brazilian players
    //   Given the FIFA player data is loaded
    //   When I search for Brazilian players ordered by overall
    //   Then I should receive a non-empty list sorted by overall descending
    [Fact]
    public void Top_brazilian_players_are_sorted_by_overall_desc()
    {
        var players = _f.Players.SearchPlayers(nationality: "Brazil", topN: 10);

        Assert.NotEmpty(players);
        for (int i = 1; i < players.Count; i++)
        {
            Assert.True(players[i - 1].Overall >= players[i].Overall,
                $"expected {players[i - 1].Overall} >= {players[i].Overall}");
        }
        Assert.All(players, p => Assert.Equal("Brazil", p.Nationality, StringComparer.OrdinalIgnoreCase));
    }

    // Scenario: Search a player by name
    //   Given the FIFA player data is loaded
    //   When I search for "Neymar"
    //   Then the result should include a player whose name contains Neymar
    [Fact]
    public void Search_by_name_returns_matching_player()
    {
        var players = _f.Players.SearchPlayers(name: "Neymar", topN: 10);

        Assert.NotEmpty(players);
        Assert.Contains(players, p => p.Name.Contains("Neymar", StringComparison.OrdinalIgnoreCase));
    }

    // Scenario: Brazilian players grouped by club
    //   Given the FIFA player data is loaded
    //   When I ask for Brazilian players grouped by club
    //   Then I should receive a non-empty list of clubs with counts
    [Fact]
    public void Brazilian_players_by_club_returns_counts()
    {
        var clubs = _f.Players.BrazilianPlayersByClub(topN: 10);

        Assert.NotEmpty(clubs);
        Assert.True(clubs[0].Count >= clubs[^1].Count);
    }

    // Scenario: Filter players by club
    //   Given the FIFA player data is loaded
    //   When I search for players at a Brazilian club
    //   Then every returned player should have that club in their Club field
    [Fact]
    public void Search_by_club_filters_correctly()
    {
        var players = _f.Players.SearchPlayers(club: "Flamengo", topN: 20);

        Assert.All(players, p =>
            Assert.Contains("Flamengo", p.Club, StringComparison.OrdinalIgnoreCase));
    }
}
