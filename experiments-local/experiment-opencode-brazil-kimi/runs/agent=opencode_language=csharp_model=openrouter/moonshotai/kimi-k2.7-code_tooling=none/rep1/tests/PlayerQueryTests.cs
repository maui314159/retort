/*
 * Brazilian Soccer MCP Server - Player Query Tests
 *
 * BDD scenarios covering player search, nationality filters and top-rated players.
 */
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Queries;

namespace BrazilianSoccerMcp.Tests;

public class PlayerQueryTests : QueryTestBase
{
    public PlayerQueryTests(DataFixture fixture) : base(fixture) { }

    [Fact]
    public void GivenPlayerDataLoaded_WhenSearchingForBrazilianPlayers_ThenReceiveBrazilianPlayersOnly()
    {
        var players = Engine.SearchPlayers(nationality: "Brazil");

        Assert.NotEmpty(players);
        Assert.All(players, p => Assert.Equal("Brazil", p.Nationality, StringComparer.OrdinalIgnoreCase));
    }

    [Fact]
    public void GivenPlayerDataLoaded_WhenSearchingForFluminensePlayers_ThenReceivePlayersAtFluminense()
    {
        var players = Engine.SearchPlayers(club: "Fluminense");

        Assert.NotEmpty(players);
        Assert.All(players, p => Assert.Contains("Fluminense", p.Club ?? string.Empty, StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void GivenPlayerDataLoaded_WhenRequestingTopBrazilianPlayers_ThenReceivePlayersSortedByOverall()
    {
        var players = Engine.GetTopPlayers(nationality: "Brazil", count: 5);

        Assert.Equal(5, players.Count);
        Assert.All(players, p => Assert.Equal("Brazil", p.Nationality, StringComparer.OrdinalIgnoreCase));
        for (int i = 1; i < players.Count; i++)
        {
            Assert.True(players[i - 1].Overall >= players[i].Overall);
        }
    }

    [Fact]
    public void GivenPlayerDataLoaded_WhenSearchingByName_ThenReceiveMatchingPlayers()
    {
        var players = Engine.SearchPlayers(name: "Neymar");

        Assert.NotEmpty(players);
        Assert.All(players, p => Assert.Contains("Neymar", p.Name, StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void GivenPlayerDataLoaded_WhenFilteringByPosition_ThenReceivePlayersInThatPosition()
    {
        var players = Engine.SearchPlayers(position: "ST", nationality: "Brazil");

        Assert.NotEmpty(players);
        Assert.All(players, p => Assert.Contains("ST", p.Position ?? string.Empty, StringComparison.OrdinalIgnoreCase));
    }
}
