// <copyright file="McpToolsTests.cs" company="BrazilianSoccerMcp">
// Brazilian Soccer MCP Server - Tests for MCP tool text responses.
// </copyright>
using BrazilianSoccerMcp.Server.Tools;
using BrazilianSoccerMcp.Tests.Fixtures;
using FluentAssertions;

namespace BrazilianSoccerMcp.Tests.Server;

[Collection("Data")]
public class McpToolsTests
{
    private readonly SoccerMcpTools _tools;

    public McpToolsTests(DataFixture fixture)
    {
        _tools = new SoccerMcpTools(fixture.QueryService);
    }

    [Fact]
    public void SearchMatches_ReturnsFormattedMatchList()
    {
        var response = _tools.SearchMatches(team: "Flamengo", opponent: "Fluminense", limit: 5);

        response.Should().NotBeNullOrEmpty();
        response.Should().Contain("Flamengo");
        response.Should().Contain("Fluminense");
    }

    [Fact]
    public void GetHeadToHead_ReturnsStatsAndMatches()
    {
        var response = _tools.GetHeadToHead("Palmeiras", "Santos");

        response.Should().NotBeNullOrEmpty();
        response.Should().Contain("Palmeiras");
        response.Should().Contain("Santos");
        response.Should().Contain("wins");
    }

    [Fact]
    public void SearchPlayers_ReturnsFormattedPlayerList()
    {
        var response = _tools.SearchPlayers(name: "Neymar", limit: 5);

        response.Should().NotBeNullOrEmpty();
        response.Should().Contain("Neymar");
    }

    [Fact]
    public void GetStandings_ReturnsFormattedTable()
    {
        var response = _tools.GetStandings("Brasileirão", 2019, 5);

        response.Should().NotBeNullOrEmpty();
        response.Should().Contain("Flamengo");
    }

    [Fact]
    public void GetCompetitionStatistics_ReturnsAggregateStats()
    {
        var response = _tools.GetCompetitionStatistics("Brasileirão");

        response.Should().NotBeNullOrEmpty();
        response.Should().Contain("Average goals per match");
    }
}
