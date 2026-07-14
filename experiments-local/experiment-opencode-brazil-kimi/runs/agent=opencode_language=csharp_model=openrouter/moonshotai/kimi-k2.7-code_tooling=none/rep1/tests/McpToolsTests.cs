/*
 * Brazilian Soccer MCP Server - MCP Tools Tests
 *
 * Verifies that the MCP tool wrapper methods return formatted responses
 * when invoked against the loaded datasets.
 */
using BrazilianSoccerMcp.Mcp;

namespace BrazilianSoccerMcp.Tests;

public class McpToolsTests : QueryTestBase
{
    private readonly SoccerTools _tools;

    public McpToolsTests(DataFixture fixture) : base(fixture)
    {
        _tools = new SoccerTools(Engine);
    }

    [Fact]
    public void GivenTools_WhenCallingFindMatches_ThenReturnsFormattedMatchList()
    {
        var result = _tools.FindMatches(team: "Flamengo", opponent: "Fluminense", limit: 5);

        Assert.NotNull(result);
        Assert.Contains("Flamengo", result);
        Assert.Contains("Fluminense", result);
    }

    [Fact]
    public void GivenTools_WhenCallingGetTeamStatistics_ThenReturnsFormattedRecord()
    {
        var result = _tools.GetTeamStatistics("Palmeiras", season: 2023, competition: "Brasileirão");

        Assert.NotNull(result);
        Assert.Contains("Palmeiras", result);
        Assert.Contains("Matches:", result);
    }

    [Fact]
    public void GivenTools_WhenCallingSearchPlayers_ThenReturnsFormattedPlayerList()
    {
        var result = _tools.SearchPlayers(nationality: "Brazil", club: "Fluminense", limit: 5);

        Assert.NotNull(result);
        Assert.Contains("Players", result);
    }
}
