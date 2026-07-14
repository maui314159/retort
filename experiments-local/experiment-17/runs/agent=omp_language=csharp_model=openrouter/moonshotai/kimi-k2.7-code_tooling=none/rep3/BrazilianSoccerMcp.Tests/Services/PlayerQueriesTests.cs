using BrazilianSoccerMcp.Server.Data;
using BrazilianSoccerMcp.Server.Services;
using BrazilianSoccerMcp.Tests.Data;
using FluentAssertions;

namespace BrazilianSoccerMcp.Tests.Services;

[Collection("SoccerData")]
public sealed class PlayerQueriesTests
{
    private readonly SoccerDataContext _context;

    public PlayerQueriesTests(DataFixture fixture)
    {
        _context = fixture.Context;
    }

    [Fact]
    public void Given_the_player_data_is_loaded_When_searching_for_Brazilian_players_Then_should_return_only_Brazilian_players()
    {
        var service = new PlayerService(_context);

        var players = service.SearchPlayers(nationality: "Brazil");

        players.Should().NotBeEmpty();
        players.Should().OnlyContain(p => p.Nationality.Equals("Brazil", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void Given_the_player_data_is_loaded_When_searching_for_players_at_Gremio_Then_should_return_players_at_Gremio()
    {
        var service = new PlayerService(_context);

        var players = service.SearchPlayers(club: "Grêmio");

        players.Should().NotBeEmpty();
        players.Should().OnlyContain(p => p.Club.Contains("Grêmio", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void Given_the_player_data_is_loaded_When_searching_for_top_rated_Brazilian_players_Then_results_should_be_sorted_by_overall()
    {
        var service = new PlayerService(_context);

        var players = service.SearchPlayers(nationality: "Brazil", minOverall: 85, limit: 10);

        players.Should().NotBeEmpty();
        players.Should().Equal(players.OrderByDescending(p => p.Overall ?? 0));
        players.Should().OnlyContain(p => p.Overall >= 85);
    }
}
