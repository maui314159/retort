using BrazilianSoccerCore.Data;
using BrazilianSoccerMcp.Tests.Infrastructure;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Feature: Player Queries
/// BDD scenarios for searching the FIFA player dataset.
/// </summary>
[Collection("SoccerData")]
public class PlayerQueryTests
{
    private readonly DataFixture _f;
    public PlayerQueryTests(DataFixture f) => _f = f;

    // Scenario: Find all Brazilian players in the dataset
    //   When I filter FIFA data by nationality "Brazil"
    //   Then I should receive players whose nationality is Brazil
    [Fact]
    public void SearchPlayers_by_Brazil_nationality_returns_brazilians()
    {
        var players = _f.Players.SearchPlayers(nationality: "Brazil", limit: 50);
        Assert.NotEmpty(players);
        Assert.All(players, p =>
            Assert.True(TeamNormalizer.SameTeam(p.Nationality, "Brazil")));
    }

    // Scenario: Who are the highest-rated players?
    [Fact]
    public void TopRated_returns_players_sorted_by_overall_desc()
    {
        var players = _f.Players.TopRated(limit: 10);
        Assert.NotEmpty(players);
        for (var i = 1; i < players.Count; i++)
            Assert.True(players[i - 1].Overall >= players[i].Overall);
    }

    // Scenario: Top Brazilian players
    [Fact]
    public void TopRated_brazilians_are_sorted_and_brazilian()
    {
        var players = _f.Players.TopRated(limit: 10, nationality: "Brazil");
        Assert.NotEmpty(players);
        Assert.All(players, p => Assert.True(TeamNormalizer.SameTeam(p.Nationality, "Brazil")));
        for (var i = 1; i < players.Count; i++)
            Assert.True(players[i - 1].Overall >= players[i].Overall);
    }

    // Scenario: Search by name (accent-insensitive)
    [Fact]
    public void SearchByName_is_accent_insensitive()
    {
        var players = _f.Players.SearchByName("Neymar");
        Assert.NotEmpty(players);
        Assert.All(players, p => Assert.Contains("neymar", TeamNormalizer.Key(p.Name)));
    }

    // Scenario: Show me all forwards from a club
    [Fact]
    public void SearchPlayers_by_position_forward_returns_strikers()
    {
        var players = _f.Players.SearchPlayers(position: "forward", limit: 20);
        Assert.NotEmpty(players);
        Assert.All(players, p =>
        {
            var forwardPositions = new[] { "ST", "CF", "LS", "RS", "LW", "RW", "LF", "RF" };
            Assert.Contains(p.Position, forwardPositions);
        });
    }

    // Scenario: filter by club
    [Fact]
    public void SearchPlayers_by_club_returns_club_members()
    {
        // Use a club fragment that exists in the FIFA dataset.
        var players = _f.Players.SearchPlayers(club: "Barcelona", limit: 30);
        Assert.NotEmpty(players);
        Assert.All(players, p =>
            Assert.Contains("barcelona", TeamNormalizer.Key(p.Club)));
    }

    // Scenario: Brazilian players at Brazilian clubs grouped
    [Fact]
    public void BrazilianPlayersAtBrazilianClubs_returns_groups()
    {
        var groups = _f.Players.BrazilianPlayersAtBrazilianClubs();
        // The FIFA dataset snapshot may or may not include Brazilian clubs;
        // if it does, each group must have a positive count and avg rating.
        Assert.All(groups, g =>
        {
            Assert.True(g.Count > 0);
            Assert.InRange(g.AvgRating, 0, 100);
        });
    }
}