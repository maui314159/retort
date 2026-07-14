// =============================================================================
// Context
// -----------------------------------------------------------------------------
// File:    PlayerQueryTests.cs
// Project: BrazilianSoccer.Tests
// Purpose: BDD scenarios for player queries over fifa_data.csv: search by name,
//          filter by nationality and club, and top-rated ranking — the spec's
//          "Feature: Player Queries".
// =============================================================================

using BrazilianSoccer.Core.Queries;
using Xunit;

namespace BrazilianSoccer.Tests;

[Collection("dataset")]
public sealed class PlayerQueryTests
{
    private readonly QueryService _query;

    public PlayerQueryTests(DatasetFixture fixture) => _query = fixture.Query;

    [Fact]
    public void Given_PlayerDatabase_When_SearchingForNeymar_Then_HeIsFoundAndBrazilian()
    {
        // When I search for "Neymar"
        var players = _query.SearchPlayersByName("Neymar");

        // Then a Brazilian player named Neymar is returned with a high rating
        Assert.NotEmpty(players);
        var neymar = players[0];
        Assert.Contains("Neymar", neymar.Name);
        Assert.Equal("Brazil", neymar.Nationality);
        Assert.True(neymar.Overall >= 80);
    }

    [Fact]
    public void Given_PlayerDatabase_When_FilteringByNationalityBrazil_Then_AllAreBrazilian()
    {
        // When I list Brazilian players
        var players = _query.PlayersByNationality("Brazil", limit: 100);

        // Then every player is Brazilian and the list is rating-sorted
        Assert.NotEmpty(players);
        Assert.All(players, p => Assert.Equal("Brazil", p.Nationality));
        for (var i = 1; i < players.Count; i++)
            Assert.True(players[i - 1].Overall >= players[i].Overall);
    }

    [Fact]
    public void Given_PlayerDatabase_When_FilteringByClub_Then_PlayersBelongToThatClub()
    {
        // When I list players at Flamengo
        var players = _query.PlayersByClub("Flamengo");

        // Then each returned player's club normalises to Flamengo
        Assert.All(players, p =>
            Assert.True(p.ClubKey.Contains("flamengo", StringComparison.Ordinal)));
    }

    [Fact]
    public void Given_PlayerDatabase_When_RequestingTopBrazilians_Then_TheyAreHighestRatedBrazilians()
    {
        // When I ask for the top 5 Brazilian players
        var top = _query.TopPlayers(limit: 5, nationality: "Brazil");

        // Then there are 5, all Brazilian, ordered by overall descending
        Assert.Equal(5, top.Count);
        Assert.All(top, p => Assert.Equal("Brazil", p.Nationality));
        for (var i = 1; i < top.Count; i++)
            Assert.True(top[i - 1].Overall >= top[i].Overall);
    }

    [Fact]
    public void Given_PlayerDatabase_When_EmptyNameSearched_Then_ReturnsEmpty()
    {
        Assert.Empty(_query.SearchPlayersByName(""));
    }
}
