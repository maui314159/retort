// <copyright file="PlayerQueryTests.cs" company="BrazilianSoccerMcp">
// Brazilian Soccer MCP Server - BDD scenarios for player queries.
// </copyright>
using BrazilianSoccerMcp.Core.Models;
using BrazilianSoccerMcp.Core.Services;
using BrazilianSoccerMcp.Tests.Fixtures;
using FluentAssertions;

namespace BrazilianSoccerMcp.Tests.Queries;

[Collection("Data")]
public class PlayerQueryTests
{
    private readonly SoccerQueryService _queryService;

    public PlayerQueryTests(DataFixture fixture)
    {
        _queryService = fixture.QueryService;
    }

    [Fact]
    public void GivenFifaData_WhenFilteringBrazilianPlayers_ThenReturnsManyBrazilianPlayers()
    {
        var players = _queryService.SearchPlayers(new PlayerSearchCriteria
        {
            Nationality = "Brazil",
            Limit = 1000
        });

        players.Should().NotBeEmpty();
        players.Should().OnlyContain(p =>
            p.Nationality.Contains("Brazil", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void GivenFifaData_WhenSearchingTopBrazilianPlayers_ThenResultsAreSortedByOverall()
    {
        var players = _queryService.SearchPlayers(new PlayerSearchCriteria
        {
            Nationality = "Brazil",
            Limit = 5
        });

        players.Should().NotBeEmpty();
        players.Should().BeInDescendingOrder(p => p.Overall!.Value);
    }

    [Fact]
    public void GivenFifaData_WhenSearchingTopPlayersAtAClub_ThenResultsAreSortedByOverall()
    {
        var players = _queryService.SearchPlayers(new PlayerSearchCriteria
        {
            Club = "Paris Saint-Germain",
            Limit = 5
        });

        players.Should().NotBeEmpty();
        players.Should().BeInDescendingOrder(p => p.Overall!.Value);
    }

    [Fact]
    public void GivenFifaData_WhenSearchingByNameNeymar_ThenReturnsMatch()
    {
        var players = _queryService.SearchPlayers(new PlayerSearchCriteria
        {
            Name = "Neymar"
        });

        players.Should().NotBeEmpty();
        players.Should().Contain(p =>
            p.Name.Contains("Neymar", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void GivenFifaData_WhenSearchingForwardsAtAClub_ThenReturnsForwardPlayers()
    {
        var players = _queryService.SearchPlayers(new PlayerSearchCriteria
        {
            Club = "Liverpool",
            Position = "ST",
            Limit = 50
        });

        players.Should().NotBeEmpty();
        players.Should().OnlyContain(p =>
            !string.IsNullOrEmpty(p.Position) &&
            p.Position.Contains("ST", StringComparison.OrdinalIgnoreCase));
    }
}
