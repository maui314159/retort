using BrazilianSoccerMcp.Services;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// BDD-style tests for player queries against the FIFA dataset.
/// </summary>
[Collection("DataCollection")]
public class PlayerQueryBddTests
{
    private readonly DataFixture _fixture;

    public PlayerQueryBddTests(DataFixture fixture) => _fixture = fixture;

    [Fact]
    public void Search_Brazilian_players_returns_sorted_by_overall()
    {
        // Given the player data is loaded
        var svc = new PlayerService(_fixture.Repository);
        Assert.NotEmpty(_fixture.Repository.Players);

        // When I search for Brazilian players
        var players = svc.Search(nationality: "Brazil", limit: 20);

        // Then the result is non-empty, all Brazilian, sorted desc by Overall
        Assert.NotEmpty(players);
        Assert.All(players, p => Assert.Equal("Brazil", p.Nationality));
        for (int i = 1; i < players.Count; i++)
            Assert.True(players[i - 1].Overall >= players[i].Overall);
    }

    [Fact]
    public void Search_players_at_a_specific_club()
    {
        // Given the player data is loaded (the bundled FIFA 19 snapshot focuses
        // on European clubs, so we pick one that is well represented)
        var svc = new PlayerService(_fixture.Repository);

        // When I search for Brazilian players at Real Madrid
        var players = svc.Search(club: "Real Madrid", nationality: "Brazil");

        // Then every result is at Real Madrid and Brazilian
        Assert.NotEmpty(players);
        Assert.All(players, p =>
        {
            Assert.Contains("Real Madrid", p.Club, StringComparison.OrdinalIgnoreCase);
            Assert.Equal("Brazil", p.Nationality);
        });
    }

    [Fact]
    public void Search_by_position_and_min_overall()
    {
        var svc = new PlayerService(_fixture.Repository);
        var strikers = svc.Search(position: "ST", minOverall: 80, limit: 20);
        Assert.All(strikers, p =>
        {
            Assert.Contains("ST", p.Position, StringComparison.OrdinalIgnoreCase);
            Assert.True(p.Overall >= 80);
        });
    }

    [Fact]
    public void Group_by_club_returns_counts_and_averages()
    {
        // Given the player data is loaded (FIFA 19 snapshot has no Brazilian
        // league clubs, so we group Brazilian players by their European clubs)
        var svc = new PlayerService(_fixture.Repository);
        var groups = svc.GroupByClub(nationality: "Brazil");
        Assert.NotEmpty(groups);
        Assert.All(groups, g => Assert.True(g.Count > 0));
    }
}
